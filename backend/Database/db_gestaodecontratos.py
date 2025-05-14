# backend/Database/db_gestaodecontratos.py

import os
import sqlite3
import tempfile
from dotenv import load_dotenv
import sys
from pathlib import Path
import threading
import contextlib
import logging
import streamlit as st
import time

# Adiciona o caminho do backend para importar corretamente o módulo do Google Drive
sys.path.append(str(Path(__file__).resolve().parents[1]))
from Services import Service_googledrive as gdrive

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────── Variáveis ───────────────────────────
load_dotenv()
DB_NAME = "db_gestaodecontratos.db"
DB_PATH = Path(tempfile.gettempdir()) / DB_NAME
_last_remote_ts: float = 0.0   # epoch seconds da última versão remota vista

# Cache de conexão por thread
_thread_local = threading.local()

def marca_sujo() -> None:
    """Marca o banco como modificado na thread atual."""
    setattr(_thread_local, "dirty", True)

def _remote_modified_ts(file_id: str) -> float:
    """Obtém o timestamp de modificação de um arquivo no Google Drive."""
    meta = gdrive.get_service().files().get(
        fileId=file_id, fields="modifiedTime"
    ).execute()
    # O timestamp do Drive tem um 'Z' no final, que indica UTC.
    # time.strptime não lida com frações de segundo ou 'Z' diretamente em todos os sistemas.
    # Removemos as frações de segundo e o 'Z' para um parsing mais robusto.
    ts_string = meta["modifiedTime"].split('.')[0] 
    return time.mktime(time.strptime(ts_string, "%Y-%m-%dT%H:%M:%S"))

def _get_drive_folder_id():
    """Obtém o ID da pasta do Drive do session_state ou do secrets.toml"""
    try:
        # Tenta obter do session_state
        if "GDRIVE_DATABASE_FOLDER_ID" in st.session_state:
            return st.session_state["GDRIVE_DATABASE_FOLDER_ID"]
            
        # Se não estiver no session_state, tenta obter do secrets.toml
        if "gdrive" in st.secrets and "database_folder_id" in st.secrets["gdrive"]:
            folder_id = st.secrets["gdrive"]["database_folder_id"]
            st.session_state["GDRIVE_DATABASE_FOLDER_ID"] = folder_id
            return folder_id
            
        # Se não encontrar em nenhum lugar, usa o valor padrão
        default_id = "1OwkYVqfY8jRaYvZzhW9MkekJAGKSqbPX"
        st.session_state["GDRIVE_DATABASE_FOLDER_ID"] = default_id
        return default_id
        
    except Exception as e:
        logger.error(f"Erro ao obter folder_id: {str(e)}")
        # Em caso de erro, retorna o valor padrão
        return "1OwkYVqfY8jRaYvZzhW9MkekJAGKSqbPX"

def autenticar_usuario(usuario: str, senha: str) -> tuple[bool, str, str]:
    """Autentica um usuário no sistema"""
    conn = None
    try:
        # Baixa o banco do Drive se necessário
        caminho_banco = baixar_banco_do_drive()
        conn = sqlite3.connect(str(caminho_banco))
        cursor = conn.cursor()
        
        # Busca usuário
        cursor.execute(
            "SELECT tipo, nome FROM usuarios WHERE usuario = ? AND senha = ?",
            (usuario, senha)
        )
        resultado = cursor.fetchone()
        
        if resultado:
            logger.info(f"Usuário autenticado: {usuario} (Tipo: {resultado[0]})")
            return True, resultado[0], resultado[1]
        logger.warning(f"Tentativa de login falhou para usuário: {usuario}")
        return False, "", ""
        
    except Exception as e:
        logger.error(f"Erro ao autenticar usuário: {str(e)}")
        return False, "", ""
        
    finally:
        if conn:
            conn.close()

# ─────────────── Baixar banco do Google Drive ───────────────
def baixar_banco_do_drive():
    """Baixa o banco de dados do Google Drive"""
    try:
        folder_id = _get_drive_folder_id()
        logger.info(f"Usando pasta do Drive: {folder_id}")
            
        file_id = gdrive.get_file_id_by_name(DB_NAME, folder_id)
        if not file_id:
            # Se o arquivo não existe no Drive, tentamos criar um banco novo localmente.
            # Se já existir um DB_PATH local, ele será usado. Caso contrário, será criado por inicializar_tabelas.
            logger.warning(f"Arquivo {DB_NAME} não encontrado no Drive. Tentando usar/criar banco local.")
            if not DB_PATH.exists():
                # Força a criação de um banco novo se não existir localmente nem no Drive
                conn_temp = sqlite3.connect(str(DB_PATH))
                inicializar_tabelas(conn_temp)
                conn_temp.commit()
                conn_temp.close()
                # Marca como dirty para forçar o upload inicial
                if hasattr(_thread_local, 'conn'): # Verifica se a conexão já foi estabelecida
                     _thread_local.dirty = True
                salvar_banco_no_drive(DB_PATH) # Tenta salvar o novo banco no Drive
                logger.info(f"Novo banco de dados local criado e salvo no Drive: {DB_PATH}")
            return DB_PATH

        remote_ts = _remote_modified_ts(file_id)
        global _last_remote_ts
        if DB_PATH.exists() and remote_ts <= _last_remote_ts:
            logger.info("Versão local já está atualizada; download evitado.")
            return DB_PATH
            
        caminho_local = DB_PATH
        gdrive.download_file(file_id, caminho_local)
        _last_remote_ts = remote_ts # Atualiza o timestamp após download bem-sucedido
        logger.info(f"Banco de dados baixado com sucesso: {caminho_local}")
        return caminho_local
    except Exception as e:
        logger.error(f"Erro ao baixar banco do Drive: {str(e)}")
        raise

# ─────────────── Obter conexão com o banco ───────────────
def obter_conexao() -> sqlite3.Connection:
    """Obtém uma conexão com o banco de dados"""
    try:
        # Obtém ou cria a conexão para a thread atual
        if not hasattr(_thread_local, 'conn'):
            caminho_banco = baixar_banco_do_drive()
            novo = not caminho_banco.exists()

            _thread_local.conn = sqlite3.connect(str(caminho_banco))
            _thread_local.conn.row_factory = sqlite3.Row
            _thread_local.dirty = False # Inicializa a flag dirty
            if novo:
                inicializar_tabelas(_thread_local.conn)
                _thread_local.conn.commit()
                # Após inicializar um banco novo, ele está 'sujo' e precisa ser salvo.
                _thread_local.dirty = True 
                salvar_banco_no_drive(caminho_banco)
        
        return _thread_local.conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {str(e)}")
        raise

# ─────────────── Fechar conexão ───────────────
def fechar_conexao():
    """Fecha a conexão da thread atual"""
    if hasattr(_thread_local, 'conn'):
        try:
            _thread_local.conn.close()
        except sqlite3.Error:
            pass
        finally:
            del _thread_local.conn

# ─────────────── Contexto de conexão ───────────────
class ConexaoContext:
    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = obter_conexao()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and getattr(_thread_local, "dirty", False):
            try:
                self.conn.commit()
                # O dirty só é resetado se o commit for bem sucedido E o upload subsequente também for.
                # O upload em salvar_banco_no_drive cuidará de resetar dirty.
            except sqlite3.Error as e:
                logger.error(f"Erro no commit dentro do context manager: {e}")
                # Não reseta dirty, pois o commit falhou.
                pass
        # Fechar a conexão não é feito aqui, pois `obter_conexao` gerencia isso por thread.
        # `fechar_conexao` pode ser chamado explicitamente no final da sessão/aplicação se necessário.

# ─────────────── Função de contexto ───────────────
def conexao():
    """Contexto para gerenciar a conexão com o banco de dados"""
    return ConexaoContext()

# ─────────────── Inicializar tabelas se necessário ───────────────
def inicializar_tabelas(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_nascimento TEXT,
            funcao TEXT,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            tipo TEXT CHECK(tipo IN ('admin', 'ope')) NOT NULL
        );
    """)

    # Verifica se já existe algum usuário admin
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE tipo = 'admin'")
    if cursor.fetchone()[0] == 0:
        # Insere o usuário admin padrão
        cursor.execute("""
            INSERT INTO usuarios (nome, usuario, senha, tipo)
            VALUES (?, ?, ?, ?)
        """, ("Administrador", "admin", "admin123", "admin"))
        logger.info("Usuário admin padrão criado")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_nascimento TEXT,
            cpf TEXT UNIQUE NOT NULL,
            cod_funcionario TEXT UNIQUE NOT NULL,
            funcao TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cnpj TEXT UNIQUE NOT NULL,
            cod_empresa TEXT UNIQUE NOT NULL,
            pasta_empresa TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contratos (
            numero_contrato TEXT PRIMARY KEY,
            cod_empresa TEXT NOT NULL,
            empresa_contratada TEXT,
            titulo TEXT,
            especificacoes TEXT,
            pasta_contrato TEXT,
            FOREIGN KEY(cod_empresa) REFERENCES empresas(cod_empresa)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unidades (
            cod_unidade TEXT PRIMARY KEY,
            numero_contrato TEXT NOT NULL,
            nome_unidade TEXT NOT NULL,
            estado TEXT,
            cidade TEXT,
            localizacao TEXT,
            pasta_unidade TEXT,
            FOREIGN KEY(numero_contrato) REFERENCES contratos(numero_contrato)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servicos (
            cod_servico TEXT PRIMARY KEY,
            cod_unidade TEXT NOT NULL,
            tipo_servico TEXT,
            data_criacao TEXT,
            data_execucao TEXT,
            status TEXT CHECK(status IN ('Ativo', 'Em andamento', 'Pausada', 'Encerrado')),
            observacoes TEXT,
            pasta_servico TEXT,
            FOREIGN KEY(cod_unidade) REFERENCES unidades(cod_unidade)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servico_funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cod_servico TEXT NOT NULL,
            cod_funcionario TEXT NOT NULL,
            FOREIGN KEY(cod_servico) REFERENCES servicos(cod_servico),
            FOREIGN KEY(cod_funcionario) REFERENCES funcionarios(cod_funcionario)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS arquivos_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cod_servico TEXT NOT NULL,
            nome_arquivo TEXT NOT NULL,
            tipo_arquivo TEXT NOT NULL,
            drive_file_id TEXT NOT NULL,
            data_upload TEXT NOT NULL,
            descricao TEXT,
            FOREIGN KEY(cod_servico) REFERENCES servicos(cod_servico)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS arquivos_contrato (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_contrato TEXT NOT NULL,
            nome_arquivo TEXT NOT NULL,
            tipo_arquivo TEXT NOT NULL,
            drive_file_id TEXT NOT NULL,
            data_upload TEXT NOT NULL,
            descricao TEXT,
            FOREIGN KEY(numero_contrato) REFERENCES contratos(numero_contrato)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS arquivos_unidade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cod_unidade TEXT NOT NULL,
            nome_arquivo TEXT NOT NULL,
            tipo_arquivo TEXT NOT NULL,
            drive_file_id TEXT NOT NULL,
            data_upload TEXT NOT NULL,
            descricao TEXT,
            FOREIGN KEY(cod_unidade) REFERENCES unidades(cod_unidade)
        );
    """)

# ─────────────── Enviar/atualizar banco no Drive ───────────────
def salvar_banco_no_drive(caminho_banco: Path):
    """Salva o banco de dados no Google Drive"""
    try:
        # Usa True como default para getattr para garantir que, se a flag não existir por algum motivo,
        # ele tente salvar (comportamento seguro), especialmente na primeira execução ou após reinício.
        if not getattr(_thread_local, "dirty", True):
            logger.info("Nenhuma alteração local pendente (_thread_local.dirty=False); upload para o Drive evitado.")
            return

        folder_id = _get_drive_folder_id()
        logger.info(f"Usando pasta do Drive: {folder_id}")

        file_id = gdrive.get_file_id_by_name(DB_NAME, folder_id)
        
        # Antes de fazer upload/update, verifica se o arquivo remoto não foi modificado por outro processo.
        if file_id:
            remote_ts_before_upload = _remote_modified_ts(file_id)
            if remote_ts_before_upload > _last_remote_ts:
                logger.warning(f"CONFLITO DETECTADO: O arquivo no Drive ({remote_ts_before_upload}) é mais novo que a última sincronização local ({_last_remote_ts}). Upload abortado para evitar perda de dados.")
                # Aqui, uma estratégia de resolução de conflitos mais elaborada poderia ser implementada.
                # Por ora, apenas logamos e evitamos a sobrescrita.
                # Opcionalmente, poderia levantar uma exceção para o chamador tratar.
                st.error("❌ CONFLITO: O banco de dados no servidor foi modificado por outra sessão. Suas alterações não foram salvas para evitar perda de dados. Por favor, recarregue e tente novamente.")
                return 

        if file_id:
            gdrive.update_file(file_id, str(caminho_banco))
            logger.info("Banco atualizado no Google Drive")
        else:
            gdrive.upload_file(str(caminho_banco), folder_id)
            logger.info("Banco enviado ao Google Drive")
        
        _thread_local.dirty = False # Upload bem-sucedido, banco não está mais sujo
        _last_remote_ts = time.time() # Agora somos a versão mais nova

    except Exception as e:
        logger.error(f"Erro ao salvar banco no Drive: {str(e)}")
        raise

# ─────────────── Atualizar banco de dados ───────────────
def atualizar_banco():
    """Atualiza o banco de dados criando novas tabelas se necessário"""
    conn = obter_conexao() # _thread_local.dirty será False aqui inicialmente
    cursor = conn.cursor()
    schema_changed = False
    
    # Verifica se a tabela empresas tem o campo pasta_empresa
    cursor.execute("PRAGMA table_info(empresas)")
    colunas = [col[1] for col in cursor.fetchall()]
    if 'pasta_empresa' not in colunas:
        print("📝 Adicionando campo pasta_empresa à tabela empresas...")
        cursor.execute("ALTER TABLE empresas ADD COLUMN pasta_empresa TEXT")
        schema_changed = True
    
    # Verifica se a tabela contratos tem o campo pasta_contrato
    cursor.execute("PRAGMA table_info(contratos)")
    colunas = [col[1] for col in cursor.fetchall()]
    if 'pasta_contrato' not in colunas:
        print("📝 Adicionando campo pasta_contrato à tabela contratos...")
        cursor.execute("ALTER TABLE contratos ADD COLUMN pasta_contrato TEXT")
        schema_changed = True
    
    # Verifica se a tabela unidades tem o campo pasta_unidade
    cursor.execute("PRAGMA table_info(unidades)")
    colunas = [col[1] for col in cursor.fetchall()]
    if 'pasta_unidade' not in colunas:
        print("📝 Adicionando campo pasta_unidade à tabela unidades...")
        cursor.execute("ALTER TABLE unidades ADD COLUMN pasta_unidade TEXT")
        schema_changed = True
    
    # Verifica se a tabela servicos tem o campo pasta_servico
    cursor.execute("PRAGMA table_info(servicos)")
    colunas = [col[1] for col in cursor.fetchall()]
    if 'pasta_servico' not in colunas:
        print("📝 Adicionando campo pasta_servico à tabela servicos...")
        cursor.execute("ALTER TABLE servicos ADD COLUMN pasta_servico TEXT")
        schema_changed = True
    
    # Verifica se a tabela servico_funcionarios existe
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='servico_funcionarios'
    """)
    if not cursor.fetchone():
        print("📝 Criando tabela servico_funcionarios...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS servico_funcionarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cod_servico TEXT NOT NULL,
                cod_funcionario TEXT NOT NULL,
                FOREIGN KEY(cod_servico) REFERENCES servicos(cod_servico),
                FOREIGN KEY(cod_funcionario) REFERENCES funcionarios(cod_funcionario)
            );
        """)
        schema_changed = True
    
    # Verifica se as tabelas de arquivos existem
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='arquivos_servico'
    """)
    if not cursor.fetchone():
        print("📝 Criando tabela arquivos_servico...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS arquivos_servico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cod_servico TEXT NOT NULL,
                nome_arquivo TEXT NOT NULL,
                tipo_arquivo TEXT NOT NULL,
                drive_file_id TEXT NOT NULL,
                data_upload TEXT NOT NULL,
                descricao TEXT,
                FOREIGN KEY(cod_servico) REFERENCES servicos(cod_servico)
            );
        """)
        schema_changed = True

    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='arquivos_contrato'
    """)
    if not cursor.fetchone():
        print("📝 Criando tabela arquivos_contrato...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS arquivos_contrato (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_contrato TEXT NOT NULL,
                nome_arquivo TEXT NOT NULL,
                tipo_arquivo TEXT NOT NULL,
                drive_file_id TEXT NOT NULL,
                data_upload TEXT NOT NULL,
                descricao TEXT,
                FOREIGN KEY(numero_contrato) REFERENCES contratos(numero_contrato)
            );
        """)
        schema_changed = True

    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='arquivos_unidade'
    """)
    if not cursor.fetchone():
        print("📝 Criando tabela arquivos_unidade...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS arquivos_unidade (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cod_unidade TEXT NOT NULL,
                nome_arquivo TEXT NOT NULL,
                tipo_arquivo TEXT NOT NULL,
                drive_file_id TEXT NOT NULL,
                data_upload TEXT NOT NULL,
                descricao TEXT,
                FOREIGN KEY(cod_unidade) REFERENCES unidades(cod_unidade)
            );
        """)
        schema_changed = True

    if schema_changed:
        _thread_local.dirty = True # Marca como sujo se o esquema mudou

    conn.commit() # Commit local das alterações de esquema
    
    # Só salva no drive se algo mudou no esquema (ou se já estava dirty por outro motivo)
    if getattr(_thread_local, "dirty", False):
        salvar_banco_no_drive(Path(tempfile.gettempdir()) / DB_NAME)
    
    print("✅ Banco de dados atualizado com sucesso!")

# ─────────────── Execução isolada ───────────────
if __name__ == "__main__":
    # Para execução isolada, certifique-se que o st.session_state e st.secrets podem não estar disponíveis.
    # Você pode precisar mocká-los ou usar valores padrão diretamente aqui se for testar _get_drive_folder_id
    # ou outras funções dependentes do Streamlit.
    
    # Exemplo de mock básico se st não estiver disponível (apenas para __main__):
    if 'streamlit' not in sys.modules:
        class MockStreamlit:
            def __init__(self):
                self.session_state = {}
                self.secrets = {"gdrive": {"database_folder_id": "ID_PASTA_DRIVE_PADRAO_TESTE"}} # Exemplo
        st = MockStreamlit()

    conn = obter_conexao()
    print("✅ Banco de dados pronto para uso.")
    atualizar_banco()  # Atualiza o banco ao executar o script
