# backend/Models/model_funcionario.py
# -----------------------------------------------------------------------------
#  Camada de dados – Funcionários
#  • Imports limpos (sem sys.path hacks)
#  • listar_funcionarios() com filtros opcionais e paginação
#  • Models chamam db.marca_sujo() após INSERT / UPDATE / DELETE
#  • Nenhum upload Drive direto – db_gestaodecontratos gerencia isso
#  • Validação de CPF continua como está (duplicação, mas sem regex)
# -----------------------------------------------------------------------------

from __future__ import annotations

import logging
from pathlib import Path
from tempfile import gettempdir
from typing import List, Optional, Sequence, Tuple

from Database import db_gestaodecontratos as db

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
#  CRUD ------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def criar_funcionario(
    nome: str,
    data_nascimento: str,
    cpf: str,
    cod_funcionario: str,
    funcao: str,
) -> bool:
    """Insere novo funcionário. Retorna True se sucesso."""
    try:
        with db.obter_conexao() as conn:
            cur = conn.cursor()
            # checa duplicidade cpf ou código
            if cur.execute(
                "SELECT 1 FROM funcionarios WHERE cpf=? OR cod_funcionario=?",
                (cpf, cod_funcionario),
            ).fetchone():
                logger.warning(
                    "CPF (%s) ou código (%s) duplicado ao tentar criar funcionário",
                    cpf,
                    cod_funcionario,
                )
                return False

            cur.execute(
                """
                INSERT INTO funcionarios
                      (nome, data_nascimento, cpf, cod_funcionario, funcao)
                VALUES (?,?,?,?,?)
                """,
                (nome, data_nascimento, cpf, cod_funcionario, funcao),
            )
            db.marca_sujo()
            logger.info("Funcionário %s (%s) inserido.", cod_funcionario, nome)
            return True
    except Exception as e:
        logger.error("Erro ao criar funcionário: %s", e)
        return False


def listar_funcionarios(
    nome_like: str | None = None,
    funcao_like: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> List[Tuple]:
    """Lista funcionários com filtros opcionais. Retorna tuples em ordem de nome."""
    sql = (
        "SELECT cod_funcionario, nome, cpf, data_nascimento, funcao, id "
        "FROM funcionarios WHERE 1=1"
    )
    params: list[str] = []
    if nome_like:
        sql += " AND nome LIKE ?"
        params.append(f"%{nome_like}%")
    if funcao_like:
        sql += " AND funcao LIKE ?"
        params.append(f"%{funcao_like}%")
    sql += " ORDER BY nome"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
        if offset is not None:
            sql += " OFFSET ?"
            params.append(offset)

    try:
        with db.obter_conexao() as conn:
            return conn.execute(sql, params).fetchall()
    except Exception as e:
        logger.error("Erro ao listar funcionários: %s", e)
        return []


def buscar_funcionario_por_id(funcionario_id: int) -> Optional[Tuple]:
    try:
        with db.obter_conexao() as conn:
            return conn.execute(
                "SELECT * FROM funcionarios WHERE id=?", (funcionario_id,)
            ).fetchone()
    except Exception as e:
        logger.error("Erro ao buscar funcionário: %s", e)
        return None


def buscar_funcionario_por_codigo(cod_funcionario: str) -> Optional[Tuple]:
    try:
        with db.obter_conexao() as conn:
            return conn.execute(
                "SELECT * FROM funcionarios WHERE cod_funcionario=?",
                (cod_funcionario,),
            ).fetchone()
    except Exception as e:
        logger.error("Erro ao buscar funcionário por código: %s", e)
        return None


def atualizar_funcionario(
    cod_funcionario_original: str,
    novo_nome: str,
    nova_data_nascimento: str,
    novo_cpf: str,
    nova_funcao: str,
) -> bool:
    try:
        with db.obter_conexao() as conn:
            cur = conn.cursor()
            # verificar duplicidade de CPF para outros registros
            if cur.execute(
                "SELECT 1 FROM funcionarios WHERE cpf=? AND cod_funcionario!=?",
                (novo_cpf, cod_funcionario_original),
            ).fetchone():
                logger.warning(
                    "CPF duplicado ao atualizar funcionário %s -> %s",
                    cod_funcionario_original,
                    novo_cpf,
                )
                return False

            cur.execute(
                """
                UPDATE funcionarios
                   SET nome=?, data_nascimento=?, cpf=?, funcao=?
                 WHERE cod_funcionario=?
                """,
                (
                    novo_nome,
                    nova_data_nascimento,
                    novo_cpf,
                    nova_funcao,
                    cod_funcionario_original,
                ),
            )
            if cur.rowcount > 0:
                db.marca_sujo()
                logger.info("Funcionário %s atualizado.", cod_funcionario_original)
            return True
    except Exception as e:
        logger.error("Erro ao atualizar funcionário: %s", e)
        return False


def deletar_funcionario(cod_funcionario: str) -> bool:
    try:
        # Checa dependências em serviços
        with db.obter_conexao() as conn:
            if conn.execute(
                "SELECT 1 FROM servico_funcionarios WHERE cod_funcionario=?",
                (cod_funcionario,),
            ).fetchone():
                logger.warning(
                    "Não é possível excluir funcionário %s – possui serviços vinculados.",
                    cod_funcionario,
                )
                return False

            cur = conn.cursor()
            cur.execute(
                "DELETE FROM funcionarios WHERE cod_funcionario=?", (cod_funcionario,)
            )
            if cur.rowcount > 0:
                db.marca_sujo()
                logger.info("Funcionário %s deletado.", cod_funcionario)
            return True
    except Exception as e:
        logger.error("Erro ao deletar funcionário: %s", e)
        return False
