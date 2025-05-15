# backend/Models/model_unidade.py
# -----------------------------------------------------------------------------
#  Camada de dados – Unidades
#  • Sem sys.path hacks; imports diretos
#  • listar_unidades(numero_contrato=None) com filtro opcional
#  • Nenhum upload Drive direto; usa db.marca_sujo()
#  • remove _thread_local; flag sujo é global
#  • Funções auxiliares enxutas, com cache de file_id no session_state
# -----------------------------------------------------------------------------

from __future__ import annotations

import logging
from pathlib import Path
from tempfile import gettempdir
from typing import List, Optional, Tuple

import streamlit as st
from dotenv import load_dotenv

from Database import db_gestaodecontratos as db
from Services import Service_googledrive as gdrive

load_dotenv()
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Helpers Drive ----------------------------------------------------------------
# -----------------------------------------------------------------------------

def _cached_file_id(name: str, parent_id: str | None) -> Optional[str]:
    """Busca file_id no cache de sessão, senão consulta o Drive."""
    key = f"file_id:{parent_id}:{name}"
    if key not in st.session_state:
        st.session_state[key] = gdrive.get_file_id_by_name(name, parent_id)
    return st.session_state[key]

# -----------------------------------------------------------------------------
# CRUD -------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def obter_pasta_contrato(numero_contrato: str, nome_empresa: str) -> Optional[str]:
    """Retorna folder_id do contrato tentando vários formatos de nome."""
    # busca empresa contratada
    empresa_contratada = None
    with db.obter_conexao() as conn:
        row = conn.execute(
            "SELECT empresa_contratada FROM contratos WHERE numero_contrato=?",
            (numero_contrato,),
        ).fetchone()
        if row:
            empresa_contratada = row[0]
    if not empresa_contratada:
        logger.warning("Contrato %s não encontrado", numero_contrato)
        return None

    formatos = [
        f"{numero_contrato}_{empresa_contratada}",
        f"{numero_contrato}_{nome_empresa}",
        f"{numero_contrato}_{empresa_contratada.replace(' ', '_')}",
        f"{numero_contrato}_{nome_empresa.replace(' ', '_')}",
    ]
    root_id = st.session_state.get("GDRIVE_EMPRESAS_FOLDER_ID")

    # procura na raiz
    for nome in formatos:
        fid = _cached_file_id(nome, root_id)
        if fid:
            return fid

    # procura dentro da pasta da empresa
    empresa_id = _cached_file_id(nome_empresa, root_id)
    if not empresa_id:
        return None
    for nome in formatos:
        fid = _cached_file_id(nome, empresa_id)
        if fid:
            return fid
    return None


def obter_nome_empresa_por_contrato(numero_contrato: str) -> Optional[str]:
    with db.obter_conexao() as conn:
        row = conn.execute(
            """
            SELECT e.nome FROM contratos c
            JOIN empresas e ON c.cod_empresa = e.cod_empresa
            WHERE c.numero_contrato = ?
            """,
            (numero_contrato,),
        ).fetchone()
        return row[0] if row else None


def criar_unidade(
    numero_contrato: str,
    nome_unidade: str,
    estado: str,
    cidade: str,
    localizacao: str,
    cod_unidade: str,
) -> bool:
    # nome da empresa para logs
    nome_empresa = obter_nome_empresa_por_contrato(numero_contrato)
    if not nome_empresa:
        logger.error("Empresa não encontrada para contrato %s", numero_contrato)
        return False

    # pasta do contrato deve existir
    with db.obter_conexao() as conn:
        row = conn.execute(
            "SELECT pasta_contrato FROM contratos WHERE numero_contrato=?",
            (numero_contrato,),
        ).fetchone()
        if not row or not row[0]:
            logger.error("Contrato %s sem pasta registr. no DB", numero_contrato)
            return False
        pasta_contrato_id = row[0]

    pasta_unidade_id = gdrive.ensure_folder(
        f"{nome_unidade}_{cod_unidade}", pasta_contrato_id
    )
    if not pasta_unidade_id:
        logger.error("Falha ao criar pasta da unidade no Drive")
        return False

    # grava no banco
    try:
        with db.obter_conexao() as conn:
            conn.execute(
                """
                INSERT INTO unidades
                (cod_unidade, numero_contrato, nome_unidade, estado, cidade, localizacao, pasta_unidade)
                VALUES (?,?,?,?,?,?,?)
                """,
                (cod_unidade, numero_contrato, nome_unidade, estado, cidade, localizacao, pasta_unidade_id),
            )
            db.marca_sujo()
        return True
    except sqlite3.IntegrityError:
        logger.warning("Código de unidade duplicado: %s", cod_unidade)
        return False
    except Exception as e:
        logger.error("Erro ao inserir unidade: %s", e)
        return False


def listar_unidades(numero_contrato: str | None = None) -> List[Tuple]:
    sql = (
        "SELECT cod_unidade, numero_contrato, nome_unidade, estado, cidade, localizacao "
        "FROM unidades"
    )
    params: list[str] = []
    if numero_contrato:
        sql += " WHERE numero_contrato = ?"
        params.append(numero_contrato)
    sql += " ORDER BY nome_unidade"

    with db.obter_conexao() as conn:
        return conn.execute(sql, params).fetchall()


def buscar_unidade_por_codigo(cod_unidade: str) -> Optional[Tuple]:
    with db.obter_conexao() as conn:
        return conn.execute(
            "SELECT * FROM unidades WHERE cod_unidade=?", (cod_unidade,)
        ).fetchone()


def atualizar_unidade(
    cod_unidade: str,
    numero_contrato: str,
    nome_unidade: str,
    estado: str,
    cidade: str,
    localizacao: str,
) -> bool:
    with db.obter_conexao() as conn:
        cur = conn.execute(
            """
            UPDATE unidades
               SET numero_contrato=?, nome_unidade=?, estado=?, cidade=?, localizacao=?
             WHERE cod_unidade=?
            """,
            (numero_contrato, nome_unidade, estado, cidade, localizacao, cod_unidade),
        )
        if cur.rowcount:
            db.marca_sujo()
    return True


def deletar_unidade(cod_unidade: str) -> bool:
    with db.obter_conexao() as conn:
        cur = conn.execute("DELETE FROM unidades WHERE cod_unidade=?", (cod_unidade,))
        if cur.rowcount:
            db.marca_sujo()
    return True
