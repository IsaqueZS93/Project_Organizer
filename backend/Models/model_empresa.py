# backend/Models/model_empresa.py

import sqlite3
from typing import List, Optional, Tuple
from pathlib import Path
import sys
import os
import logging
from tempfile import gettempdir
import streamlit as st

# Adiciona o caminho para importar banco e serviço do Drive
sys.path.append(str(Path(__file__).resolve().parents[1]))
from Database import db_gestaodecontratos as db
from Services import Service_googledrive as gdrive

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ───────────────── CRUD de Empresas com Drive ─────────────────

def criar_empresa(nome: str, cnpj: str, cod_empresa: str) -> bool:
    """Cria uma nova empresa no banco de dados e no Google Drive"""
    try:
        logger.info(f"Iniciando criação da empresa: {cod_empresa} - {nome}")
        empresas_root_folder_id = st.session_state.get("GDRIVE_EMPRESAS_FOLDER_ID")
        if not empresas_root_folder_id:
            logger.error("ID da pasta raiz de empresas (GDRIVE_EMPRESAS_FOLDER_ID) não encontrado no session_state.")
            st.error("Configuração crítica ausente: ID da pasta raiz de empresas não definido.")
            return False

        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM empresas WHERE cnpj = ? OR cod_empresa = ?", (cnpj, cod_empresa))
            if cursor.fetchone():
                logger.warning(f"Tentativa de criar empresa com CNPJ ({cnpj}) ou Código ({cod_empresa}) duplicado.")
                st.warning(f"Já existe uma empresa com este CNPJ ou Código.")
                return False

            # Cria a pasta no Drive ANTES de inserir no banco, para garantir que o ID da pasta exista.
            pasta_empresa_id = gdrive.ensure_folder(nome, empresas_root_folder_id)
            if not pasta_empresa_id:
                logger.error(f"Erro ao criar a pasta para a empresa {nome} no Drive.")
                st.error(f"Não foi possível criar a pasta da empresa no Google Drive.")
                return False
            logger.info(f"Pasta da empresa {nome} criada/assegurada no Drive com ID: {pasta_empresa_id}")

            cursor.execute("""
                INSERT INTO empresas (nome, cnpj, cod_empresa, pasta_empresa)
                VALUES (?, ?, ?, ?)
            """, (nome, cnpj, cod_empresa, pasta_empresa_id))
            db.marca_sujo()
            logger.info(f"Empresa {cod_empresa} - {nome} inserida no banco de dados.")

        caminho_banco_local = Path(gettempdir()) / db.DB_NAME
        try:
            db.salvar_banco_no_drive(caminho_banco_local)
            logger.info(f"Banco de dados salvo no Drive após criação da empresa {cod_empresa}.")
            return True
        except Exception as e_save:
            logger.error(f"Erro ao salvar banco no Drive após criar empresa {cod_empresa}: {e_save}")
            # Mesmo com erro no Drive, a operação no banco local e a criação da pasta no Drive foram bem-sucedidas.
            # A flag 'dirty' permanece, então a próxima sincronização tentará salvar.
            return True 
            
    except Exception as e_main:
        logger.error(f"Erro geral ao criar empresa {cod_empresa} - {nome}: {e_main}")
        st.error(f"Ocorreu um erro inesperado ao criar a empresa: {e_main}")
        return False


def listar_empresas() -> List[Tuple]:
    """Lista todas as empresas cadastradas"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cod_empresa, nome, cnpj, pasta_empresa FROM empresas ORDER BY nome")
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Erro ao listar empresas: {e}")
        return []


def buscar_empresa_por_codigo(cod_empresa: str) -> Optional[Tuple]:
    """Busca uma empresa pelo código"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM empresas WHERE cod_empresa = ?", (cod_empresa,))
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Erro ao buscar empresa {cod_empresa}: {e}")
        return None


def atualizar_empresa(cod_empresa_original: str, novo_nome: str, novo_cnpj: str) -> bool:
    """Atualiza os dados de uma empresa"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            # Verificar duplicação de CNPJ para outras empresas
            cursor.execute("SELECT id FROM empresas WHERE cnpj = ? AND cod_empresa != ?", (novo_cnpj, cod_empresa_original))
            if cursor.fetchone():
                logger.warning(f"Tentativa de atualizar empresa {cod_empresa_original} para CNPJ ({novo_cnpj}) duplicado.")
                st.warning("Já existe outra empresa com este CNPJ.")
                return False
            
            # Obter nome e ID da pasta antiga para possível renomeação no Drive
            cursor.execute("SELECT nome, pasta_empresa FROM empresas WHERE cod_empresa = ?", (cod_empresa_original,))
            res_empresa_antiga = cursor.fetchone()
            if not res_empresa_antiga:
                logger.error(f"Empresa {cod_empresa_original} não encontrada para atualização.")
                st.error("Empresa não encontrada para atualização.")
                return False
            nome_antigo, pasta_empresa_id_antiga = res_empresa_antiga

            # Renomear pasta no Drive se o nome da empresa mudou e a pasta existe
            if novo_nome != nome_antigo and pasta_empresa_id_antiga:
                if gdrive.rename_file(pasta_empresa_id_antiga, novo_nome):
                    logger.info(f"Pasta da empresa {nome_antigo} (ID: {pasta_empresa_id_antiga}) renomeada para {novo_nome} no Drive.")
                else:
                    logger.warning(f"Falha ao renomear pasta da empresa {nome_antigo} para {novo_nome} no Drive. A atualização do banco prosseguirá.")
                    # Considerar se isso deve ser um erro bloqueante.

            cursor.execute("""
                UPDATE empresas SET nome = ?, cnpj = ?
                WHERE cod_empresa = ?
            """, (novo_nome, novo_cnpj, cod_empresa_original))
            
            if cursor.rowcount > 0:
                db.marca_sujo()
            else:
                # Se o nome mudou e a pasta foi renomeada, mas os outros dados não, ainda pode ser considerado uma operação.
                # No entanto, se rowcount é 0, significa que o cod_empresa não foi encontrado ou nome e cnpj eram iguais.
                # Se o nome mudou E a pasta foi renomeada com sucesso, mas os outros dados do banco não mudaram (já eram iguais),
                # o banco não estará sujo por esta operação SQL, mas a intenção foi uma atualização.
                # Para simplificar, se rowcount=0, consideramos que não houve mudança efetiva no *banco*.
                logger.info(f"Nenhuma empresa encontrada com o código {cod_empresa_original} para atualizar, ou os dados são os mesmos.")
                # Se apenas a pasta foi renomeada, mas os dados do banco não mudaram, o banco não fica sujo.
                # Se for desejado que a renomeação da pasta suje o banco (para log ou algo assim), adicionar db.marca_sujo() após a renomeação.
                return True 

        if getattr(db._thread_local, "dirty", False):
            caminho_banco_local = Path(gettempdir()) / db.DB_NAME
            try:
                db.salvar_banco_no_drive(caminho_banco_local)
                logger.info(f"Empresa {cod_empresa_original} atualizada e banco salvo.")
            except Exception as e_save:
                logger.error(f"Erro ao salvar banco no Drive após atualizar empresa {cod_empresa_original}: {e_save}")
                return True # Operação local no banco bem-sucedida
        return True
            
    except Exception as e_main:
        logger.error(f"Erro ao atualizar empresa {cod_empresa_original}: {e_main}")
        st.error(f"Ocorreu um erro inesperado ao atualizar a empresa: {e_main}")
        return False


def deletar_empresa(cod_empresa: str) -> bool:
    """Deleta uma empresa"""
    try:
        # Verificar dependências (contratos) antes de deletar
        with db.obter_conexao() as conn_check_deps:
            cursor_deps = conn_check_deps.cursor()
            cursor_deps.execute("SELECT COUNT(*) FROM contratos WHERE cod_empresa = ?", (cod_empresa,))
            if cursor_deps.fetchone()[0] > 0:
                logger.warning(f"Tentativa de deletar empresa {cod_empresa} que possui contratos associados.")
                st.error("Não é possível excluir esta empresa pois ela possui contratos vinculados.")
                return False

        with db.obter_conexao() as conn_delete:
            cursor_delete = conn_delete.cursor()
            cursor_delete.execute("DELETE FROM empresas WHERE cod_empresa = ?", (cod_empresa,))
            if cursor_delete.rowcount > 0:
                db.marca_sujo()
                logger.info(f"Empresa {cod_empresa} deletada do banco.")
            else:
                logger.info(f"Empresa {cod_empresa} não encontrada no banco para deleção.")
                return True # Sucesso se não havia o que deletar

        if getattr(db._thread_local, "dirty", False):
            caminho_banco_local = Path(gettempdir()) / db.DB_NAME
            try:
                db.salvar_banco_no_drive(caminho_banco_local)
                logger.info(f"Banco de dados salvo no Drive após deleção da empresa {cod_empresa}.")
            except Exception as e_save:
                logger.error(f"Erro ao salvar banco no Drive após deletar empresa {cod_empresa}: {e_save}")
                return True # Operação local bem-sucedida
        return True

    except Exception as e_main:
        logger.error(f"Erro ao deletar empresa {cod_empresa}: {e_main}")
        st.error(f"Ocorreu um erro inesperado ao deletar a empresa: {e_main}")
        return False
