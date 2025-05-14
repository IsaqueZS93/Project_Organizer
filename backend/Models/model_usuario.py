# backend/Models/model_usuario.py
# -----------------------------------------------------------------------------
#  Camada de acesso a dados – Usuários
#  • Filtros flexíveis em listar_usuarios(nome_like, tipos, limit, offset)
#  • Helper _sync_after_write → centraliza commit + upload Drive
#  • Sem sys.path hacks (projeto deve estar configurado como pacote)
#  • Todas as senhas ainda são armazenadas em texto puro (hash em etapa futura)
# -----------------------------------------------------------------------------

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from tempfile import gettempdir
from typing import List, Optional, Sequence, Tuple
import sys

from Database.db_gestaodecontratos import (
    DB_NAME,
    obter_conexao,
    salvar_banco_no_drive,
)
from Database import db_gestaodecontratos as db

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
#  Utilitário interno -----------------------------------------------------------
# -----------------------------------------------------------------------------

def _sync_after_write(conn: sqlite3.Connection) -> bool:
    """Commit + tentativa de upload do banco. Retorna True se commit ok."""
    try:
        conn.commit()
        caminho_banco = Path(gettempdir()) / DB_NAME
        salvar_banco_no_drive(caminho_banco)  # já faz tratamento de conflito
        return True
    except Exception as e:
        logger.error("Erro no commit/sync Drive: %s", e)
        return False

# -----------------------------------------------------------------------------
#  CRUD ------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def criar_usuario(
    nome: str,
    data_nascimento: str,
    funcao: str,
    usuario: str,
    senha: str,
    tipo: str,
) -> bool:
    try:
        with db.obter_conexao() as conn:
            cur = conn.cursor()
            if cur.execute("SELECT 1 FROM usuarios WHERE usuario = ?", (usuario,)).fetchone():
                logger.warning("Usuário duplicado: %s", usuario)
                return False

            cur.execute(
                """
                INSERT INTO usuarios (nome, data_nascimento, funcao, usuario, senha, tipo)
                VALUES (?,?,?,?,?,?)
                """,
                (nome, data_nascimento, funcao, usuario, senha, tipo),
            )
            db.marca_sujo()
            return _sync_after_write(conn)
    except Exception as e:
        logger.error("Erro ao criar usuário: %s", e)
        return False


def listar_usuarios(
    nome_like: str | None = None,
    tipos: Sequence[str] | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> List[Tuple]:
    """Retorna lista [(id,nome,usuario,tipo,funcao,senha,data_nascimento)]."""

    sql = "SELECT id, nome, usuario, tipo, funcao, senha, data_nascimento FROM usuarios WHERE 1=1"
    params: list[str] = []

    if nome_like:
        sql += " AND nome LIKE ?"
        params.append(f"%{nome_like}%")
    if tipos:
        sql += f" AND tipo IN ({','.join('?' * len(tipos))})"
        params.extend(tipos)
    sql += " ORDER BY nome"

    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
        if offset is not None:
            sql += " OFFSET ?"
            params.append(offset)

    try:
        with db.obter_conexao() as conn:
            cur = conn.cursor()
            return cur.execute(sql, params).fetchall()
    except Exception as e:
        logger.error("Erro ao listar usuários: %s", e)
        return []


def buscar_usuario_por_id(usuario_id: int) -> Optional[Tuple]:
    try:
        with db.obter_conexao() as conn:
            cur = conn.cursor()
            return cur.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    except Exception as e:
        logger.error("Erro buscar usuário: %s", e)
        return None


def atualizar_usuario(
    usuario_id: int,
    nome: str,
    data_nascimento: str,
    funcao: str,
    usuario: str,
    senha: str,
    tipo: str,
) -> bool:
    try:
        with db.obter_conexao() as conn:
            cur = conn.cursor()
            if cur.execute(
                "SELECT 1 FROM usuarios WHERE usuario = ? AND id != ?",
                (usuario, usuario_id),
            ).fetchone():
                logger.warning("Login já existe: %s", usuario)
                return False

            cur.execute(
                """
                UPDATE usuarios
                SET nome=?, data_nascimento=?, funcao=?, usuario=?, senha=?, tipo=?
                WHERE id=?
                """,
                (nome, data_nascimento, funcao, usuario, senha, tipo, usuario_id),
            )
            db.marca_sujo()
            return _sync_after_write(conn)
    except Exception as e:
        logger.error("Erro atualizar usuário: %s", e)
        return False


def deletar_usuario(usuario_id: int) -> bool:
    try:
        with db.obter_conexao() as conn:
            conn.execute("DELETE FROM usuarios WHERE id=?", (usuario_id,))
            db.marca_sujo()
            return _sync_after_write(conn)
    except Exception as e:
        logger.error("Erro deletar usuário: %s", e)
        return False


def autenticar_usuario(usuario: str, senha: str) -> Optional[Tuple]:
    try:
        with db.obter_conexao() as conn:
            cur = conn.cursor()
            return cur.execute(
                "SELECT id, nome, tipo FROM usuarios WHERE usuario=? AND senha=?",
                (usuario, senha),
            ).fetchone()
    except Exception as e:
        logger.error("Erro autenticar usuário: %s", e)
        return None
