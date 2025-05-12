# backend/Models/model_empresa.py

import sqlite3
from typing import List, Optional, Tuple
from pathlib import Path
import sys
import os
from tempfile import gettempdir

# Adiciona o caminho para importar banco e serviço do Drive
sys.path.append(str(Path(__file__).resolve().parents[1]))
from Database.db_gestaodecontratos import obter_conexao, salvar_banco_no_drive, DB_NAME
from Services import Service_googledrive as gdrive

# Pasta raiz do Drive para empresas (criada manualmente ou previamente)
from dotenv import load_dotenv
load_dotenv()
GDRIVE_EMPRESAS_FOLDER_ID = os.getenv("GDRIVE_EMPRESAS_FOLDER_ID")

# ───────────────── CRUD de Empresas com Drive ─────────────────

def criar_empresa(nome: str, cnpj: str, cod_empresa: str) -> bool:
    try:
        conn = obter_conexao()
        cursor = conn.cursor()

        # Cria a pasta no Drive
        if not GDRIVE_EMPRESAS_FOLDER_ID:
            print("⚠️ GDRIVE_EMPRESAS_FOLDER_ID não definida no .env.")
            return False

        pasta_empresa_id = gdrive.ensure_folder(nome, GDRIVE_EMPRESAS_FOLDER_ID)
        if not pasta_empresa_id:
            print("❌ Erro ao criar pasta da empresa no Drive")
            return False

        # Salva no banco de dados
        cursor.execute("""
            INSERT INTO empresas (nome, cnpj, cod_empresa, pasta_empresa)
            VALUES (?, ?, ?, ?)
        """, (nome, cnpj, cod_empresa, pasta_empresa_id))
        conn.commit()

        caminho_banco = Path(gettempdir()) / DB_NAME
        salvar_banco_no_drive(caminho_banco)
        conn.close()
        return True

    except Exception as e:
        print("Erro ao criar empresa:", e)
        return False


def listar_empresas() -> List[Tuple]:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome, cnpj, cod_empresa FROM empresas")
            return cursor.fetchall()
    except Exception as e:
        print(f"❌ Erro ao listar empresas: {e}")
        return []


def buscar_empresa_por_id(emp_id: int) -> Optional[Tuple]:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM empresas WHERE id = ?", (emp_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"❌ Erro ao buscar empresa: {e}")
        return None


def atualizar_empresa(emp_id: int, nome: str, cnpj: str, cod_empresa: str) -> bool:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE empresas
                SET nome = ?, cnpj = ?, cod_empresa = ?
                WHERE id = ?
            """, (nome, cnpj, cod_empresa, emp_id))
            
            caminho_banco = Path(gettempdir()) / DB_NAME
            salvar_banco_no_drive(caminho_banco)
            return True

    except Exception as e:
        print(f"❌ Erro ao atualizar empresa: {e}")
        return False


def deletar_empresa(emp_id: int) -> bool:
    try:
        with obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM empresas WHERE id = ?", (emp_id,))
            
            caminho_banco = Path(gettempdir()) / DB_NAME
            salvar_banco_no_drive(caminho_banco)
            return True
    except Exception as e:
        print(f"❌ Erro ao deletar empresa: {e}")
        return False
