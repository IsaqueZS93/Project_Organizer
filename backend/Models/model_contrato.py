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
from Database import db_gestaodecontratos as db
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
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM empresas WHERE cod_empresa = ?", (cod_empresa,))
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Erro ao buscar nome da empresa: {e}")
        return None


def criar_contrato(cod_empresa: str, empresa_contratada: str, numero_contrato: str, titulo: str, especificacoes: str) -> bool:
    try:
        logger.info(f"Iniciando criação do contrato {numero_contrato}")
        
        with db.obter_conexao() as conn:
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

            try:
                # Inicia uma transação
                conn.execute("BEGIN TRANSACTION")
                
                # Insere no banco
                cursor.execute("""
                    INSERT INTO contratos (numero_contrato, cod_empresa, empresa_contratada, titulo, especificacoes, pasta_contrato)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (numero_contrato, cod_empresa, empresa_contratada, titulo, especificacoes, contrato_folder_id))
                
                # Força o commit
                conn.commit()
                logger.info("Dados inseridos no banco com sucesso")
                
                # Verifica se o contrato foi realmente inserido
                cursor.execute("SELECT numero_contrato FROM contratos WHERE numero_contrato = ?", (numero_contrato,))
                if not cursor.fetchone():
                    logger.error("Erro: Contrato não foi inserido no banco")
                    conn.rollback()
                    return False
                
                # Salva no Drive
                caminho_banco = Path(gettempdir()) / db.DB_NAME
                try:
                    db.salvar_banco_no_drive(caminho_banco)
                    logger.info(f"Contrato {numero_contrato} criado com sucesso")
                    return True
                except Exception as e:
                    logger.error(f"Erro ao salvar banco no Drive: {e}")
                    # Mesmo com erro no Drive, o contrato foi criado localmente
                    return True
                    
            except Exception as e:
                logger.error(f"Erro durante a transação: {e}")
                conn.rollback()
                return False

    except Exception as e:
        logger.error(f"Erro ao criar contrato: {e}")
        return False


def listar_contratos() -> List[Tuple]:
    try:
        with db.obter_conexao() as conn:
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
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contratos WHERE numero_contrato = ?", (numero_contrato,))
            return cursor.fetchone()
    except Exception as e:
        print(f"❌ Erro ao buscar contrato: {e}")
        return None


def atualizar_contrato(numero_contrato: str, cod_empresa: str, empresa_contratada: str, titulo: str, especificacoes: str) -> bool:
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE contratos
                SET cod_empresa = ?, empresa_contratada = ?, titulo = ?, especificacoes = ?
                WHERE numero_contrato = ?
            """, (cod_empresa, empresa_contratada, titulo, especificacoes, numero_contrato))
            
            if cursor.rowcount > 0:
                db.marca_sujo()
            else:
                logger.info(f"Nenhum contrato encontrado com o número {numero_contrato} para atualizar, ou os dados são os mesmos.")
                return True # Sucesso se nada precisava ser atualizado

        if getattr(db._thread_local, "dirty", False):
            caminho_banco = Path(gettempdir()) / db.DB_NAME
            try:
                db.salvar_banco_no_drive(caminho_banco)
                logger.info(f"Contrato {numero_contrato} atualizado e banco salvo.")
            except Exception as e_save:
                logger.error(f"Erro ao salvar banco no Drive após atualizar contrato {numero_contrato}: {e_save}")
                return True # Operação local bem-sucedida
        return True # Sucesso se não estava sujo

    except Exception as e:
        print(f"❌ Erro ao atualizar contrato: {e}")
        return False


def deletar_contrato(numero_contrato: str) -> bool:
    try:
        # Adicionar lógica para verificar/deletar unidades e serviços dependentes antes
        # ou configurar ON DELETE CASCADE no banco (se SQLite suportar para as suas FKs).
        # Por enquanto, deleta apenas da tabela contratos.
        with db.obter_conexao() as conn_delete:
            cursor_delete = conn_delete.cursor()
            cursor_delete.execute("DELETE FROM contratos WHERE numero_contrato = ?", (numero_contrato,))
            if cursor_delete.rowcount > 0:
                db.marca_sujo()
                logger.info(f"Contrato {numero_contrato} deletado do banco.")
            else:
                logger.info(f"Contrato {numero_contrato} não encontrado no banco para deleção.")
                return True # Sucesso se não havia o que deletar

        if getattr(db._thread_local, "dirty", False):
            caminho_banco = Path(gettempdir()) / db.DB_NAME
            try:
                db.salvar_banco_no_drive(caminho_banco)
                logger.info(f"Banco de dados salvo no Drive após deleção do contrato {numero_contrato}.")
            except Exception as e_save:
                logger.error(f"Erro ao salvar banco no Drive após deletar contrato {numero_contrato}: {e_save}")
                return True # Operação local bem-sucedida
        return True # Sucesso se não estava sujo ou operação bem-sucedida

    except Exception as e:
        print(f"❌ Erro ao deletar contrato: {e}")
        return False
