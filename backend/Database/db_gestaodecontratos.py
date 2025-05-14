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
# _last_remote_ts: float = 0.0   # Removido - será usado st.session_state

# Cache de conexão por thread
_thread_local = threading.local()

def marca_sujo() -> None:
    """Marca o banco como modificado na thread atual."""
    setattr(_thread_local, "dirty", True)

def _remote_modified_ts(file_id: str) -> float:
    """Obtém o timestamp de modificação de um arquivo no Google Drive."""
    st.session_state.setdefault("last_remote_ts", 0.0)
    
    meta = gdrive.get_service().files().get(
        fileId=file_id, fields="modifiedTime"
    ).execute()
    ts_string = meta["modifiedTime"].split('.')[0] 
    return time.mktime(time.strptime(ts_string, "%Y-%m-%dT%H:%M:%S"))

def _get_drive_folder_id():
    """Obtém o ID da pasta do Drive do session_state ou do secrets.toml"""
    try:
        if "GDRIVE_DATABASE_FOLDER_ID" in st.session_state:
            return st.session_state["GDRIVE_DATABASE_FOLDER_ID"]
        if "gdrive" in st.secrets and "database_folder_id" in st.secrets["gdrive"]:
            folder_id = st.secrets["gdrive"]["database_folder_id"]
            st.session_state["GDRIVE_DATABASE_FOLDER_ID"] = folder_id
            return folder_id
        default_id = "1OwkYVqfY8jRaYvZzhW9MkekJAGKSqbPX"
        st.session_state["GDRIVE_DATABASE_FOLDER_ID"] = default_id
        return default_id
    except Exception as e:
        logger.error(f"Erro ao obter folder_id: {str(e)}")
        return "1OwkYVqfY8jRaYvZzhW9MkekJAGKSqbPX"

def autenticar_usuario(usuario: str, senha: str) -> tuple[bool, str, str]:
    """Autentica um usuário no sistema"""
    conn = None
    try:
        caminho_banco = baixar_banco_do_drive()
        conn = sqlite3.connect(str(caminho_banco))
        cursor = conn.cursor()
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
        
        st.session_state.setdefault("last_remote_ts", 0.0)
            
        file_id = gdrive.get_file_id_by_name(DB_NAME, folder_id)
        if not file_id:
            logger.warning(f"Arquivo {DB_NAME} não encontrado no Drive. Tentando usar/criar banco local.")
            if not DB_PATH.exists():
                conn_temp = sqlite3.connect(str(DB_PATH))
                inicializar_tabelas(conn_temp)
                conn_temp.commit()
                conn_temp.close()
                logger.info(f"Novo banco de dados local criado: {DB_PATH}. Será enviado ao Drive na próxima operação de escrita.")
            return DB_PATH

        remote_ts = _remote_modified_ts(file_id)
        
        if DB_PATH.exists() and remote_ts <= st.session_state.get("last_remote_ts", 0.0):
            logger.info("Versão local já está atualizada; download evitado.")
            return DB_PATH
            
        caminho_local = DB_PATH
        gdrive.download_file(file_id, caminho_local)
        st.session_state["last_remote_ts"] = remote_ts
        logger.info(f"Banco de dados baixado com sucesso: {caminho_local}")
        return caminho_local
    except Exception as e:
        logger.error(f"Erro ao baixar banco do Drive: {str(e)}")
        raise

# ─────────────── Obter conexão com o banco ───────────────
def obter_conexao() -> sqlite3.Connection:
    """Obtém uma conexão com o banco de dados"""
    try:
        if not hasattr(_thread_local, 'conn') or _thread_local.conn is None:
            caminho_banco_local = baixar_banco_do_drive()
            novo = not caminho_banco_local.exists() or caminho_banco_local.stat().st_size == 0

            _thread_local.conn = sqlite3.connect(str(caminho_banco_local))
            _thread_local.conn.row_factory = sqlite3.Row
            _thread_local.dirty = False 
            
            if novo:
                logger.info(f"Banco de dados não encontrado ou vazio em {caminho_banco_local}, inicializando tabelas.")
                inicializar_tabelas(_thread_local.conn)
                _thread_local.conn.commit()
                _thread_local.dirty = True 
                logger.info("Banco de dados inicializado e marcado como 'dirty'. Será salvo no Drive na próxima operação de escrita.")
        
        return _thread_local.conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {str(e)}")
        raise

# ─────────────── Fechar conexão ───────────────
def fechar_conexao():
    """Fecha a conexão da thread atual"""
    if hasattr(_thread_local, 'conn') and _thread_local.conn is not None: # Adicionado cheque de None
        try:
            _thread_local.conn.close()
        except sqlite3.Error:
            pass # Pode já estar fechada ou em estado inválido
        finally:
            # Remove conn de _thread_local para que obter_conexao() crie uma nova na próxima vez.
            delattr(_thread_local, 'conn') 
            if hasattr(_thread_local, 'dirty'): # Limpa a flag dirty também se existir
                delattr(_thread_local, 'dirty')


# ─────────────── Contexto de conexão ───────────────
class ConexaoContext:
    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = obter_conexao()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            # Só faz commit se não houve exceção DENTRO do bloco 'with' E se o banco está 'dirty'.
            if exc_type is None and getattr(_thread_local, "dirty", False):
                try:
                    self.conn.commit()
                    logger.info("Commit realizado pelo ConexaoContext.")
                except sqlite3.Error as e_commit:
                    logger.error(f"Erro no commit dentro do context manager: {e_commit}")
                    # Se não havia uma exceção original (exc_val is None),
                    # propaga o erro do commit. Caso contrário, a exceção original (exc_val)
                    # já será propagada automaticamente ao sair do __exit__.
                    if exc_val is None: 
                        raise e_commit # Propaga o erro de commit como a exceção primária.
            # Se uma exceção ocorreu no bloco 'with' (exc_type is not None), o commit não é tentado.
            # A flag 'dirty' permanecerá True (correto, pois as alterações não foram salvas).
            # Se não estava 'dirty', nada precisa ser feito em termos de commit.
        finally:
            # Reseta a flag 'dirty' ao sair do contexto, independentemente de commit ou exceção.
            # Esta é a principal mudança solicitada: garantir que 'dirty' seja False para a próxima
            # vez que o contexto for usado no mesmo thread, a menos que uma nova operação de escrita ocorra.
            setattr(_thread_local, "dirty", False)
            logger.debug("Flag 'dirty' resetada para False ao sair do ConexaoContext.")
        # A conexão não é fechada aqui; fechar_conexao() pode ser chamado explicitamente.

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

    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE tipo = 'admin'")
    if cursor.fetchone()[0] == 0:
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_contrato TEXT UNIQUE NOT NULL,
            cod_empresa TEXT NOT NULL,
            empresa_contratada TEXT,
            titulo TEXT,
            especificacoes TEXT,
            pasta_contrato TEXT,
            FOREIGN KEY (cod_empresa) REFERENCES empresas(cod_empresa) ON DELETE CASCADE 
        );
    """)
    # Adicionado ON DELETE CASCADE para cod_empresa

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cod_unidade TEXT UNIQUE NOT NULL,
            numero_contrato TEXT NOT NULL,
            nome_unidade TEXT,
            estado TEXT,
            cidade TEXT,
            localizacao TEXT,
            pasta_unidade TEXT,
            FOREIGN KEY (numero_contrato) REFERENCES contratos(numero_contrato) ON DELETE CASCADE
        );
    """)
    # Adicionado ON DELETE CASCADE para numero_contrato

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cod_servico TEXT UNIQUE NOT NULL,
            cod_unidade TEXT NOT NULL,
            descricao TEXT,
            data_prevista TEXT,
            data_execucao TEXT,
            status TEXT,
            observacoes TEXT,
            pasta_servico TEXT, -- ID da pasta do serviço no Drive
            nome_arquivo_original TEXT, -- Nome original do arquivo de upload
            id_arquivo_drive TEXT, -- ID do arquivo específico no Drive
            FOREIGN KEY (cod_unidade) REFERENCES unidades(cod_unidade) ON DELETE CASCADE
        );
    """)
    # Adicionado ON DELETE CASCADE para cod_unidade

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servico_funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cod_servico TEXT NOT NULL,
            cod_funcionario TEXT NOT NULL,
            FOREIGN KEY (cod_servico) REFERENCES servicos(cod_servico) ON DELETE CASCADE,
            FOREIGN KEY (cod_funcionario) REFERENCES funcionarios(cod_funcionario) ON DELETE CASCADE,
            UNIQUE (cod_servico, cod_funcionario)
        );
    """)
    # Adicionado ON DELETE CASCADE para cod_servico e cod_funcionario

    conn.commit()
    logger.info("Tabelas inicializadas/verificadas.")


# ───────────────── Salvar Banco de Dados no Google Drive ─────────────────
def salvar_banco_no_drive(caminho_banco: Path):
    """Salva o banco de dados local no Google Drive se estiver marcado como 'dirty' e não houver conflitos."""
    st.session_state.setdefault("last_remote_ts", 0.0)

    if not getattr(_thread_local, "dirty", False):
        logger.info("Banco de dados não está 'dirty', upload para o Drive evitado.")
        return

    try:
        folder_id = _get_drive_folder_id()
        file_id = gdrive.get_file_id_by_name(DB_NAME, folder_id)

        if file_id:
            remote_ts_before_upload = _remote_modified_ts(file_id)
            if remote_ts_before_upload > st.session_state.get("last_remote_ts", 0.0):
                logger.warning(
                    f"CONFLITO DETECTADO: Versão do banco no Drive (ts: {remote_ts_before_upload}) "
                    f"é mais nova que a última versão conhecida localmente (ts: {st.session_state.get('last_remote_ts', 0.0)}). "
                    f"Upload abortado para evitar perda de dados."
                )
                # Mostrar erro para o usuário no Streamlit
                # É crucial que esta mensagem seja visível se stiver em um contexto Streamlit
                if hasattr(st, 'error'):
                    st.error(f"Conflito ao salvar: alterações remotas detectadas. Suas últimas alterações não foram salvas na nuvem para evitar sobrescrever dados. Por favor, recarregue a página e tente novamente.")
                return # Aborta o upload

            logger.info(f"Atualizando arquivo {DB_NAME} no Drive.")
            gdrive.update_file(file_id, caminho_banco)
            logger.info(f"Arquivo {DB_NAME} atualizado no Drive.")
        else:
            logger.info(f"Enviando novo arquivo {DB_NAME} para o Drive.")
            file_id = gdrive.upload_file(caminho_banco, folder_id) # Salva o file_id retornado
            if not file_id:
                logger.error(f"Falha ao fazer upload do novo arquivo {DB_NAME} para o Drive.")
                return # Aborta se o upload falhar
            logger.info(f"Novo arquivo {DB_NAME} enviado ao Drive com ID: {file_id}.")
        
        # Atualiza o timestamp da última versão remota conhecida com o timestamp do arquivo que acabou de ser salvo/criado.
        # Isso é importante para a próxima verificação de conflito.
        if file_id: # Garante que file_id não é None (caso upload_file falhe e retorne None)
             new_remote_ts = _remote_modified_ts(file_id)
             st.session_state["last_remote_ts"] = new_remote_ts
             logger.info(f"Timestamp remoto atualizado para: {new_remote_ts}")
        else: # Caso de falha no upload inicial onde file_id pode não ser retornado.
             st.session_state["last_remote_ts"] = time.time() # Fallback para tempo atual
             logger.warning("Não foi possível obter o file_id após o upload, usando time.time() para last_remote_ts.")

        # A flag 'dirty' agora é resetada no __exit__ do ConexaoContext.
        # setattr(_thread_local, "dirty", False) # Upload bem-sucedido, banco não está mais sujo (movido)

    except gdrive.googleapiclient.errors.HttpError as e:
        logger.error(f"Erro de API do Google ao salvar banco no Drive: {str(e)}")
        if hasattr(st, 'error'):
            st.error(f"Erro de API ao salvar no Google Drive: {e}. Suas alterações podem não ter sido salvas na nuvem.")
        # Não levanta a exceção para não quebrar a aplicação, mas o erro é logado e mostrado ao usuário.
        # A flag 'dirty' permanecerá True, então a próxima tentativa de salvar_banco_no_drive tentará novamente.
    except Exception as e:
        logger.error(f"Erro inesperado ao salvar banco no Drive: {str(e)}")
        if hasattr(st, 'error'):
            st.error(f"Erro inesperado ao salvar no Google Drive: {e}. Suas alterações podem não ter sido salvas na nuvem.")
        # Similarmente, não levanta a exceção. 'dirty' permanece True.

# Função para atualizar o esquema do banco de dados (se necessário)
def atualizar_banco():
    """Verifica e atualiza o esquema do banco de dados se necessário."""
    # Esta função pode ser expandida para lidar com migrações de esquema mais complexas.
    # Por enquanto, apenas garante que todas as tabelas sejam criadas.
    try:
        with conexao() as conn: # Usa o contexto de conexão
            # A verificação/criação de tabelas já define 'dirty' se algo mudar
            inicializar_tabelas(conn) 
            # O commit e o reset de dirty são gerenciados pelo ConexaoContext e salvar_banco_no_drive
        
        # Se inicializar_tabelas marcou como dirty, tenta salvar.
        if getattr(_thread_local, "dirty", False):
             # Se o contexto resetou, mas inicializar_tabelas FEZ algo, precisamos marcar de novo
             # No entanto, inicializar_tabelas já faz commit.
             # A questão é se o schema MUDOU e precisa de upload.
             # A lógica atual: se `inicializar_tabelas` faz um commit, o context manager fará o commit.
             # Se o context manager comitou, `dirty` estava True. `salvar_banco_no_drive` será chamado pelos models.
             # Esta função `atualizar_banco` pode não precisar chamar `salvar_banco_no_drive` explicitamente
             # se as chamadas de `inicializar_tabelas` já marcam `dirty` e os models chamam `salvar_banco_no_drive`.
             # Contudo, para uma atualização de esquema explícita, pode ser bom forçar.
             
             # Se o objetivo é apenas garantir que o esquema está atualizado E salvo no Drive:
             # 1. Abrir conexão (feito)
             # 2. Rodar inicializar_tabelas (feito, comita internamente se criar algo)
             # 3. Se inicializar_tabelas criou algo, o banco está tecnicamente 'dirty' para o Drive.
             # A flag _thread_local.dirty será True dentro de inicializar_tabelas se algo for criado (devido ao commit).
             # O ConexaoContext comitará e resetará dirty.
             # Para forçar o salvamento APÓS uma atualização de esquema:
             logger.info("Esquema do banco verificado/atualizado. Tentando salvar no Drive se houver alterações pendentes.")
             # Re-marca como dirty aqui para garantir que salvar_banco_no_drive faça o upload
             # Isso é necessário porque o ConexaoContext já resetou a flag.
             # No entanto, isso pode levar a uploads desnecessários se o schema já estava atualizado.
             # Uma flag de "schema_changed" seria melhor.
             
             # Melhoria: inicializar_tabelas poderia retornar um booleano se o esquema mudou.
             # Por ora, vamos simplificar. A chamada abaixo tentará salvar se _thread_local.dirty for True.
             # Se o contexto já limpou, e não houve outras escritas, não salvará.
             # Se inicializar_tabelas realmente ALTEROU o esquema, ela DEVE marcar dirty.

             pass # A lógica de salvar é melhor nos models após operações de escrita.
                  # Ou, se esta função é chamada em um ponto que DEVE sincronizar:
             # marca_sujo() # Se tem certeza que quer forçar um check/save
             # salvar_banco_no_drive(DB_PATH)

        logger.info("Verificação/atualização do banco de dados concluída.")
    except Exception as e:
        logger.error(f"Erro ao atualizar banco de dados: {str(e)}")
        # Considerar se deve levantar a exceção ou apenas logar.

# Função para popular o banco de dados com exemplos (para desenvolvimento)

if __name__ == "__main__":
    # Mock para st.secrets e st.session_state para testes locais
    class MockStreamlit:
        def __init__(self):
            self.secrets = {
                "gdrive": {"database_folder_id": "TEST_DB_FOLDER_ID"},
                "db_path_readonly": "", 
                "db_readonly_queried": False 
            }
            self.session_state = {} # last_remote_ts será inicializado por setdefault

        def __getattr__(self, name):
            # Para simular st.text_input, st.button, etc., retornando um mock simples
            if name not in self.session_state:
                # self.session_state[name] = None # Não popular dinamicamente
                def mock_function(*args, **kwargs):
                    print(f"Mocked st.{name} called with args: {args} kwargs: {kwargs}")
                    # Tenta retornar um valor padrão que não quebre chamadas comuns
                    if "key" in kwargs: return self.session_state.get(kwargs["key"])
                    if name in ["button", "checkbox"]: return False
                    if name in ["text_input", "text_area", "selectbox", "date_input"]: return None
                    return None 
                return mock_function
            return self.session_state[name]

    st = MockStreamlit()
    st.session_state.setdefault("last_remote_ts", 0.0) # Garante a inicialização

    logger.info("Executando em modo de teste...")
    
    # Teste de limpeza de conexão
    logger.info("Testando ciclo de conexão e limpeza...")
    with conexao() as conn_test:
        logger.info(f"Conexão obtida: {conn_test}")
        cursor = conn_test.cursor()
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        logger.info(f"Contagem de usuários: {cursor.fetchone()[0]}")
        # Simula uma escrita para testar a flag dirty
        # marca_sujo() 
        # logger.info(f"Após marca_sujo, _thread_local.dirty: {getattr(_thread_local, 'dirty', 'N/A')}")
    logger.info(f"Após sair do contexto, _thread_local.dirty: {getattr(_thread_local, 'dirty', 'N/A')}") # Deve ser False

    fechar_conexao() # Testa o fechamento explícito
    logger.info(f"Após fechar_conexao, hasattr(_thread_local, 'conn'): {hasattr(_thread_local, 'conn')}") # Deve ser False

    logger.info("Reabrindo conexão para teste...")
    with conexao() as conn_test_2:
        logger.info(f"Segunda conexão obtida: {conn_test_2}")
        logger.info(f"Na segunda conexão, _thread_local.dirty: {getattr(_thread_local, 'dirty', 'N/A')}") # Deve ser False
    logger.info(f"Após sair do segundo contexto, _thread_local.dirty: {getattr(_thread_local, 'dirty', 'N/A')}") # Deve ser False


    # Exemplo: Como usar obter_conexao e fechar_conexao sem o context manager
    # logger.info("Testando obter_conexao e fechar_conexao manualmente...")
    # conn_manual = obter_conexao()
    # try:
    #     logger.info(f"Conexão manual: {conn_manual}, dirty: {getattr(_thread_local, 'dirty', 'N/A')}")
    #     # conn_manual.execute("INSERT INTO usuarios (nome, usuario, senha, tipo) VALUES ('Test', 'testuser', 'test', 'ope')")
    #     # marca_sujo()
    #     # logger.info(f"Após escrita manual, dirty: {getattr(_thread_local, 'dirty', 'N/A')}")
    #     # conn_manual.commit() # Commit manual necessário se não usar o contexto e dirty=True
    #     # logger.info("Commit manual realizado.")
    # except Exception as e:
    #     logger.error(f"Erro no teste manual: {e}")
    #     # conn_manual.rollback() # Rollback em caso de erro
    # finally:
    #     # Se não usou contexto, e fez commit/rollback, resetar dirty manualmente se necessário
    #     # setattr(_thread_local, "dirty", False) 
    #     fechar_conexao()
    # logger.info(f"Após fechar conexão manual, hasattr(_thread_local, 'conn'): {hasattr(_thread_local, 'conn')}")
    
    logger.info("Testes básicos concluídos.")
