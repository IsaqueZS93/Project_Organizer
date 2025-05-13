# backend/Models/model_contrato.py

import sqlite3
from typing import List, Optional, Tuple
from pathlib import Path
import sys
import os
import logging
from tempfile import gettempdir
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
from Database.db_gestaodecontratos import obter_conexao, salvar_banco_no_drive, DB_NAME
from Services import Service_googledrive as gdrive
from dotenv import load_dotenv

load_dotenv()
EMPRESAS_DRIVE_FOLDER_ID = os.getenv("GDRIVE_EMPRESAS_FOLDER_ID")  # Pasta raiz das empresas

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────── CRUD de Contratos com integração ao Drive ────────────────

def obter_nome_empresa_por_codigo(cod_empresa: str) -> Optional[str]:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM empresas WHERE cod_empresa = ?", (cod_empresa,))
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Erro ao buscar nome da empresa: {e}")
        return None


def criar_contrato(cod_empresa: str, empresa_contratada: str, numero_contrato: str, titulo: str, especificacoes: str) -> bool:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            
            # Verifica se o número do contrato já existe
            cursor.execute("SELECT numero_contrato FROM contratos WHERE numero_contrato = ?", (numero_contrato,))
            if cursor.fetchone():
                logger.warning(f"Tentativa de criar contrato com número duplicado: {numero_contrato}")
                return False
            
            # Busca o nome da empresa
            cursor.execute("SELECT nome FROM empresas WHERE cod_empresa = ?", (cod_empresa,))
            row = cursor.fetchone()
            if not row:
                logger.error("Empresa não encontrada para o código informado")
                return False
            nome_empresa = row[0]

            # Busca o ID da pasta da empresa
            cursor.execute("SELECT pasta_empresa FROM empresas WHERE cod_empresa = ?", (cod_empresa,))
            row = cursor.fetchone()
            if not row or not row[0]:
                logger.error("Pasta da empresa não encontrada no banco")
                return False
            empresa_folder_id = row[0]

            logger.info(f"Usando pasta da empresa: {nome_empresa}")
            
            nome_pasta_contrato = f"{numero_contrato}_{empresa_contratada}"
            logger.info(f"Criando pasta do contrato: {nome_pasta_contrato}")
            logger.info(f"Dentro da pasta da empresa: {nome_empresa}")
            
            contrato_folder_id = gdrive.ensure_folder(nome_pasta_contrato, empresa_folder_id)
            if not contrato_folder_id:
                logger.error("Erro ao criar pasta do contrato")
                return False
                
            logger.info(f"Pasta do contrato criada com sucesso: {nome_pasta_contrato}")

            # Insere no banco
            cursor.execute("""
                INSERT INTO contratos (numero_contrato, cod_empresa, empresa_contratada, titulo, especificacoes, pasta_contrato)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (numero_contrato, cod_empresa, empresa_contratada, titulo, especificacoes, contrato_folder_id))
            
            # Força o commit
            conn.commit()
            
            # Verifica se o contrato foi realmente inserido
            cursor.execute("SELECT numero_contrato FROM contratos WHERE numero_contrato = ?", (numero_contrato,))
            if not cursor.fetchone():
                logger.error("Erro: Contrato não foi inserido no banco")
                return False

            # Salva no Drive
            caminho_banco = Path(gettempdir()) / DB_NAME
            try:
                salvar_banco_no_drive(caminho_banco)
                logger.info(f"Contrato {numero_contrato} criado com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao salvar banco no Drive: {e}")
                # Mesmo com erro no Drive, o contrato foi criado localmente
                return True

    except Exception as e:
        logger.error(f"Erro ao criar contrato: {e}")
        return False


def listar_contratos() -> List[Tuple]:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT numero_contrato, cod_empresa, empresa_contratada, titulo, especificacoes FROM contratos
            """)
            return cursor.fetchall()
    except Exception as e:
        print(f"❌ Erro ao listar contratos: {e}")
        return []


def buscar_contrato_por_numero(numero_contrato: str) -> Optional[Tuple]:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contratos WHERE numero_contrato = ?", (numero_contrato,))
            return cursor.fetchone()
    except Exception as e:
        print(f"❌ Erro ao buscar contrato: {e}")
        return None


def atualizar_contrato(numero_contrato: str, cod_empresa: str, empresa_contratada: str, titulo: str, especificacoes: str) -> bool:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE contratos
                SET cod_empresa = ?, empresa_contratada = ?, titulo = ?, especificacoes = ?
                WHERE numero_contrato = ?
            """, (cod_empresa, empresa_contratada, titulo, especificacoes, numero_contrato))
            
            caminho_banco = Path(gettempdir()) / DB_NAME
            salvar_banco_no_drive(caminho_banco)
            return True

    except Exception as e:
        print(f"❌ Erro ao atualizar contrato: {e}")
        return False


def deletar_contrato(numero_contrato: str) -> bool:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM contratos WHERE numero_contrato = ?", (numero_contrato,))
            
            caminho_banco = Path(gettempdir()) / DB_NAME
            salvar_banco_no_drive(caminho_banco)
            return True
    except Exception as e:
        print(f"❌ Erro ao deletar contrato: {e}")
        return False
