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
from Database import db_gestaodecontratos as db
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
        with db.obter_conexao() as conn:
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
        with db.obter_conexao() as conn:
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
        with db.obter_conexao() as conn:
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
            with db.obter_conexao() as conn:
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
                caminho_banco = Path(gettempdir()) / db.DB_NAME
                try:
                    db.salvar_banco_no_drive(caminho_banco)
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
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cod_unidade, numero_contrato, nome_unidade, estado, cidade, localizacao FROM unidades")
            return cursor.fetchall()
    except Exception as e:
        print(f"❌ Erro ao listar unidades: {e}")
        return []


def buscar_unidade_por_codigo(cod_unidade: str) -> Optional[Tuple]:
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM unidades WHERE cod_unidade = ?", (cod_unidade,))
            return cursor.fetchone()
    except Exception as e:
        print(f"❌ Erro ao buscar unidade: {e}")
        return None


def atualizar_unidade(cod_unidade: str, numero_contrato: str, nome_unidade: str, estado: str, cidade: str, localizacao: str) -> bool:
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE unidades
                SET numero_contrato = ?, nome_unidade = ?, estado = ?, cidade = ?, localizacao = ?
                WHERE cod_unidade = ?
            """, (numero_contrato, nome_unidade, estado, cidade, localizacao, cod_unidade))
            
            if cursor.rowcount > 0:
                db.marca_sujo()
            else:
                logger.info(f"Nenhuma unidade encontrada com o código {cod_unidade} para atualizar, ou os dados são os mesmos.")
                return True # Considera sucesso se não havia o que atualizar ou dados eram iguais

        if getattr(db._thread_local, "dirty", False):
            caminho_banco = Path(gettempdir()) / db.DB_NAME
            try:
                db.salvar_banco_no_drive(caminho_banco)
                logger.info(f"Unidade {cod_unidade} atualizada e banco salvo.")
                return True
            except Exception as e_save:
                logger.error(f"Erro ao salvar banco no Drive após atualizar unidade {cod_unidade}: {e_save}")
                return True # Operação local bem-sucedida
        return True # Retorna True se não estava sujo (nenhuma alteração efetiva)

    except Exception as e:
        print(f"❌ Erro ao atualizar unidade: {e}")
        return False


def deletar_unidade(cod_unidade: str) -> bool:
    try:
        # Verificar se há serviços associados antes de deletar?
        # Por simplicidade, esta função deleta diretamente.
        with db.obter_conexao() as conn_delete:
            cursor_delete = conn_delete.cursor()
            # Adicionar deleção em cascata ou tratamento para tabelas dependentes (ex: servicos)
            # Por enquanto, deleta apenas da tabela unidades.
            cursor_delete.execute("DELETE FROM unidades WHERE cod_unidade = ?", (cod_unidade,))
            if cursor_delete.rowcount > 0:
                db.marca_sujo()
                logger.info(f"Unidade {cod_unidade} deletada do banco.")
            else:
                logger.info(f"Unidade {cod_unidade} não encontrada no banco para deleção.")
                # Se não encontrou no banco, não há o que marcar como sujo nem salvar.
                return True # Considera sucesso se não havia o que deletar.

        if getattr(db._thread_local, "dirty", False):
            caminho_banco = Path(gettempdir()) / db.DB_NAME
            try:
                db.salvar_banco_no_drive(caminho_banco)
                logger.info(f"Banco de dados salvo no Drive após deleção da unidade {cod_unidade}.")
            except Exception as e_save:
                logger.error(f"Erro ao salvar banco no Drive após deletar unidade {cod_unidade}: {e_save}")
                # Mesmo se salvar no Drive falhar, a deleção local e no Drive (pasta) podem ter ocorrido.
                # Retornar True, pois a principal operação no banco foi tentada.
                return True 
        return True # Retorna True se a operação foi bem-sucedida (ou nada a fazer)

    except Exception as e_main:
        logger.error(f"Erro ao deletar unidade {cod_unidade}: {e_main}")
        return False
