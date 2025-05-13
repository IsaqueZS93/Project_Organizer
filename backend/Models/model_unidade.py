# backend/Models/model_unidade.py

import sqlite3
from typing import List, Optional, Tuple
from pathlib import Path
import sys
import os
import logging
from datetime import datetime
from tempfile import gettempdir
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
from Database.db_gestaodecontratos import obter_conexao, salvar_banco_no_drive, DB_NAME
from Services import Service_googledrive as gdrive
from dotenv import load_dotenv

load_dotenv()
EMPRESAS_DRIVE_FOLDER_ID = os.getenv("GDRIVE_EMPRESAS_FOLDER_ID")

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────── CRUD de Unidades com pastas ────────────────

def obter_pasta_contrato(numero_contrato: str, nome_empresa: str) -> Optional[str]:
    try:
        # Busca o nome exato da empresa contratada no banco
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT empresa_contratada FROM contratos WHERE numero_contrato = ?", (numero_contrato,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"Contrato {numero_contrato} não encontrado no banco de dados")
                return None
                
            empresa_contratada = row[0]
            logger.info(f"Informações do contrato:")
            logger.info(f"   - Número: {numero_contrato}")
            logger.info(f"   - Empresa contratada: {empresa_contratada}")
            logger.info(f"   - Nome da empresa: {nome_empresa}")
            
            # Tenta diferentes formatos de nome de pasta
            formatos_pasta = [
                f"{numero_contrato}_{empresa_contratada}",  # Formato original
                f"{numero_contrato}_{nome_empresa}",        # Formato alternativo
                f"{numero_contrato}_{empresa_contratada.replace(' ', '_')}",  # Sem espaços
                f"{numero_contrato}_{nome_empresa.replace(' ', '_')}"         # Sem espaços
            ]
            
            logger.info("Tentando encontrar a pasta do contrato...")
            
            # Primeiro tenta encontrar na pasta raiz
            for formato in formatos_pasta:
                logger.info(f"Tentando formato: {formato}")
                pasta_id = gdrive.get_file_id_by_name(formato, st.session_state.get("GDRIVE_EMPRESAS_FOLDER_ID"))
                if pasta_id:
                    logger.info(f"Pasta encontrada na raiz: {formato}")
                    return pasta_id
            
            # Se não encontrar na raiz, tenta dentro da pasta da empresa
            logger.info("Buscando dentro da pasta da empresa...")
            empresa_folder_id = gdrive.get_file_id_by_name(nome_empresa, st.session_state.get("GDRIVE_EMPRESAS_FOLDER_ID"))
            if empresa_folder_id:
                logger.info(f"Pasta da empresa encontrada: {nome_empresa}")
                for formato in formatos_pasta:
                    logger.info(f"Tentando formato: {formato}")
                    pasta_id = gdrive.get_file_id_by_name(formato, empresa_folder_id)
                    if pasta_id:
                        logger.info(f"Pasta encontrada dentro da empresa: {formato}")
                        return pasta_id
            else:
                logger.error(f"Pasta da empresa não encontrada: {nome_empresa}")
            
            logger.error("Nenhum formato de pasta do contrato foi encontrado")
            return None
            
    except Exception as e:
        logger.error(f"Erro ao obter pasta do contrato: {e}")
        return None


def obter_nome_empresa_por_contrato(numero_contrato: str) -> Optional[str]:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.nome FROM contratos c
                JOIN empresas e ON c.cod_empresa = e.cod_empresa
                WHERE c.numero_contrato = ?
            """, (numero_contrato,))
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Erro ao buscar nome da empresa: {e}")
        return None


def criar_unidade(numero_contrato: str, nome_unidade: str, estado: str, cidade: str, localizacao: str, cod_unidade: str) -> bool:
    try:
        logger.info(f"Iniciando criação da unidade {cod_unidade}")
        
        nome_empresa = obter_nome_empresa_por_contrato(numero_contrato)
        if not nome_empresa:
            logger.error("Empresa relacionada ao contrato não encontrada")
            return False

        logger.info(f"Empresa encontrada: {nome_empresa}")

        # Busca o ID da pasta do contrato
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pasta_contrato FROM contratos WHERE numero_contrato = ?", (numero_contrato,))
            row = cursor.fetchone()
            if not row or not row[0]:
                logger.error("Pasta do contrato não encontrada no banco")
                return False
            pasta_contrato_id = row[0]

        logger.info("Pasta do contrato encontrada")

        nome_pasta_unidade = f"{nome_unidade}_{cod_unidade}"
        logger.info(f"Criando pasta da unidade: {nome_pasta_unidade}")
        
        pasta_unidade_id = gdrive.ensure_folder(nome_pasta_unidade, pasta_contrato_id)
        if not pasta_unidade_id:
            logger.error("Erro ao criar pasta da unidade")
            return False
            
        logger.info(f"Pasta da unidade criada com sucesso: {nome_pasta_unidade}")

        try:
            # Inicia uma transação
            with obter_conexao() as conn:
                cursor = conn.cursor()
                conn.execute("BEGIN TRANSACTION")
                
                # Verifica se o código da unidade já existe
                cursor.execute("SELECT cod_unidade FROM unidades WHERE cod_unidade = ?", (cod_unidade,))
                if cursor.fetchone():
                    logger.warning(f"Tentativa de criar unidade com código duplicado: {cod_unidade}")
                    conn.rollback()
                    return False
                
                # Insere no banco
                cursor.execute("""
                    INSERT INTO unidades (cod_unidade, numero_contrato, nome_unidade, estado, cidade, localizacao, pasta_unidade)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (cod_unidade, numero_contrato, nome_unidade, estado, cidade, localizacao, pasta_unidade_id))
                
                # Força o commit
                conn.commit()
                logger.info("Dados inseridos no banco com sucesso")
                
                # Verifica se a unidade foi realmente inserida
                cursor.execute("SELECT cod_unidade FROM unidades WHERE cod_unidade = ?", (cod_unidade,))
                if not cursor.fetchone():
                    logger.error("Erro: Unidade não foi inserida no banco")
                    conn.rollback()
                    return False
                
                # Salva no Drive
                caminho_banco = Path(gettempdir()) / DB_NAME
                try:
                    salvar_banco_no_drive(caminho_banco)
                    logger.info(f"Unidade {cod_unidade} criada com sucesso")
                    return True
                except Exception as e:
                    logger.error(f"Erro ao salvar banco no Drive: {e}")
                    # Mesmo com erro no Drive, a unidade foi criada localmente
                    return True
                    
        except Exception as e:
            logger.error(f"Erro durante a transação: {e}")
            conn.rollback()
            return False

    except Exception as e:
        logger.error(f"Erro ao criar unidade: {e}")
        return False


def listar_unidades() -> List[Tuple]:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cod_unidade, numero_contrato, nome_unidade, estado, cidade, localizacao FROM unidades")
            return cursor.fetchall()
    except Exception as e:
        print(f"❌ Erro ao listar unidades: {e}")
        return []


def buscar_unidade_por_codigo(cod_unidade: str) -> Optional[Tuple]:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM unidades WHERE cod_unidade = ?", (cod_unidade,))
            return cursor.fetchone()
    except Exception as e:
        print(f"❌ Erro ao buscar unidade: {e}")
        return None


def atualizar_unidade(cod_unidade: str, numero_contrato: str, nome_unidade: str, estado: str, cidade: str, localizacao: str) -> bool:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE unidades
                SET numero_contrato = ?, nome_unidade = ?, estado = ?, cidade = ?, localizacao = ?
                WHERE cod_unidade = ?
            """, (numero_contrato, nome_unidade, estado, cidade, localizacao, cod_unidade))
            
            caminho_banco = Path(gettempdir()) / DB_NAME
            salvar_banco_no_drive(caminho_banco)
            return True

    except Exception as e:
        print(f"❌ Erro ao atualizar unidade: {e}")
        return False


def deletar_unidade(cod_unidade: str) -> bool:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM unidades WHERE cod_unidade = ?", (cod_unidade,))
            
            caminho_banco = Path(gettempdir()) / DB_NAME
            salvar_banco_no_drive(caminho_banco)
            return True
    except Exception as e:
        print(f"❌ Erro ao deletar unidade: {e}")
        return False
