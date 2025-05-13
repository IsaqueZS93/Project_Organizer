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
from Database.db_gestaodecontratos import obter_conexao, salvar_banco_no_drive, DB_NAME
from Services import Service_googledrive as gdrive

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ───────────────── CRUD de Empresas com Drive ─────────────────

def criar_empresa(nome: str, cnpj: str, cod_empresa: str) -> bool:
    """Cria uma nova empresa no banco de dados e no Google Drive"""
    try:
        # Obtém o ID da pasta de empresas do session_state
        empresas_folder_id = st.session_state.get("GDRIVE_EMPRESAS_FOLDER_ID")
        if not empresas_folder_id:
            logger.error("GDRIVE_EMPRESAS_FOLDER_ID não definida no session_state")
            return False

        with obter_conexao() as conn:
            cursor = conn.cursor()
            
            # Verifica se CNPJ já existe
            cursor.execute("SELECT id FROM empresas WHERE cnpj = ?", (cnpj,))
            if cursor.fetchone():
                logger.warning(f"Tentativa de criar empresa com CNPJ duplicado: {cnpj}")
                return False
                
            # Verifica se código já existe
            cursor.execute("SELECT id FROM empresas WHERE cod_empresa = ?", (cod_empresa,))
            if cursor.fetchone():
                logger.warning(f"Tentativa de criar empresa com código duplicado: {cod_empresa}")
                return False

            # Cria a pasta no Drive
            pasta_empresa_id = gdrive.ensure_folder(nome, empresas_folder_id)
            if not pasta_empresa_id:
                logger.error("Erro ao criar pasta da empresa no Drive")
                return False

            # Salva no banco de dados
            cursor.execute("""
                INSERT INTO empresas (nome, cnpj, cod_empresa, pasta_empresa)
                VALUES (?, ?, ?, ?)
            """, (nome, cnpj, cod_empresa, pasta_empresa_id))
            
            # Força o commit
            conn.commit()
            
            # Verifica se a empresa foi realmente inserida
            cursor.execute("SELECT id FROM empresas WHERE cnpj = ?", (cnpj,))
            if not cursor.fetchone():
                logger.error("Erro: Empresa não foi inserida no banco")
                return False

            # Salva no Drive
            caminho_banco = Path(gettempdir()) / DB_NAME
            try:
                salvar_banco_no_drive(caminho_banco)
                logger.info(f"Empresa {nome} criada com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao salvar banco no Drive: {e}")
                # Mesmo com erro no Drive, a empresa foi criada localmente
                return True

    except Exception as e:
        logger.error(f"Erro ao criar empresa: {e}")
        return False


def listar_empresas() -> List[Tuple]:
    """Lista todas as empresas cadastradas"""
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome, cnpj, cod_empresa FROM empresas")
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Erro ao listar empresas: {e}")
        return []


def buscar_empresa_por_id(emp_id: int) -> Optional[Tuple]:
    """Busca uma empresa pelo ID"""
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM empresas WHERE id = ?", (emp_id,))
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Erro ao buscar empresa: {e}")
        return None


def atualizar_empresa(emp_id: int, nome: str, cnpj: str, cod_empresa: str) -> bool:
    """Atualiza os dados de uma empresa"""
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            
            # Verifica se o CNPJ ou código já existe (exceto para a própria empresa)
            cursor.execute("""
                SELECT id FROM empresas 
                WHERE (cnpj = ? OR cod_empresa = ?) AND id != ?
            """, (cnpj, cod_empresa, emp_id))
            
            if cursor.fetchone():
                logger.warning(f"Tentativa de atualizar para CNPJ ou código já existente")
                return False

            # Atualiza a empresa
            cursor.execute("""
                UPDATE empresas
                SET nome = ?, cnpj = ?, cod_empresa = ?
                WHERE id = ?
            """, (nome, cnpj, cod_empresa, emp_id))
            
            # Força o commit
            conn.commit()
            
            # Verifica se a atualização foi bem sucedida
            cursor.execute("SELECT id FROM empresas WHERE id = ? AND nome = ?", (emp_id, nome))
            if not cursor.fetchone():
                logger.error("Erro: Atualização da empresa não foi confirmada")
                return False
            
            # Salva no Drive
            caminho_banco = Path(gettempdir()) / DB_NAME
            try:
                salvar_banco_no_drive(caminho_banco)
                logger.info(f"Empresa {nome} atualizada com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao salvar banco no Drive: {e}")
                # Mesmo com erro no Drive, a empresa foi atualizada localmente
                return True

    except Exception as e:
        logger.error(f"Erro ao atualizar empresa: {e}")
        return False


def deletar_empresa(emp_id: int) -> bool:
    """Deleta uma empresa"""
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            
            # Verifica se a empresa existe
            cursor.execute("SELECT id FROM empresas WHERE id = ?", (emp_id,))
            if not cursor.fetchone():
                logger.warning(f"Tentativa de deletar empresa inexistente: {emp_id}")
                return False
                
            cursor.execute("DELETE FROM empresas WHERE id = ?", (emp_id,))
            
            # Força o commit
            conn.commit()
            
            # Verifica se a empresa foi realmente deletada
            cursor.execute("SELECT id FROM empresas WHERE id = ?", (emp_id,))
            if cursor.fetchone():
                logger.error("Erro: Empresa não foi deletada do banco")
                return False

            # Salva no Drive
            caminho_banco = Path(gettempdir()) / DB_NAME
            try:
                salvar_banco_no_drive(caminho_banco)
                logger.info(f"Empresa {emp_id} deletada com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao salvar banco no Drive: {e}")
                # Mesmo com erro no Drive, a empresa foi deletada localmente
                return True
                
    except Exception as e:
        logger.error(f"Erro ao deletar empresa: {e}")
        return False
