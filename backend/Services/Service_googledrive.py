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
from pathlib import Path
from typing import List, Optional

import httplib2
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

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

# Instância global do serviço --------------------------------------------------
_service: Optional["googleapiclient.discovery.Resource"] = None

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
        import streamlit as st  # só existe em runtime Streamlit
        if "gdrive" in st.secrets and "credentials_json" in st.secrets["gdrive"]:
            creds_dict = json.loads(st.secrets["gdrive"]["credentials_json"])
            logger.info("Credenciais carregadas de st.secrets['gdrive']['credentials_json']")
            return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    except ModuleNotFoundError:
        pass  # não estamos rodando dentro do Streamlit

    # 2) Variável de ambiente ---------------------------------------------------
    env_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if env_json:
        logger.info("Credenciais carregadas da variável de ambiente GOOGLE_CREDENTIALS_JSON")
        return Credentials.from_service_account_info(json.loads(env_json), scopes=SCOPES)

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
    global _service
    if _service is not None:
        return _service

    try:
        logger.info("Iniciando construção do serviço Google Drive")
        creds = _load_credentials()

        _service = build("drive", "v3", credentials=creds, cache_discovery=False)
        # teste rápido
        _service.files().list(pageSize=1).execute()
        logger.info("Serviço Google Drive construído e testado com sucesso")
        return _service

    except Exception as e:
        logger.error(f"Erro ao construir serviço do Google Drive: {e}")
        raise


def get_service():
    """Interface pública para obter o cliente Drive."""
    return _build_service()


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
        resp = service.files().list(
            q=_folder_query(name, parent_id),
            fields="files(id)",
            pageSize=1
        ).execute()

        if resp.get("files"):
            logger.info(f"Pasta encontrada: {name}")
            return resp["files"][0]["id"]

        logger.info(f"Criando nova pasta: {name}")
        metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            metadata["parents"] = [parent_id]
        folder = service.files().create(body=metadata, fields="id").execute()
        logger.info(f"Pasta criada com sucesso: {name}")
        return folder["id"]

    except Exception as e:
        logger.error(f"Erro ao garantir pasta: {e}")
        raise


@_retry_on_error
def upload_file(local_path: str, parent_id: str) -> str:
    """Faz upload de um arquivo para a pasta especificada e devolve o fileId."""
    try:
        service    = get_service()
        local_path = pathlib.Path(local_path)
        mime_type, _ = mimetypes.guess_type(local_path.name)

        logger.info(f"Upload de arquivo: {local_path.name}")
        metadata = {"name": local_path.name, "parents": [parent_id]}
        media    = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)

        file = service.files().create(body=metadata, media_body=media, fields="id").execute()
        logger.info(f"Arquivo enviado com sucesso: {local_path.name}")
        return file["id"]

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
        resp  = service.files().list(
            q=q,
            fields="files(id, name, mimeType, size, createdTime)",
            pageSize=1000
        ).execute()
        files = resp.get("files", [])
        logger.info(f"Encontrados {len(files)} arquivos")
        return files

    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {e}")
        raise


def list_files_in_folder(folder_id: str) -> List[dict]:
    """Alias para manter compatibilidade retro-ativa."""
    return list_files(folder_id)


@_retry_on_error
def download_file(file_id: str, dest_path: str):
    """Baixa um arquivo do Drive para `dest_path`."""
    try:
        service = get_service()
        logger.info(f"Download de arquivo: {file_id}")
        request = service.files().get_media(fileId=file_id)

        with io.FileIO(dest_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        logger.info(f"Arquivo baixado em: {dest_path}")

    except Exception as e:
        logger.error(f"Erro ao baixar arquivo: {e}")
        raise


@_retry_on_error
def update_file(file_id: str, new_local_path: str):
    """Substitui o conteúdo de um arquivo mantendo o mesmo ID."""
    try:
        service       = get_service()
        new_local_path = pathlib.Path(new_local_path)
        mime_type, _  = mimetypes.guess_type(new_local_path.name)

        logger.info(f"Atualizando arquivo: {file_id}")
        media = MediaFileUpload(new_local_path, mimetype=mime_type, resumable=True)
        service.files().update(fileId=file_id, media_body=media).execute()
        logger.info(f"Arquivo atualizado com sucesso: {file_id}")

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
