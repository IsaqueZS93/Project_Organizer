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

# Cache de conexão por thread
_thread_local = threading.local()
_last_download = None

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
        # Verifica se as variáveis do Google Drive estão configuradas
        if "GDRIVE_DATABASE_FOLDER_ID" not in st.session_state:
            raise Exception("GDRIVE_DATABASE_FOLDER_ID não está configurado no session_state")
            
        folder_id = st.session_state["GDRIVE_DATABASE_FOLDER_ID"]
        logger.info(f"Usando pasta do Drive: {folder_id}")
            
        file_id = gdrive.get_file_id_by_name(DB_NAME, folder_id)
        if not file_id:
            raise Exception(f"Arquivo {DB_NAME} não encontrado no Drive")
            
        caminho_local = DB_PATH
        gdrive.download_file(file_id, caminho_local)
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
            if novo:
                inicializar_tabelas(_thread_local.conn)
                _thread_local.conn.commit()
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
        if exc_type is None:
            try:
                self.conn.commit()
            except sqlite3.Error:
                pass

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
        # Verifica se as variáveis do Google Drive estão configuradas
        if "GDRIVE_DATABASE_FOLDER_ID" not in st.session_state:
            raise Exception("GDRIVE_DATABASE_FOLDER_ID não está configurado no session_state")
            
        folder_id = st.session_state["GDRIVE_DATABASE_FOLDER_ID"]
        logger.info(f"Usando pasta do Drive: {folder_id}")

        file_id = gdrive.get_file_id_by_name(DB_NAME, folder_id)
        if file_id:
            gdrive.update_file(file_id, str(caminho_banco))
            logger.info("Banco atualizado no Google Drive")
        else:
            gdrive.upload_file(str(caminho_banco), folder_id)
            logger.info("Banco enviado ao Google Drive")
    except Exception as e:
        logger.error(f"Erro ao salvar banco no Drive: {str(e)}")
        raise

# ─────────────── Atualizar banco de dados ───────────────
def atualizar_banco():
    """Atualiza o banco de dados criando novas tabelas se necessário"""
    conn = obter_conexao()
    cursor = conn.cursor()
    
    # Verifica se a tabela empresas tem o campo pasta_empresa
    cursor.execute("PRAGMA table_info(empresas)")
    colunas = [col[1] for col in cursor.fetchall()]
    if 'pasta_empresa' not in colunas:
        print("📝 Adicionando campo pasta_empresa à tabela empresas...")
        cursor.execute("ALTER TABLE empresas ADD COLUMN pasta_empresa TEXT")
    
    # Verifica se a tabela contratos tem o campo pasta_contrato
    cursor.execute("PRAGMA table_info(contratos)")
    colunas = [col[1] for col in cursor.fetchall()]
    if 'pasta_contrato' not in colunas:
        print("📝 Adicionando campo pasta_contrato à tabela contratos...")
        cursor.execute("ALTER TABLE contratos ADD COLUMN pasta_contrato TEXT")
    
    # Verifica se a tabela unidades tem o campo pasta_unidade
    cursor.execute("PRAGMA table_info(unidades)")
    colunas = [col[1] for col in cursor.fetchall()]
    if 'pasta_unidade' not in colunas:
        print("📝 Adicionando campo pasta_unidade à tabela unidades...")
        cursor.execute("ALTER TABLE unidades ADD COLUMN pasta_unidade TEXT")
    
    # Verifica se a tabela servicos tem o campo pasta_servico
    cursor.execute("PRAGMA table_info(servicos)")
    colunas = [col[1] for col in cursor.fetchall()]
    if 'pasta_servico' not in colunas:
        print("📝 Adicionando campo pasta_servico à tabela servicos...")
        cursor.execute("ALTER TABLE servicos ADD COLUMN pasta_servico TEXT")
    
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

    conn.commit()
    caminho_banco = Path(tempfile.gettempdir()) / DB_NAME
    salvar_banco_no_drive(caminho_banco)
    print("✅ Banco de dados atualizado com sucesso!")

# ─────────────── Execução isolada ───────────────
if __name__ == "__main__":
    conn = obter_conexao()
    print("✅ Banco de dados pronto para uso.")
    atualizar_banco()  # Atualiza o banco ao executar o script
