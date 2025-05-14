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

def gerar_codigo_servico() -> Optional[str]:
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            data_atual = datetime.now().strftime("%Y%m%d")
            cursor.execute("""
                SELECT cod_servico FROM servicos 
                WHERE cod_servico LIKE ? 
                ORDER BY cod_servico DESC LIMIT 1
            """, (f"OS_{data_atual}_%",))
            ultimo_codigo = cursor.fetchone()
            if ultimo_codigo:
                ultimo_numero = int(ultimo_codigo[0].split('_')[-1])
                novo_numero = ultimo_numero + 1
            else:
                novo_numero = 1
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
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT u.nome_unidade, u.pasta_unidade, c.numero_contrato, e.nome \n                            FROM unidades u \n                            JOIN contratos c ON u.numero_contrato = c.numero_contrato \n                            JOIN empresas e ON c.cod_empresa = e.cod_empresa \n                            WHERE u.cod_unidade = ?", (cod_unidade,))
            info_unidade = cursor.fetchone()

        if not info_unidade:
            logger.error(f"❌ Unidade não encontrada: {cod_unidade}")
            return False
        
        nome_unidade, pasta_unidade_id, numero_contrato, nome_empresa = info_unidade
        nome_pasta_servico = f"{cod_servico}_{tipo_servico.replace(' ', '_')}"

        if not pasta_unidade_id:
            logger.info(f"Pasta da unidade {cod_unidade} não encontrada no banco, tentando criar/obter.")
            pasta_contrato_id = obter_pasta_contrato(numero_contrato, nome_empresa)
            if not pasta_contrato_id:
                logger.error(f"Pasta do contrato {numero_contrato} para empresa {nome_empresa} não encontrada.")
                return False
            pasta_unidade_id = gdrive.ensure_folder(f"{nome_unidade}_{cod_unidade}", pasta_contrato_id)
            if not pasta_unidade_id:
                logger.error(f"Não foi possível criar a pasta para a unidade {nome_unidade} no Drive.")
                return False
            with db.obter_conexao() as conn_update: # Nova conexão para este update específico
                cursor_update = conn_update.cursor()
                cursor_update.execute("UPDATE unidades SET pasta_unidade = ? WHERE cod_unidade = ?", (pasta_unidade_id, cod_unidade))
                db.marca_sujo()
                logger.info(f"Pasta da unidade {cod_unidade} atualizada no banco com ID: {pasta_unidade_id}")
        
        pasta_servico_id = gdrive.ensure_folder(nome_pasta_servico, pasta_unidade_id)
        if not pasta_servico_id:
            logger.error(f"Erro ao criar pasta do serviço {nome_pasta_servico} no Drive.")
            return False
        logger.info(f"Pasta do serviço {nome_pasta_servico} criada com ID: {pasta_servico_id}")

        with db.obter_conexao() as conn: # Conexão principal para inserir o serviço
            cursor = conn.cursor()
            cursor.execute("SELECT cod_servico FROM servicos WHERE cod_servico = ?", (cod_servico,))
            if cursor.fetchone():
                logger.warning(f"Tentativa de criar serviço com código duplicado: {cod_servico}")
                return False
            
            cursor.execute("""
                INSERT INTO servicos (
                    cod_servico, cod_unidade, tipo_servico, data_criacao, 
                    data_execucao, status, observacoes, pasta_servico
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cod_servico, cod_unidade, tipo_servico, data_criacao,
                data_execucao, status, observacoes, pasta_servico_id
            ))
            db.marca_sujo()
            logger.info(f"Serviço {cod_servico} inserido no banco de dados.")

            # Salva o estado do banco de dados no Drive
            caminho_banco_local = Path(gettempdir()) / db.DB_NAME
            try:
                db.salvar_banco_no_drive(caminho_banco_local)
                logger.info(f"Banco de dados salvo no Drive após criação do serviço {cod_servico}.")
                return True
            except Exception as e_save:
                logger.error(f"Erro ao salvar banco no Drive após criar serviço {cod_servico}: {e_save}")
                return True # Retorna True pois a operação no banco local foi bem-sucedida

    except Exception as e_main:
        logger.error(f"Erro geral ao criar serviço {cod_servico}: {e_main}")
        return False


def listar_servicos() -> List[Tuple]:
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM servicos ORDER BY data_criacao DESC")
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Erro ao listar serviços: {e}")
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


def atualizar_servico(cod_servico_original: str, novo_tipo_servico: str, nova_data_execucao: str, novo_status: str, novas_observacoes: str) -> bool:
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE servicos 
                SET tipo_servico = ?, data_execucao = ?, status = ?, observacoes = ?
                WHERE cod_servico = ?
            """, (novo_tipo_servico, nova_data_execucao, novo_status, novas_observacoes, cod_servico_original))
            db.marca_sujo()
        
        caminho_banco_local = Path(gettempdir()) / db.DB_NAME
        try:
            db.salvar_banco_no_drive(caminho_banco_local)
            logger.info(f"Serviço {cod_servico_original} atualizado e banco salvo no Drive.")
            return True
        except Exception as e_save:
            logger.error(f"Erro ao salvar banco no Drive após atualizar serviço {cod_servico_original}: {e_save}")
            return True # Operação local bem-sucedida
            
    except Exception as e_main:
        logger.error(f"Erro ao atualizar serviço {cod_servico_original}: {e_main}")
        return False

def deletar_servico(cod_servico: str) -> bool:
    try:
        with db.obter_conexao() as conn: # Primeira conexão para deletar de servico_funcionarios
            cursor = conn.cursor()
            cursor.execute("DELETE FROM servico_funcionarios WHERE cod_servico = ?", (cod_servico,))
            db.marca_sujo() # Marca sujo após o primeiro delete

        with db.obter_conexao() as conn: # Segunda conexão para deletar de servicos
            cursor = conn.cursor()
            cursor.execute("DELETE FROM servicos WHERE cod_servico = ?", (cod_servico,))
            db.marca_sujo() # Marca sujo após o segundo delete
        
        caminho_banco_local = Path(gettempdir()) / db.DB_NAME
        try:
            db.salvar_banco_no_drive(caminho_banco_local)
            logger.info(f"Serviço {cod_servico} deletado e banco salvo no Drive.")
            return True
        except Exception as e_save:
            logger.error(f"Erro ao salvar banco no Drive após deletar serviço {cod_servico}: {e_save}")
            return True # Operação local bem-sucedida

    except Exception as e_main:
        logger.error(f"Erro ao deletar serviço {cod_servico}: {e_main}")
        return False

# ──────────────── Funções de Arquivos ────────────────

def upload_arquivo_servico(cod_servico: str, arquivo_upload: st.runtime.uploaded_file_manager.UploadedFile, descricao: Optional[str] = None) -> bool:
    arquivo_bytes = arquivo_upload.getvalue()
    nome_arquivo_original = arquivo_upload.name
    tipo_arquivo = arquivo_upload.type
    
    try:
        logger.info(f"Iniciando upload do arquivo: {nome_arquivo_original} para o serviço: {cod_servico}")
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pasta_servico FROM servicos WHERE cod_servico = ?", (cod_servico,))
            row = cursor.fetchone()
            if not row or not row[0]:
                logger.error(f"Pasta do serviço {cod_servico} não encontrada no banco.")
                return False
            pasta_servico_id = row[0]
        
        pasta_arquivos_nome = "Arquivos"
        pasta_arquivos_id = gdrive.ensure_folder(pasta_arquivos_nome, pasta_servico_id)
        if not pasta_arquivos_id:
            logger.error(f"Erro ao criar/garantir a pasta \"{pasta_arquivos_nome}\" no Drive para o serviço {cod_servico}.")
            return False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extensao = nome_arquivo_original.split('.')[-1].lower() if '.' in nome_arquivo_original else ''
        
        with db.obter_conexao() as conn_seq:
            cursor_seq = conn_seq.cursor()
            cursor_seq.execute("""
                SELECT nome_arquivo FROM arquivos_servico 
                WHERE cod_servico = ? AND nome_arquivo LIKE ?
                ORDER BY nome_arquivo DESC LIMIT 1
            """, (cod_servico, f"{cod_servico}_{timestamp.split('_')[0]}%"))
            ultimo_arquivo_seq = cursor_seq.fetchone()
        
        novo_numero_seq = 1
        if ultimo_arquivo_seq and ultimo_arquivo_seq[0]:
            try:
                partes_nome = ultimo_arquivo_seq[0].split('_')
                if len(partes_nome) > 2:
                    num_str = partes_nome[-1].split('.')[0]
                    if num_str.isdigit():
                        novo_numero_seq = int(num_str) + 1
            except ValueError:
                pass # Mantém novo_numero_seq = 1 se o parsing falhar

        novo_nome_arquivo = f"{cod_servico}_{timestamp}_{novo_numero_seq:03d}{f'.{extensao}' if extensao else ''}"
        
        temp_path = Path(gettempdir()) / novo_nome_arquivo
        try:
            with open(temp_path, "wb") as f:
                f.write(arquivo_bytes)
            
            drive_file_id = gdrive.upload_file(str(temp_path), pasta_arquivos_id)
            if not drive_file_id:
                logger.error(f"Falha no upload do arquivo {novo_nome_arquivo} para o Drive.")
                return False
        finally:
            if temp_path.exists():
                temp_path.unlink() # Garante que o arquivo temporário seja removido

        with db.obter_conexao() as conn_insert:
            cursor_insert = conn_insert.cursor()
            cursor_insert.execute("""
                INSERT INTO arquivos_servico (
                    cod_servico, nome_arquivo, tipo_arquivo, drive_file_id, data_upload, descricao
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                cod_servico, novo_nome_arquivo, tipo_arquivo, drive_file_id, 
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                descricao
            ))
            db.marca_sujo()
            logger.info(f"Registro do arquivo {novo_nome_arquivo} salvo no banco.")

        caminho_banco_local = Path(gettempdir()) / db.DB_NAME
        try:
            db.salvar_banco_no_drive(caminho_banco_local)
            logger.info(f"Upload do arquivo {novo_nome_arquivo} e atualização do banco concluídos.")
            return True
        except Exception as e_save:
            logger.error(f"Erro ao salvar banco no Drive após upload do arquivo: {e_save}")
            return True # Operação local no banco bem-sucedida

    except Exception as e_main:
        logger.error(f"Erro geral no upload do arquivo para o serviço {cod_servico}: {e_main}")
        return False

def deletar_arquivo_servico(arquivo_id: int) -> bool:
    try:
        drive_file_id_para_deletar = None
        nome_arquivo_deletado = "[desconhecido]"
        with db.obter_conexao() as conn_select:
            cursor_select = conn_select.cursor()
            cursor_select.execute("SELECT drive_file_id, nome_arquivo FROM arquivos_servico WHERE id = ?", (arquivo_id,))
            res = cursor_select.fetchone()
            if res:
                drive_file_id_para_deletar, nome_arquivo_deletado = res
            else:
                logger.warning(f"Arquivo com ID {arquivo_id} não encontrado no banco para deleção.")
                # Considerar retornar False se o arquivo não existe no banco, 
                # mas a lógica atual prossegue para tentar deletar do Drive se o ID for conhecido
                # e depois tenta deletar do banco (o que não fará nada se não existir).

        if drive_file_id_para_deletar:
            if gdrive.delete_file(drive_file_id_para_deletar):
                logger.info(f"Arquivo {nome_arquivo_deletado} (ID Drive: {drive_file_id_para_deletar}) deletado do Google Drive.")
            else:
                logger.warning(f"Falha ao deletar arquivo {nome_arquivo_deletado} (ID Drive: {drive_file_id_para_deletar}) do Google Drive. Pode já ter sido removido.")
        
        with db.obter_conexao() as conn_delete:
            cursor_delete = conn_delete.cursor()
            cursor_delete.execute("DELETE FROM arquivos_servico WHERE id = ?", (arquivo_id,))
            # Verifica se alguma linha foi afetada para marcar como sujo
            if cursor_delete.rowcount > 0:
                db.marca_sujo()
                logger.info(f"Registro do arquivo (ID: {arquivo_id}) deletado do banco de dados.")
            else:
                logger.info(f"Nenhum registro de arquivo com ID {arquivo_id} encontrado para deletar do banco (pode já ter sido removido).")

        caminho_banco_local = Path(gettempdir()) / db.DB_NAME
        if getattr(db._thread_local, "dirty", False): # Salva apenas se algo foi realmente modificado
            try:
                db.salvar_banco_no_drive(caminho_banco_local)
                logger.info(f"Banco de dados salvo no Drive após deleção do arquivo {arquivo_id}.")
            except Exception as e_save:
                logger.error(f"Erro ao salvar banco no Drive após deletar arquivo {arquivo_id}: {e_save}")
                return True # Operação local no banco (deleção) pode ter sido bem-sucedida
        return True
            
    except Exception as e_main:
        logger.error(f"Erro ao deletar arquivo do serviço (ID: {arquivo_id}): {e_main}")
        return False

def atualizar_descricao_arquivo(arquivo_id: int, nova_descricao: str) -> bool:
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE arquivos_servico SET descricao = ? WHERE id = ?", (nova_descricao, arquivo_id))
            if cursor.rowcount > 0:
                 db.marca_sujo()
        
        if getattr(db._thread_local, "dirty", False):
            caminho_banco_local = Path(gettempdir()) / db.DB_NAME
            try:
                db.salvar_banco_no_drive(caminho_banco_local)
                logger.info(f"Descrição do arquivo {arquivo_id} atualizada e banco salvo.")
                return True
            except Exception as e_save:
                logger.error(f"Erro ao salvar banco no Drive após atualizar descrição: {e_save}")
                return True # Operação local bem-sucedida
        else:
            logger.info(f"Descrição do arquivo {arquivo_id} não precisou de atualização ou não foi encontrada.")
            return True # Considera sucesso se não houve erro e nenhuma alteração era necessária/possível
            
    except Exception as e_main:
        logger.error(f"Erro ao atualizar descrição do arquivo {arquivo_id}: {e_main}")
        return False

def transferir_arquivo_servico(arquivo_id: int, nova_pasta_id: str) -> bool:
    try:
        with db.obter_conexao() as conn_select: # Conexão apenas para leitura inicial
            cursor = conn_select.cursor()
            cursor.execute("SELECT drive_file_id, nome_arquivo FROM arquivos_servico WHERE id = ?", (arquivo_id,))
            resultado = cursor.fetchone()
            if not resultado:
                logger.error(f"❌ Arquivo com ID {arquivo_id} não encontrado no banco de dados para transferência.")
                return False
            drive_file_id, nome_arquivo = resultado
            
        file_metadata = gdrive.get_service().files().get(fileId=drive_file_id, fields="parents").execute()
        old_parent_id = file_metadata.get('parents')[0] if file_metadata.get('parents') else None

        if not old_parent_id:
            logger.warning(f"Não foi possível determinar a pasta pai original do arquivo {drive_file_id} (Nome: {nome_arquivo}). A tentativa de mover prosseguirá.")

        if not gdrive.move_file(drive_file_id, nova_pasta_id, old_parent_id):
            logger.error(f"❌ Erro ao mover arquivo {nome_arquivo} (ID Drive: {drive_file_id}) no Google Drive para a pasta {nova_pasta_id}.")
            return False
        
        logger.info(f"✅ Arquivo {nome_arquivo} (ID Drive: {drive_file_id}) movido para pasta {nova_pasta_id} no Drive.")
        # Nenhuma alteração no banco de dados é realizada por esta função atualmente.
        # Se, no futuro, a tabela 'arquivos_servico' tiver um campo para armazenar 'pasta_drive_id',
        # aqui seria o local para um UPDATE e db.marca_sujo(), seguido por db.salvar_banco_no_drive().
        # Exemplo:
        # with db.obter_conexao() as conn_update:
        #     cursor_update = conn_update.cursor()
        #     cursor_update.execute("UPDATE arquivos_servico SET pasta_drive_atual_id = ? WHERE id = ?", (nova_pasta_id, arquivo_id))
        #     if cursor_update.rowcount > 0:
        #         db.marca_sujo()
        #         # Chamar db.salvar_banco_no_drive() se sujo
        return True # Retorna True pois a operação no Drive foi bem-sucedida.
            
    except Exception as e:
        logger.error(f"❌ Erro ao transferir arquivo (ID: {arquivo_id}): {e}")
        return False

def listar_arquivos_servico(cod_servico: str) -> List[Tuple]:
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
        logger.error(f"Erro ao listar arquivos do serviço {cod_servico}: {e}")
        return []


def listar_funcionarios_servico(cod_servico: str) -> List[Tuple]:
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            # Exemplo de JOIN para obter nomes dos funcionários
            cursor.execute("""
                SELECT f.cod_funcionario, f.nome, f.funcao
                FROM servico_funcionarios sf
                JOIN funcionarios f ON sf.cod_funcionario = f.cod_funcionario
                WHERE sf.cod_servico = ?
            """, (cod_servico,))
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Erro ao listar funcionários do serviço {cod_servico}: {e}")
        return []

def download_arquivo_servico(arquivo_id: int) -> Optional[Tuple[bytes, str, str]]:
    temp_file_path = None
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nome_arquivo, drive_file_id, tipo_arquivo FROM arquivos_servico WHERE id = ?", (arquivo_id,))
            row = cursor.fetchone()
            if not row:
                logger.error(f"Arquivo com ID {arquivo_id} não encontrado no banco.")
                return None
            nome_arquivo, drive_file_id, tipo_arquivo = row
            
        logger.info(f"Iniciando download do arquivo: {nome_arquivo} (ID Drive: {drive_file_id})")
        temp_file_path = Path(gettempdir()) / nome_arquivo
        
        if not gdrive.download_file(drive_file_id, str(temp_file_path)):
            logger.error(f"Erro ao baixar arquivo {nome_arquivo} do Drive.")
            return None
            
        if not temp_file_path.exists() or temp_file_path.stat().st_size == 0:
            logger.error(f"Arquivo {nome_arquivo} baixado do Drive está vazio ou não existe localmente.")
            return None
            
        file_bytes = temp_file_path.read_bytes()
        logger.info(f"Arquivo {nome_arquivo} baixado com sucesso ({len(file_bytes)} bytes).")
        return file_bytes, nome_arquivo, tipo_arquivo

    except Exception as e:
        logger.error(f"Erro no processo de download do arquivo {arquivo_id}: {e}")
        return None
    finally:
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except Exception as e_unlink:
                logger.warning(f"Falha ao remover arquivo temporário {temp_file_path}: {e_unlink}")

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
