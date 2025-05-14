# backend/Models/model_funcionario.py

import sqlite3
from typing import List, Optional, Tuple
from pathlib import Path
import sys
import logging
from tempfile import gettempdir

# Adiciona o caminho do backend para importar corretamente o módulo do banco de dados
sys.path.append(str(Path(__file__).resolve().parents[1]))
from Database import db_gestaodecontratos as db

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ───────────────── CRUD de Funcionários ─────────────────

def criar_funcionario(nome: str, data_nascimento: str, cpf: str, cod_funcionario: str, funcao: str) -> bool:
    """Cria um novo funcionário no banco de dados"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM funcionarios WHERE cpf = ? OR cod_funcionario = ?", (cpf, cod_funcionario))
            if cursor.fetchone():
                logger.warning(f"Tentativa de criar funcionário com CPF ({cpf}) ou Código ({cod_funcionario}) duplicado.")
                return False

            cursor.execute("""
                INSERT INTO funcionarios (nome, data_nascimento, cpf, cod_funcionario, funcao)
                VALUES (?, ?, ?, ?, ?)
            """, (nome, data_nascimento, cpf, cod_funcionario, funcao))
            db.marca_sujo()
            logger.info(f"Funcionário {cod_funcionario} - {nome} inserido no banco.")

        caminho_banco_local = Path(gettempdir()) / db.DB_NAME
        try:
            db.salvar_banco_no_drive(caminho_banco_local)
            logger.info(f"Banco de dados salvo no Drive após criação do funcionário {cod_funcionario}.")
            return True
        except Exception as e_save:
            logger.error(f"Erro ao salvar banco no Drive após criar funcionário: {e_save}")
            return True # Operação local bem-sucedida
            
    except Exception as e_main:
        logger.error(f"Erro ao criar funcionário: {e_main}")
        return False

def listar_funcionarios() -> List[Tuple]:
    """Lista todos os funcionários"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cod_funcionario, nome, cpf, data_nascimento, funcao FROM funcionarios ORDER BY nome")
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Erro ao listar funcionários: {e}")
        return []

def buscar_funcionario_por_id(funcionario_id: int) -> Optional[Tuple]:
    """Busca um funcionário pelo ID"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM funcionarios WHERE id = ?", (funcionario_id,))
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Erro ao buscar funcionário: {e}")
        return None

def atualizar_funcionario(cod_funcionario_original: str, novo_nome: str, nova_data_nascimento: str, novo_cpf: str, nova_funcao: str) -> bool:
    """Atualiza os dados de um funcionário"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            # Verificar duplicação de CPF para outros funcionários
            cursor.execute("SELECT id FROM funcionarios WHERE cpf = ? AND cod_funcionario != ?", (novo_cpf, cod_funcionario_original))
            if cursor.fetchone():
                logger.warning(f"Tentativa de atualizar funcionário {cod_funcionario_original} para CPF ({novo_cpf}) duplicado.")
                return False

            cursor.execute("""
                UPDATE funcionarios 
                SET nome = ?, data_nascimento = ?, cpf = ?, funcao = ?
                WHERE cod_funcionario = ?
            """, (novo_nome, nova_data_nascimento, novo_cpf, nova_funcao, cod_funcionario_original))
            
            if cursor.rowcount > 0:
                db.marca_sujo()
            else:
                logger.info(f"Nenhum funcionário encontrado com o código {cod_funcionario_original} para atualizar, ou os dados são os mesmos.")
                return True

        if getattr(db._thread_local, "dirty", False):
            caminho_banco_local = Path(gettempdir()) / db.DB_NAME
            try:
                db.salvar_banco_no_drive(caminho_banco_local)
                logger.info(f"Funcionário {cod_funcionario_original} atualizado e banco salvo.")
            except Exception as e_save:
                logger.error(f"Erro ao salvar banco no Drive após atualizar funcionário: {e_save}")
                return True # Operação local bem-sucedida
        return True 
            
    except Exception as e_main:
        logger.error(f"Erro ao atualizar funcionário: {e_main}")
        return False

def deletar_funcionario(cod_funcionario: str) -> bool:
    """Deleta um funcionário"""
    try:
        # Verificar se o funcionário está associado a algum serviço em servico_funcionarios
        with db.obter_conexao() as conn_check_deps:
            cursor_deps = conn_check_deps.cursor()
            cursor_deps.execute("SELECT COUNT(*) FROM servico_funcionarios WHERE cod_funcionario = ?", (cod_funcionario,))
            if cursor_deps.fetchone()[0] > 0:
                logger.warning(f"Tentativa de deletar funcionário {cod_funcionario} que está associado a serviços.")
                # Idealmente, informar ao usuário através de st.error ou similar se no contexto de UI
                return False # Impedir a deleção

        with db.obter_conexao() as conn_delete:
            cursor_delete = conn_delete.cursor()
            cursor_delete.execute("DELETE FROM funcionarios WHERE cod_funcionario = ?", (cod_funcionario,))
            if cursor_delete.rowcount > 0:
                db.marca_sujo()
                logger.info(f"Funcionário {cod_funcionario} deletado do banco.")
            else:
                logger.info(f"Funcionário {cod_funcionario} não encontrado no banco para deleção.")
                return True

        if getattr(db._thread_local, "dirty", False):
            caminho_banco_local = Path(gettempdir()) / db.DB_NAME
            try:
                db.salvar_banco_no_drive(caminho_banco_local)
                logger.info(f"Banco de dados salvo no Drive após deleção do funcionário {cod_funcionario}.")
            except Exception as e_save:
                logger.error(f"Erro ao salvar banco no Drive após deletar funcionário: {e_save}")
                return True # Operação local bem-sucedida
        return True

    except Exception as e_main:
        logger.error(f"Erro ao deletar funcionário: {e_main}")
        return False

def buscar_funcionario_por_codigo(cod_funcionario: str) -> Optional[Tuple]:
    """Busca um funcionário pelo código"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM funcionarios WHERE cod_funcionario = ?", (cod_funcionario,))
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Erro ao buscar funcionário: {e}")
        return None
