# backend/Models/model_servico_funcionarios.py

import sqlite3
from typing import List, Tuple
from pathlib import Path
import sys
from tempfile import gettempdir

# Adiciona o caminho do backend para importar corretamente o módulo do banco de dados
sys.path.append(str(Path(__file__).resolve().parents[1]))
from Database import db_gestaodecontratos as db

# ──────────────── Associação entre Serviços e Funcionários ────────────────

def atribuir_funcionario_a_servico(cod_servico: str, cod_funcionario: str) -> bool:
    """Atribui um funcionário a um serviço"""
    try:
        conn = db.obter_conexao()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO servico_funcionarios (cod_servico, cod_funcionario)
            VALUES (?, ?)
        """, (cod_servico, cod_funcionario))
        db.marca_sujo()
        db.salvar_banco_no_drive()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao atribuir funcionário ao serviço: {e}")
        return False


def listar_funcionarios_por_servico(cod_servico: str) -> List[Tuple]:
    """Lista todos os funcionários associados a um serviço"""
    try:
        with db.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.* 
                FROM funcionarios f
                INNER JOIN servico_funcionarios sf ON f.cod_funcionario = sf.cod_funcionario
                WHERE sf.cod_servico = ?
            """, (cod_servico,))
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"❌ Erro ao listar funcionários do serviço: {e}")
        return []


def listar_servicos_por_funcionario(cod_funcionario: str) -> List[Tuple]:
    """Lista todos os serviços associados a um funcionário"""
    try:
        conn = db.obter_conexao()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.* 
            FROM servicos s
            INNER JOIN servico_funcionarios sf ON s.cod_servico = sf.cod_servico
            WHERE sf.cod_funcionario = ?
        """, (cod_funcionario,))
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Erro ao listar serviços do funcionário: {e}")
        return []


def remover_funcionario_de_servico(cod_servico: str, cod_funcionario: str) -> bool:
    """Remove um funcionário de um serviço"""
    try:
        conn = db.obter_conexao()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM servico_funcionarios 
            WHERE cod_servico = ? AND cod_funcionario = ?
        """, (cod_servico, cod_funcionario))
        if cursor.rowcount > 0:
            db.marca_sujo()
        db.salvar_banco_no_drive()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao remover funcionário do serviço: {e}")
        return False
