# backend/Models/model_servico.py

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
from Models.model_unidade import obter_pasta_contrato

load_dotenv()
EMPRESAS_DRIVE_FOLDER_ID = os.getenv("GDRIVE_EMPRESAS_FOLDER_ID")

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────── Funções Auxiliares ────────────────

def gerar_codigo_servico() -> str:
    """Gera um código único para o serviço no formato: OS_AAAAMMDD_XXX"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            
            # Obtém a data atual
            data_atual = datetime.now().strftime("%Y%m%d")
            
            # Busca o último código do dia
            cursor.execute("""
                SELECT cod_servico FROM servicos 
                WHERE cod_servico LIKE ? 
                ORDER BY cod_servico DESC LIMIT 1
            """, (f"OS_{data_atual}_%",))
            
            ultimo_codigo = cursor.fetchone()
            
            if ultimo_codigo:
                # Extrai o número sequencial e incrementa
                ultimo_numero = int(ultimo_codigo[0].split('_')[-1])
                novo_numero = ultimo_numero + 1
            else:
                # Se não houver código hoje, começa do 1
                novo_numero = 1
            
            # Formata o novo código com 3 dígitos
            return f"OS_{data_atual}_{novo_numero:03d}"
    except Exception as e:
        logger.error(f"Erro ao gerar código do serviço: {e}")
        return None

# ──────────────── CRUD de Serviços com Drive ────────────────

def obter_pasta_unidade(cod_unidade: str, nome_unidade: str, numero_contrato: str, nome_empresa: str) -> Optional[str]:
    try:
        pasta_contrato = f"{numero_contrato}_{nome_empresa}"
        pasta_unidade = f"{nome_unidade}_{cod_unidade}"
        
        logger.info(f"Buscando pasta do contrato: {pasta_contrato}")
        pasta_contrato_id = gdrive.get_file_id_by_name(pasta_contrato, st.session_state.get("GDRIVE_EMPRESAS_FOLDER_ID"))
        
        if not pasta_contrato_id:
            logger.error(f"Pasta do contrato não encontrada: {pasta_contrato}")
            return None
            
        logger.info(f"Pasta do contrato encontrada: {pasta_contrato}")
        logger.info(f"Buscando pasta da unidade: {pasta_unidade}")
        
        pasta_unidade_id = gdrive.get_file_id_by_name(pasta_unidade, pasta_contrato_id)
        if not pasta_unidade_id:
            logger.error(f"Pasta da unidade não encontrada: {pasta_unidade}")
            return None
            
        logger.info(f"Pasta da unidade encontrada: {pasta_unidade}")
        return pasta_unidade_id
    except Exception as e:
        logger.error(f"Erro ao obter pasta da unidade: {e}")
        return None


def obter_info_unidade(cod_servico: str) -> Optional[Tuple[str, str, str]]:
    """Obtém informações da unidade (nome, contrato e empresa) a partir do código do serviço"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            
            # Primeiro busca o código da unidade associada ao serviço
            cursor.execute("SELECT cod_unidade FROM servicos WHERE cod_servico = ?", (cod_servico,))
            unidade_row = cursor.fetchone()
            if not unidade_row:
                logger.error(f"Serviço não encontrado: {cod_servico}")
                return None
                
            cod_unidade = unidade_row[0]
            logger.info(f"Código da unidade encontrado: {cod_unidade}")
            
            # Agora busca as informações completas da unidade
            cursor.execute("""
                SELECT u.nome_unidade, c.numero_contrato, e.nome
                FROM unidades u
                JOIN contratos c ON u.numero_contrato = c.numero_contrato
                JOIN empresas e ON c.cod_empresa = e.cod_empresa
                WHERE u.cod_unidade = ?
            """, (cod_unidade,))
            
            row = cursor.fetchone()
            if not row:
                logger.error(f"Informações incompletas para a unidade: {cod_unidade}")
                return None
                
            logger.info(f"Informações da unidade encontradas:")
            logger.info(f"   - Nome: {row[0]}")
            logger.info(f"   - Contrato: {row[1]}")
            logger.info(f"   - Empresa: {row[2]}")
            return row
            
    except Exception as e:
        logger.error(f"Erro ao buscar informações da unidade: {e}")
        return None


def criar_servico(cod_servico: str, cod_unidade: str, tipo_servico: str, data_criacao: str, data_execucao: str, status: str, observacoes: str) -> bool:
    try:
        logger.info(f"Iniciando criação do serviço {cod_servico}")
        
        # Primeiro verifica se a unidade existe e obtém suas informações
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.nome_unidade, c.numero_contrato, e.nome, u.pasta_unidade, c.pasta_contrato, e.pasta_empresa
                FROM unidades u
                JOIN contratos c ON u.numero_contrato = c.numero_contrato
                JOIN empresas e ON c.cod_empresa = e.cod_empresa
                WHERE u.cod_unidade = ?
            """, (cod_unidade,))
            row = cursor.fetchone()
            
            if not row:
                logger.error(f"Unidade não encontrada: {cod_unidade}")
                return False
                
            nome_unidade, numero_contrato, nome_empresa, pasta_unidade_id, pasta_contrato_id, pasta_empresa_id = row
            
            if not pasta_unidade_id:
                logger.error(f"Pasta da unidade não encontrada no banco para: {cod_unidade}")
                return False

        logger.info(f"Informações encontradas:")
        logger.info(f"   - Unidade: {nome_unidade}")
        logger.info(f"   - Contrato: {numero_contrato}")
        logger.info(f"   - Empresa: {nome_empresa}")
        logger.info(f"   - ID Pasta Unidade: {pasta_unidade_id}")
        logger.info(f"   - ID Pasta Contrato: {pasta_contrato_id}")
        logger.info(f"   - ID Pasta Empresa: {pasta_empresa_id}")

        # Cria a pasta do serviço
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        nome_pasta_servico = f"{cod_servico}_{nome_unidade}_{timestamp}"
        logger.info(f"Criando pasta do serviço: {nome_pasta_servico}")
        
        # Usa o ID da pasta da unidade para criar a pasta do serviço
        pasta_servico_id = gdrive.ensure_folder(nome_pasta_servico, pasta_unidade_id)
        if not pasta_servico_id:
            logger.error("Erro ao criar pasta do serviço")
            return False
        logger.info(f"Pasta do serviço criada com sucesso: {pasta_servico_id}")

        try:
            # Inicia uma transação
            with db.obter_conexao() as conn:
                cursor = conn.cursor()
                conn.execute("BEGIN TRANSACTION")
                
                # Verifica se o código do serviço já existe
                cursor.execute("SELECT cod_servico FROM servicos WHERE cod_servico = ?", (cod_servico,))
                if cursor.fetchone():
                    logger.warning(f"Tentativa de criar serviço com código duplicado: {cod_servico}")
                    conn.rollback()
                    return False
                
                # Insere no banco
                cursor.execute("""
                    INSERT INTO servicos (
                        cod_servico, cod_unidade, tipo_servico, data_criacao, 
                        data_execucao, status, observacoes, pasta_servico
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cod_servico, cod_unidade, tipo_servico, data_criacao,
                    data_execucao, status, observacoes, pasta_servico_id
                ))
                
                # Força o commit
                conn.commit()
                logger.info("Dados inseridos no banco com sucesso")
                
                # Verifica se o serviço foi realmente inserido
                cursor.execute("SELECT cod_servico FROM servicos WHERE cod_servico = ?", (cod_servico,))
                if not cursor.fetchone():
                    logger.error("Erro: Serviço não foi inserido no banco")
                    conn.rollback()
                    return False
                
                # Salva no Drive
                caminho_banco = Path(gettempdir()) / db.DB_NAME
                try:
                    db.salvar_banco_no_drive(caminho_banco)
                    logger.info(f"Serviço {cod_servico} criado com sucesso")
                    return True
                except Exception as e:
                    logger.error(f"Erro ao salvar banco no Drive: {e}")
                    # Mesmo com erro no Drive, o serviço foi criado localmente
                    return True
                    
        except Exception as e:
            logger.error(f"Erro durante a transação: {e}")
            conn.rollback()
            return False

    except Exception as e:
        logger.error(f"Erro ao criar serviço: {e}")
        return False


def listar_servicos() -> List[Tuple]:
    """Lista todos os serviços cadastrados"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cod_servico, cod_unidade, tipo_servico, data_criacao, data_execucao, status, observacoes FROM servicos")
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"❌ Erro ao listar serviços: {e}")
        return []


def buscar_servico_por_codigo(cod_servico: str) -> Optional[Tuple]:
    """Busca um serviço pelo código"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, u.nome_unidade, c.numero_contrato, e.nome as nome_empresa
                FROM servicos s
                INNER JOIN unidades u ON s.cod_unidade = u.cod_unidade
                INNER JOIN contratos c ON u.numero_contrato = c.numero_contrato
                INNER JOIN empresas e ON c.cod_empresa = e.cod_empresa
                WHERE s.cod_servico = ?
            """, (cod_servico,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"❌ Erro ao buscar serviço: {e}")
        return None


def atualizar_servico(cod_servico: str, tipo_servico: str, data_execucao: str, status: str, observacoes: str) -> bool:
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE servicos
                SET tipo_servico = ?, data_execucao = ?, status = ?, observacoes = ?
                WHERE cod_servico = ?
            """, (tipo_servico, data_execucao, status, observacoes, cod_servico))
            return True
    except Exception as e:
        print(f"❌ Erro ao atualizar serviço: {e}")
        return False


def deletar_servico(cod_servico: str) -> bool:
    """Exclui um serviço do banco de dados"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM servicos WHERE cod_servico = ?", (cod_servico,))
            return True
    except Exception as e:
        print(f"❌ Erro ao deletar serviço: {e}")
        return False

# ──────────────── Funções de Arquivos ────────────────

def upload_arquivo_servico(cod_servico: str, arquivo: bytes, nome_arquivo: str, tipo_arquivo: str, descricao: str = None) -> bool:
    try:
        print(f"📤 Iniciando upload do arquivo: {nome_arquivo}")
        print(f"   - Serviço: {cod_servico}")
        print(f"   - Tipo: {tipo_arquivo}")

        # Busca o ID da pasta do serviço
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pasta_servico FROM servicos WHERE cod_servico = ?", (cod_servico,))
            row = cursor.fetchone()
            if not row or not row[0]:
                print("❌ Pasta do serviço não encontrada no banco")
                return False
            pasta_servico_id = row[0]

        print(f"✅ Pasta do serviço encontrada")

        # 📁 Verificar ou criar pasta "Arquivos"
        pasta_arquivos = "Arquivos"
        pasta_arquivos_id = gdrive.get_file_id_by_name(pasta_arquivos, pasta_servico_id)
        if not pasta_arquivos_id:
            print(f"📁 Criando pasta de arquivos: {pasta_arquivos}")
            pasta_arquivos_id = gdrive.ensure_folder(pasta_arquivos, pasta_servico_id)
            if not pasta_arquivos_id:
                print("❌ Erro ao criar pasta de arquivos")
                return False
            print(f"✅ Pasta de arquivos criada: {pasta_arquivos_id}")
        else:
            print(f"✅ Pasta de arquivos encontrada: {pasta_arquivos_id}")

        # 🧠 Gerar nome único para o novo arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extensao = nome_arquivo.split('.')[-1].lower()

        # 🎯 Buscar o último arquivo do dia
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT nome_arquivo FROM arquivos_servico 
                WHERE cod_servico = ? AND nome_arquivo LIKE ?
                ORDER BY nome_arquivo DESC LIMIT 1
            """, (cod_servico, f"{cod_servico}_{timestamp.split('_')[0]}%"))
            ultimo_arquivo = cursor.fetchone()

        novo_numero = (
            int(ultimo_arquivo[0].split('_')[-1].split('.')[0]) + 1
            if ultimo_arquivo else 1
        )
        novo_nome = f"{cod_servico}_{timestamp}_{novo_numero:03d}.{extensao}"
        print(f"📝 Novo nome do arquivo: {novo_nome}")

        # ☁️ Upload do arquivo
        print(f"📤 Enviando arquivo: {novo_nome}")
        # Criar um arquivo temporário
        temp_file = Path(gettempdir()) / novo_nome
        temp_file.write_bytes(arquivo)
        
        # Fazer o upload do arquivo
        drive_file_id = gdrive.upload_file(str(temp_file), pasta_arquivos_id)
        
        # Remover o arquivo temporário
        temp_file.unlink()
        
        if not drive_file_id:
            print("❌ Erro ao fazer upload do arquivo")
            return False
        print(f"✅ Arquivo enviado com sucesso: {drive_file_id}")

        # 💾 Inserir registro no banco
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO arquivos_servico (cod_servico, nome_arquivo, tipo_arquivo, drive_file_id, data_upload, descricao)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                cod_servico, novo_nome, tipo_arquivo, drive_file_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), descricao
            ))
            print("✅ Registro inserido no banco com sucesso")

        return True

    except Exception as e:
        print(f"❌ Erro ao fazer upload do arquivo: {e}")
        return False

def listar_arquivos_servico(cod_servico: str) -> List[Tuple]:
    """Lista todos os arquivos associados a um serviço"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, nome_arquivo, tipo_arquivo, data_upload, descricao, drive_file_id
                FROM arquivos_servico
                WHERE cod_servico = ?
                ORDER BY data_upload DESC
            """, (cod_servico,))
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"❌ Erro ao listar arquivos do serviço: {e}")
        return []


def deletar_arquivo_servico(arquivo_id: int) -> bool:
    """Exclui um arquivo de um serviço"""
    try:
        conn = db.obter_conexao()
        cursor = conn.cursor()
        
        # Obtém informações do arquivo
        cursor.execute("SELECT drive_file_id FROM arquivos_servico WHERE id = ?", (arquivo_id,))
        row = cursor.fetchone()
        if not row:
            print("❌ Arquivo não encontrado no banco")
            return False
            
        drive_file_id = row[0]
        
        # Deleta do Drive
        if not gdrive.delete_file(drive_file_id):
            print("❌ Erro ao deletar arquivo do Drive")
            return False
            
        # Deleta do banco
        cursor.execute("DELETE FROM arquivos_servico WHERE id = ?", (arquivo_id,))
        conn.commit()
        
        print("✅ Arquivo deletado com sucesso")
        return True

    except Exception as e:
        print("❌ Erro ao deletar arquivo:", e)
        return False

def listar_funcionarios_servico(cod_servico: str) -> List[Tuple]:
    """Lista todos os funcionários associados a um serviço"""
    try:
        conn = db.obter_conexao()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.cod_funcionario, f.nome, f.cargo
            FROM funcionarios f
            INNER JOIN servico_funcionarios sf ON f.cod_funcionario = sf.cod_funcionario
            WHERE sf.cod_servico = ?
            ORDER BY f.nome
        """, (cod_servico,))
        resultados = cursor.fetchall()
        return resultados
    except sqlite3.Error as e:
        print(f"❌ Erro ao listar funcionários do serviço: {e}")
        return []

def download_arquivo_servico(arquivo_id: int) -> Optional[bytes]:
    """Baixa um arquivo do serviço pelo ID do registro no banco"""
    try:
        # Busca informações do arquivo no banco
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT nome_arquivo, drive_file_id, tipo_arquivo
                FROM arquivos_servico
                WHERE id = ?
            """, (arquivo_id,))
            row = cursor.fetchone()
            
            if not row:
                print(f"❌ Arquivo não encontrado no banco: {arquivo_id}")
                return None
                
            nome_arquivo, drive_file_id, tipo_arquivo = row
            
        print(f"📥 Iniciando download do arquivo:")
        print(f"   - Nome: {nome_arquivo}")
        print(f"   - Tipo: {tipo_arquivo}")
        print(f"   - ID Drive: {drive_file_id}")
        
        # Cria um arquivo temporário para o download
        temp_file = Path(gettempdir()) / nome_arquivo
        
        # Baixa o arquivo do Drive para o arquivo temporário
        if not gdrive.download_file(drive_file_id, str(temp_file)):
            print("❌ Erro ao baixar arquivo do Drive")
            return None
            
        # Lê o conteúdo do arquivo temporário
        arquivo_bytes = temp_file.read_bytes()
        
        # Remove o arquivo temporário
        temp_file.unlink()
            
        print(f"✅ Arquivo baixado com sucesso")
        return arquivo_bytes
        
    except Exception as e:
        print(f"❌ Erro ao baixar arquivo: {e}")
        return None


def obter_info_arquivo(arquivo_id: int) -> Optional[Tuple]:
    """Obtém informações de um arquivo do serviço"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, nome_arquivo, tipo_arquivo, data_upload, descricao, drive_file_id
                FROM arquivos_servico
                WHERE id = ?
            """, (arquivo_id,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"❌ Erro ao buscar informações do arquivo: {e}")
        return None

def transferir_arquivo_servico(arquivo_id: int, nova_pasta_id: str) -> bool:
    """
    Transfere um arquivo para uma nova pasta e atualiza o banco de dados.
    
    Args:
        arquivo_id (int): ID do arquivo no banco de dados
        nova_pasta_id (str): ID da nova pasta no Google Drive
        
    Returns:
        bool: True se a transferência foi bem sucedida, False caso contrário
    """
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            
            # Obtém informações do arquivo
            cursor.execute("""
                SELECT drive_file_id, cod_servico, nome_arquivo
                FROM arquivos_servico
                WHERE id = ?
            """, (arquivo_id,))
            
            resultado = cursor.fetchone()
            if not resultado:
                print("❌ Arquivo não encontrado no banco de dados")
                return False
                
            drive_file_id, cod_servico, nome_arquivo = resultado
            
            # Move o arquivo no Google Drive
            if not gdrive.move_file(drive_file_id, nova_pasta_id):
                print("❌ Erro ao mover arquivo no Google Drive")
                return False
            
            # Atualiza o registro no banco de dados
            cursor.execute("""
                UPDATE arquivos_servico
                SET pasta_drive = ?
                WHERE id = ?
            """, (nova_pasta_id, arquivo_id))
            
            print(f"✅ Arquivo {nome_arquivo} transferido com sucesso")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao transferir arquivo: {e}")
        return False
