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
        # Primeiro verifica se o CPF ou código já existe
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            
            # Verifica CPF
            cursor.execute("SELECT id FROM funcionarios WHERE cpf = ?", (cpf,))
            if cursor.fetchone():
                logger.warning(f"Tentativa de criar funcionário com CPF duplicado: {cpf}")
                return False
                
            # Verifica código
            cursor.execute("SELECT id FROM funcionarios WHERE cod_funcionario = ?", (cod_funcionario,))
            if cursor.fetchone():
                logger.warning(f"Tentativa de criar funcionário com código duplicado: {cod_funcionario}")
                return False

            # Se não existe, cria o novo funcionário
            cursor.execute("""
                INSERT INTO funcionarios (nome, data_nascimento, cpf, cod_funcionario, funcao)
                VALUES (?, ?, ?, ?, ?)
            """, (nome, data_nascimento, cpf, cod_funcionario, funcao))
            
            # Força o commit
            conn.commit()
            
            # Salva no Drive
            caminho_banco = Path(gettempdir()) / db.DB_NAME
            try:
                db.salvar_banco_no_drive(caminho_banco)
                logger.info(f"Funcionário {nome} criado com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao salvar banco no Drive: {e}")
                # Mesmo com erro no Drive, o funcionário foi criado localmente
                return True
                
    except Exception as e:
        logger.error(f"Erro ao criar funcionário: {e}")
        return False

def listar_funcionarios() -> List[Tuple]:
    """Lista todos os funcionários"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM funcionarios")
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

def atualizar_funcionario(funcionario_id: int, nome: str, data_nascimento: str, cpf: str, cod_funcionario: str, funcao: str) -> bool:
    """Atualiza os dados de um funcionário"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            
            # Verifica se o CPF ou código já existe (exceto para o próprio funcionário)
            cursor.execute("""
                SELECT id FROM funcionarios 
                WHERE (cpf = ? OR cod_funcionario = ?) AND id != ?
            """, (cpf, cod_funcionario, funcionario_id))
            
            if cursor.fetchone():
                logger.warning(f"Tentativa de atualizar para CPF ou código já existente")
                return False

            # Atualiza o funcionário
            cursor.execute("""
                UPDATE funcionarios
                SET nome = ?, data_nascimento = ?, cpf = ?, cod_funcionario = ?, funcao = ?
                WHERE id = ?
            """, (nome, data_nascimento, cpf, cod_funcionario, funcao, funcionario_id))
            
            # Força o commit
            conn.commit()
            
            # Salva no Drive
            caminho_banco = Path(gettempdir()) / db.DB_NAME
            try:
                db.salvar_banco_no_drive(caminho_banco)
                logger.info(f"Funcionário {nome} atualizado com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao salvar banco no Drive: {e}")
                # Mesmo com erro no Drive, o funcionário foi atualizado localmente
                return True
                
    except Exception as e:
        logger.error(f"Erro ao atualizar funcionário: {e}")
        return False

def deletar_funcionario(funcionario_id: int) -> bool:
    """Deleta um funcionário"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM funcionarios WHERE id = ?", (funcionario_id,))
            
            # Força o commit
            conn.commit()

            # Salva no Drive
            caminho_banco = Path(gettempdir()) / db.DB_NAME
            try:
                db.salvar_banco_no_drive(caminho_banco)
                logger.info(f"Funcionário {funcionario_id} deletado com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao salvar banco no Drive: {e}")
                # Mesmo com erro no Drive, o funcionário foi deletado localmente
                return True
                
    except Exception as e:
        logger.error(f"Erro ao deletar funcionário: {e}")
        return False

def buscar_funcionario_por_codigo(cod_funcionario: str) -> Tuple:
    """Busca um funcionário pelo código"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM funcionarios WHERE cod_funcionario = ?", (cod_funcionario,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"❌ Erro ao buscar funcionário: {e}")
        return None
