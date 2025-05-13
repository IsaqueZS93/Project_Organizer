# backend/Models/model_usuario.py

import sqlite3
from typing import List, Optional, Tuple
from pathlib import Path
import sys
import logging

# Adiciona o caminho para importar o gerenciador do banco
sys.path.append(str(Path(__file__).resolve().parents[1]))
from Database.db_gestaodecontratos import obter_conexao, salvar_banco_no_drive, DB_NAME

from tempfile import gettempdir

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ───────────────── Funções CRUD para a tabela de usuários ─────────────────

def criar_usuario(nome: str, data_nascimento: str, funcao: str, usuario: str, senha: str, tipo: str) -> bool:
    try:
        # Primeiro verifica se o usuário já existe
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", (usuario,))
            if cursor.fetchone():
                logger.warning(f"Tentativa de criar usuário duplicado: {usuario}")
                return False

            # Se não existe, cria o novo usuário
            cursor.execute("""
                INSERT INTO usuarios (nome, data_nascimento, funcao, usuario, senha, tipo)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nome, data_nascimento, funcao, usuario, senha, tipo))
            
            # Força o commit
            conn.commit()
            
            # Salva no Drive
            caminho_banco = Path(gettempdir()) / DB_NAME
            try:
                salvar_banco_no_drive(caminho_banco)
                logger.info(f"Usuário {usuario} criado com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao salvar banco no Drive: {e}")
                # Mesmo com erro no Drive, o usuário foi criado localmente
                return True
                
    except Exception as e:
        logger.error(f"Erro ao criar usuário: {e}")
        return False


def listar_usuarios() -> List[Tuple]:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome, usuario, tipo, funcao FROM usuarios")
            return cursor.fetchall()
    except Exception as e:
        print(f"❌ Erro ao listar usuários: {e}")
        return []


def buscar_usuario_por_id(usuario_id: int) -> Optional[Tuple]:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"❌ Erro ao buscar usuário: {e}")
        return None


def atualizar_usuario(usuario_id: int, nome: str, data_nascimento: str, funcao: str, usuario: str, senha: str, tipo: str) -> bool:
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE usuarios
            SET nome = ?, data_nascimento = ?, funcao = ?, usuario = ?, senha = ?, tipo = ?
            WHERE id = ?
        """, (nome, data_nascimento, funcao, usuario, senha, tipo, usuario_id))
        conn.commit()

        caminho_banco = Path(gettempdir()) / DB_NAME
        salvar_banco_no_drive(caminho_banco)
        conn.close()

        return True
    except Exception as e:
        print("Erro ao atualizar usuário:", e)
        return False


def deletar_usuario(usuario_id: int) -> bool:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))

            caminho_banco = Path(gettempdir()) / DB_NAME
            salvar_banco_no_drive(caminho_banco)
            return True
    except Exception as e:
        print(f"❌ Erro ao deletar usuário: {e}")
        return False


def autenticar_usuario(usuario: str, senha: str) -> Optional[Tuple]:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, nome, tipo FROM usuarios
                WHERE usuario = ? AND senha = ?
            """, (usuario, senha))
            return cursor.fetchone()
    except Exception as e:
        print(f"❌ Erro ao autenticar usuário: {e}")
        return None
