# backend/Services/Service_googledrive.py
# ────────────────────────────────────────────────────────────────────────────────
#  • Cliente Google Drive usando conta de serviço
#  • Lê credenciais nesta ordem de prioridade:
#        1) st.secrets["GOOGLE_CREDENTIALS"]      (Streamlit Cloud / secrets.toml)
#        2) variável de ambiente GOOGLE_CREDENTIALS_JSON  (string JSON completa)
#        3) arquivo local CREDENTIALS_FILE                      (fallback)
#  • Mantém toda a API pública original (ensure_folder, upload_file, etc.)
# ────────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import io
import json
import logging
import mimetypes
import os
import pathlib
import ssl
import time
import random
from pathlib import Path
from typing import List, Optional

import httplib2
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import threading
import streamlit as st

# ─────────────────── Config logging ────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────── Config globals ────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parents[2]          # .../Project_Organizer
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)                                   # carrega variáveis locais

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

# Retry parameters -------------------------------------------------------------
MAX_RETRIES = 3
RETRY_DELAY  = 2  # segundos

# Arquivo local de credenciais (fallback) --------------------------------------
CREDENTIALS_FILE = Path(__file__).parent / "gestao-de-contratos-459115-56094189aaf9.json"

# Cache de serviço por thread
_thread_local = threading.local()

# ─────────────────── Helpers ───────────────────────────────────────────────────
def _retry_on_error(func):
    """Decorator para retentar operações em caso de falhas transitórias."""
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except (HttpError, ConnectionError, TimeoutError, ssl.SSLError) as e:
                last_error = e
                logger.warning(f"Tentativa {attempt + 1} falhou: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        raise Exception(f"Erro após {MAX_RETRIES} tentativas: {last_error}")
    return wrapper


def _load_credentials() -> Credentials:
    """
    Carrega credenciais do Google na seguinte ordem de prioridade:
      1) st.secrets["gdrive"]["credentials_json"]   (Streamlit Cloud)
      2) variável de ambiente GOOGLE_CREDENTIALS_JSON (string JSON)
      3) arquivo local CREDENTIALS_FILE
    """
    # 1) st.secrets -------------------------------------------------------------
    try:
        if "gdrive" in st.secrets and "credentials_json" in st.secrets["gdrive"]:
            try:
                # Tenta carregar o JSON
                creds_json = st.secrets["gdrive"]["credentials_json"]
                if isinstance(creds_json, str):
                    creds_dict = json.loads(creds_json)
                else:
                    creds_dict = creds_json
                
                # Garante que a chave privada está no formato correto
                if "private_key" in creds_dict:
                    private_key = creds_dict["private_key"]
                    if not private_key.startswith("-----BEGIN PRIVATE KEY-----"):
                        private_key = private_key.replace("\\n", "\n")
                        creds_dict["private_key"] = private_key
                
                logger.info("Credenciais carregadas de st.secrets['gdrive']['credentials_json']")
                return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar JSON das credenciais: {e}")
                raise
    except ModuleNotFoundError:
        pass  # não estamos rodando dentro do Streamlit

    # 2) Variável de ambiente ---------------------------------------------------
    env_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if env_json:
        try:
            creds_dict = json.loads(env_json)
            logger.info("Credenciais carregadas da variável de ambiente GOOGLE_CREDENTIALS_JSON")
            return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON das credenciais da variável de ambiente: {e}")
            raise

    # 3) Arquivo local ----------------------------------------------------------
    if CREDENTIALS_FILE.exists():
        logger.info(f"Credenciais carregadas de arquivo: {CREDENTIALS_FILE.name}")
        return Credentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=SCOPES)

    # Falhou em todas as opções -------------------------------------------------
    raise FileNotFoundError(
        "Nenhum método de credencial Google encontrado (secrets, env ou arquivo)."
    )


def _build_service():
    """Cria (singleton) o cliente Drive."""
    creds = _load_credentials()
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    service._http.timeout = 120  # segundos (era ≈60)
    return service


def get_service():
    """Interface pública para obter o cliente Drive."""
    if not hasattr(_thread_local, "service"):
        _thread_local.service = _build_service()
    return _thread_local.service


def _folder_query(name: str, parent_id: Optional[str]) -> str:
    """Monta query para busca de pastas por nome (e opcionalmente pai)."""
    q = f"mimeType='application/vnd.google-apps.folder' and name='{name}'"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    return q

# ─────────────────── API pública (folders / files) ────────────────────────────
@_retry_on_error
def ensure_folder(name: str, parent_id: Optional[str] = None) -> str:
    """Garante existência da pasta (cria se necessário) e retorna o ID."""
    try:
        service = get_service()
        # Tenta encontrar a pasta
        for i in range(5):
            try:
                resp = service.files().list(
                    q=_folder_query(name, parent_id),
                    fields="files(id, modifiedTime)",
                    pageSize=1
                ).execute()
                if resp.get("files"):
                    logger.info(f"Pasta encontrada: {name}")
                    return resp["files"][0]["id"]
                break
            except Exception as e:
                wait = min(2 ** i, 8) + random.random()
                logger.warning(f"Tentativa {i+1} falhou: {e} – aguardando {wait:.1f}s")
                time.sleep(wait)
        else:
            raise
        # Cria a pasta se não encontrou
        logger.info(f"Criando nova pasta: {name}")
        metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            metadata["parents"] = [parent_id]
        for i in range(5):
            try:
                folder = service.files().create(
                    body=metadata, fields="id, modifiedTime"
                ).execute()
                logger.info(f"Pasta criada com sucesso: {name}")
                return folder["id"]
            except Exception as e:
                wait = min(2 ** i, 8) + random.random()
                logger.warning(f"Tentativa {i+1} falhou: {e} – aguardando {wait:.1f}s")
                time.sleep(wait)
        else:
            raise
    except Exception as e:
        logger.error(f"Erro ao garantir pasta: {e}")
        raise


@_retry_on_error
def upload_file(local_path: str, parent_id: str) -> str:
    """Faz upload de um arquivo para a pasta especificada e devolve o fileId."""
    try:
        service = get_service()
        local_path = pathlib.Path(local_path)
        mime_type, _ = mimetypes.guess_type(local_path.name)
        logger.info(f"Upload de arquivo: {local_path.name}")
        metadata = {"name": local_path.name, "parents": [parent_id]}
        media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
        for i in range(5):
            try:
                file = service.files().create(
                    body=metadata, media_body=media, fields="id, modifiedTime"
                ).execute()
                logger.info(f"Arquivo enviado com sucesso: {local_path.name}")
                return file["id"]
            except Exception as e:
                wait = min(2 ** i, 8) + random.random()
                logger.warning(f"Tentativa {i+1} falhou: {e} – aguardando {wait:.1f}s")
                time.sleep(wait)
        else:
            raise
    except Exception as e:
        logger.error(f"Erro ao fazer upload do arquivo: {e}")
        raise


@_retry_on_error
def list_files(parent_id: str, mime_filter: Optional[str] = None) -> List[dict]:
    """Lista arquivos dentro de uma pasta; pode filtrar por mimeType."""
    try:
        service = get_service()
        q = f"'{parent_id}' in parents"
        if mime_filter:
            q += f" and mimeType='{mime_filter}'"
        logger.info(f"Listando arquivos da pasta: {parent_id}")
        for i in range(5):
            try:
                resp = service.files().list(
                    q=q,
                    fields="files(id, modifiedTime)",
                    pageSize=1000
                ).execute()
                files = resp.get("files", [])
                logger.info(f"Encontrados {len(files)} arquivos")
                return files
            except Exception as e:
                wait = min(2 ** i, 8) + random.random()
                logger.warning(f"Tentativa {i+1} falhou: {e} – aguardando {wait:.1f}s")
                time.sleep(wait)
        else:
            raise
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {e}")
        raise


def list_files_in_folder(folder_id: str) -> List[dict]:
    """Alias para manter compatibilidade retro-ativa."""
    return list_files(folder_id)


def download_file(file_id: str, dest_path: str) -> bool:
    """Baixa um arquivo do Drive para `dest_path`."""
    try:
        service = get_service()
        logger.info(f"Download de arquivo: {file_id}")
        # Verifica se o arquivo existe
        for i in range(5):
            try:
                file = service.files().get(fileId=file_id, fields="id, name, size, modifiedTime").execute()
                logger.info(f"Arquivo encontrado: {file.get('name')} ({file.get('size')} bytes)")
                break
            except Exception as e:
                wait = min(2 ** i, 8) + random.random()
                logger.warning(f"Tentativa {i+1} falhou: {e} – aguardando {wait:.1f}s")
                time.sleep(wait)
        else:
            raise
        request = service.files().get_media(fileId=file_id)
        dest_dir = Path(dest_path).parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        with io.FileIO(dest_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                for i in range(5):
                    try:
                        status, done = downloader.next_chunk()
                        if status:
                            logger.info(f"Download progress: {int(status.progress() * 100)}%")
                        break
                    except Exception as e:
                        wait = min(2 ** i, 8) + random.random()
                        logger.warning(f"Tentativa {i+1} falhou: {e} – aguardando {wait:.1f}s")
                        time.sleep(wait)
                else:
                    raise
        if not Path(dest_path).exists():
            logger.error("Arquivo não foi criado após o download")
            return False
        tamanho = Path(dest_path).stat().st_size
        if tamanho == 0:
            logger.error("Arquivo foi criado mas está vazio")
            return False
        logger.info(f"Arquivo baixado com sucesso: {dest_path} ({tamanho} bytes)")
        return True
    except Exception as e:
        logger.error(f"Erro ao baixar arquivo: {e}")
        return False


@_retry_on_error
def update_file(file_id: str, new_local_path: str):
    """Substitui o conteúdo de um arquivo mantendo o mesmo ID."""
    try:
        service = get_service()
        new_local_path = pathlib.Path(new_local_path)
        mime_type, _ = mimetypes.guess_type(new_local_path.name)
        logger.info(f"Atualizando arquivo: {file_id}")
        media = MediaFileUpload(new_local_path, mimetype=mime_type, resumable=True)
        for i in range(5):
            try:
                service.files().update(
                    fileId=file_id, media_body=media, fields="id, modifiedTime"
                ).execute()
                logger.info(f"Arquivo atualizado com sucesso: {file_id}")
                break
            except Exception as e:
                wait = min(2 ** i, 8) + random.random()
                logger.warning(f"Tentativa {i+1} falhou: {e} – aguardando {wait:.1f}s")
                time.sleep(wait)
        else:
            raise
    except Exception as e:
        logger.error(f"Erro ao atualizar arquivo: {e}")
        raise


@_retry_on_error
def get_file_id_by_name(name: str, parent_id: Optional[str] = None) -> Optional[str]:
    """Busca um arquivo (ou pasta) pelo nome dentro de um diretório pai opcional."""
    try:
        service = get_service()
        q = f"name='{name}'"
        if parent_id:
            q += f" and '{parent_id}' in parents"

        logger.info(f"Buscando arquivo por nome: {name}")
        resp = service.files().list(q=q, fields="files(id)", pageSize=1).execute()
        files = resp.get("files", [])

        if files:
            logger.info(f"Arquivo encontrado: {name}")
            return files[0]["id"]

        logger.info(f"Arquivo não encontrado: {name}")
        return None

    except Exception as e:
        logger.error(f"Erro ao buscar arquivo por nome: {e}")
        raise

# Helper para cache de file_id

def _find_file_id(name: str, folder_id: str) -> str:
    service = get_service()
    q = f"name='{name}'"
    if folder_id:
        q += f" and '{folder_id}' in parents"
    logger.info(f"Buscando arquivo por nome: {name}")
    for i in range(5):
        try:
            resp = service.files().list(q=q, fields="files(id, modifiedTime)", pageSize=1).execute()
            files = resp.get("files", [])
            if files:
                logger.info(f"Arquivo encontrado: {name}")
                return files[0]["id"]
            logger.info(f"Arquivo não encontrado: {name}")
            return None
        except Exception as e:
            wait = min(2 ** i, 8) + random.random()
            logger.warning(f"Tentativa {i+1} falhou: {e} – aguardando {wait:.1f}s")
            time.sleep(wait)
    raise

def _get_cached_file_id(name: str, folder_id: str) -> str:
    cache_key = f"file_id:{name}:{folder_id}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = _find_file_id(name, folder_id)
    return st.session_state[cache_key]

# Trocar chamadas:
# file_id = get_file_id_by_name(DB_NAME, folder_id)
# por
# file_id = _get_cached_file_id(DB_NAME, folder_id)

# Em todas as files().get(...), limitar fields para 'id, modifiedTime'
# Em files().list(...), limitar fields para 'files(id, modifiedTime)'
# (Já aplicado acima nos exemplos)

# Repita o padrão de retry/back-off e fields enxuto nas demais funções que fazem request.execute(),
# como update_file, upload_file, ensure_folder, get_file_id_by_name, etc.
# ...
