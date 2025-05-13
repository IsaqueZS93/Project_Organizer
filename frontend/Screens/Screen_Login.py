# frontend/Screens/Screen_Login.py

import streamlit as st
from pathlib import Path
import sys
import os
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importa models
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_usuario

def login():
    """Realiza o login do usuário"""
    # Verifica se já está autenticado
    if "autenticado" in st.session_state and st.session_state["autenticado"]:
        return

    # Título
    st.title("🔐 Login")

    # Formulário de login
    with st.form("form_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        enviado = st.form_submit_button("Entrar")

        if enviado:
            # Tenta login como admin primeiro
            admin_user = os.getenv("DEFAULT_ADMIN_USER")
            admin_pass = os.getenv("DEFAULT_ADMIN_PASS")
            
            if admin_user and admin_pass and usuario == admin_user and senha == admin_pass:
                st.session_state["autenticado"] = True
                st.session_state["usuario"] = usuario
                st.session_state["tipo"] = "admin"
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                # Se não for admin, tenta login normal
                if model_usuario.verificar_login(usuario, senha):
                    st.session_state["autenticado"] = True
                    st.session_state["usuario"] = usuario
                    st.session_state["tipo"] = model_usuario.obter_tipo_usuario(usuario)
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos!")

def logout():
    """Realiza o logout do usuário"""
    logger.info("Realizando logout")
    # Limpa todas as variáveis de sessão
    for key in list(st.session_state.keys()):
        logger.info(f"Removendo variável de sessão: {key}")
        del st.session_state[key]
    st.rerun()
