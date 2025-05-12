# backend/Models/model_funcionario.py

import sqlite3
from typing import List, Optional, Tuple
from pathlib import Path
import sys
from tempfile import gettempdir

# Adiciona o caminho do backend para importar corretamente o módulo do banco de dados
sys.path.append(str(Path(__file__).resolve().parents[1]))
from Database import db_gestaodecontratos as db

# ───────────────── CRUD de Funcionários ─────────────────

def criar_funcionario(nome: str, data_nascimento: str, cpf: str, cod_funcionario: str, funcao: str) -> bool:
    """Cria um novo funcionário no banco de dados"""
    try:
        conn = db.obter_conexao()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO funcionarios (nome, data_nascimento, cpf, cod_funcionario, funcao)
            VALUES (?, ?, ?, ?, ?)
        """, (nome, data_nascimento, cpf, cod_funcionario, funcao))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao criar funcionário: {e}")
        return False


def listar_funcionarios() -> List[Tuple]:
    """Lista todos os funcionários cadastrados"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM funcionarios")
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"❌ Erro ao listar funcionários: {e}")
        return []


def buscar_funcionario_por_id(func_id: int) -> Optional[Tuple]:
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM funcionarios WHERE id = ?", (func_id,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"❌ Erro ao buscar funcionário: {e}")
        return None


def atualizar_funcionario(func_id: int, nome: str, data_nascimento: str, cpf: str, cod_funcionario: str, funcao: str) -> bool:
    """Atualiza os dados de um funcionário"""
    try:
        conn = db.obter_conexao()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE funcionarios 
            SET nome = ?, data_nascimento = ?, cpf = ?, cod_funcionario = ?, funcao = ?
            WHERE id = ?
        """, (nome, data_nascimento, cpf, cod_funcionario, funcao, func_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao atualizar funcionário: {e}")
        return False


def deletar_funcionario(func_id: int) -> bool:
    """Exclui um funcionário do banco de dados"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM funcionarios WHERE id = ?", (func_id,))
            return True
    except sqlite3.Error as e:
        print(f"❌ Erro ao excluir funcionário: {e}")
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
