# frontend/Screens/Screen_Login.py

import streamlit as st
from dotenv import load_dotenv
import os
from pathlib import Path
import sys
import sqlite3
from Styles.theme import aplicar_estilo_geral
from Models import model_usuario
from Services import Service_googledrive as gdrive

# ────── Garante acesso aos módulos backend e estilos ──────
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))  # para backend
sys.path.append(str(ROOT / "frontend"))  # para Styles

from backend.Database.db_gestaodecontratos import obter_conexao

# ────── Carrega variáveis e aplica tema ──────
load_dotenv()
aplicar_estilo_geral()

ADMIN_USER = os.getenv("DEFAULT_ADMIN_USER", "Isaque.Z")
ADMIN_PASS = os.getenv("DEFAULT_ADMIN_PASS", "071959")


# ────── Função de login ──────
def autenticar_usuario(usuario: str, senha: str) -> tuple[bool, str]:
    # Primeiro tenta autenticar pelo .env (admin padrão)
    if usuario == ADMIN_USER and senha == ADMIN_PASS:
        return True, "admin"

    # Senão, consulta o banco de dados
    conn = obter_conexao()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tipo FROM usuarios
        WHERE usuario = ? AND senha = ?
    """, (usuario, senha))
    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        return True, resultado[0]  # tipo: admin ou ope
    return False, ""

# ────── Interface de login ──────
def exibir_login():
    # Aplica tema
    aplicar_estilo_geral()

    # Container centralizado para o login
    col1, col2, col3 = st.columns([1,2,1])
    
    with col2:


        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            # Título do formulário
            st.markdown("""
                <h2 style='text-align: center; color: #333; margin-bottom: 1.5rem;'>
                    <i class="fas fa-user-circle"></i> Login
                </h2>
            """, unsafe_allow_html=True)

            # Campos de login
            usuario = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
            senha = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")

            # Botão de login
            if st.button("🚀 Entrar", use_container_width=True):
                if usuario and senha:
                    # Verifica credenciais
                    ok, tipo = autenticar_usuario(usuario, senha)
                    if ok:
                        # Atualiza estado da sessão
                        st.session_state["autenticado"] = True
                        st.session_state["usuario"] = usuario
                        st.session_state["tipo"] = tipo
                        
                        # Força atualização da página
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha inválidos")
                else:
                    st.warning("⚠️ Por favor, preencha todos os campos")

            # Rodapé do formulário
            st.markdown("""
                <div style='text-align: center; margin-top: 1.5rem; color: #666; font-size: 0.9rem;'>
                    <p>© 2024 Novaes Engenharia. Todos os direitos reservados.</p>
                </div>
            """, unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        # Mensagem de ajuda
        st.markdown("""
            <div style='text-align: center; margin-top: 1rem; color: #666; font-size: 0.9rem;'>
                <p>Em caso de problemas, entre em contato com o administrador do sistema.</p>
            </div>
        """, unsafe_allow_html=True)

# ────── Controle de sessão ──────
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
