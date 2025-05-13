# frontend/Screens/Screen_Login.py

import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from backend.Database.db_gestaodecontratos import autenticar_usuario
from backend.Services.Service_googledrive import get_service

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carrega variáveis do .env
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

# Constantes para credenciais padrão
ADMIN_USER = os.getenv("DEFAULT_ADMIN_USER", "Isaque.Z")
ADMIN_PASS = os.getenv("DEFAULT_ADMIN_PASS", "071959")

def validar_credenciais_admin(usuario: str, senha: str) -> bool:
    """Valida credenciais do administrador padrão"""
    logger.info(f"Validando credenciais admin - Usuário: {usuario}")
    logger.info(f"ADMIN_USER configurado: {ADMIN_USER}")
    return usuario == ADMIN_USER and senha == ADMIN_PASS

def login():
    """Exibe a tela de login e gerencia a autenticação"""
    if 'autenticado' in st.session_state and st.session_state.autenticado:
        logger.info(f"Usuário já autenticado: {st.session_state.usuario} (Tipo: {st.session_state.tipo_usuario})")
        return

    # Container principal centralizado
    with st.container():
        # Logo e título
        st.markdown("""
            <div style='text-align: center; margin-bottom: 3rem;'>
                <h1 style='color: #1E88E5; font-size: 2.5rem; margin-bottom: 0.5rem;'>Gestão de Contratos</h1>
                <p style='color: #666; font-size: 1.1rem;'>Sistema de Gerenciamento de Contratos e Serviços</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Container do formulário com estilo moderno
        with st.container():
            st.markdown("""
                <div style='
                    background-color: white;
                    padding: 2.5rem;
                    border-radius: 15px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    max-width: 500px;
                    margin: 0 auto;
                '>
            """, unsafe_allow_html=True)
            
            # Campos de login com estilo personalizado
            st.markdown("""
                <style>
                    .stTextInput > div > div > input {
                        padding: 0.75rem;
                        border-radius: 8px;
                        border: 1px solid #ddd;
                        font-size: 1rem;
                    }
                    .stButton > button {
                        width: 100%;
                        padding: 0.75rem;
                        border-radius: 8px;
                        background-color: #1E88E5;
                        color: white;
                        font-weight: 500;
                        font-size: 1rem;
                        border: none;
                        margin-top: 1rem;
                    }
                    .stButton > button:hover {
                        background-color: #1976D2;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            usuario = st.text_input("👤 Usuário", key="login_usuario")
            senha = st.text_input("🔒 Senha", type="password", key="login_senha")
            
            if st.button("Entrar", use_container_width=True):
                if not usuario or not senha:
                    st.error("Por favor, preencha todos os campos")
                    return
                    
                logger.info(f"Tentativa de login para usuário: {usuario}")
                
                # Primeiro tenta autenticar como admin
                if validar_credenciais_admin(usuario, senha):
                    logger.info("Login como administrador bem-sucedido")
                    st.session_state.autenticado = True
                    st.session_state.usuario = usuario
                    st.session_state.tipo_usuario = "admin"
                    st.session_state.nome = "Administrador"
                    logger.info(f"Variáveis de sessão configuradas - Usuário: {usuario}, Tipo: admin")
                    st.rerun()
                    return
                
                # Se não for admin, tenta autenticar no banco
                sucesso, tipo, nome = autenticar_usuario(usuario, senha)
                
                if sucesso:
                    logger.info(f"Login bem-sucedido via banco de dados. Tipo: {tipo}")
                    st.session_state.autenticado = True
                    st.session_state.usuario = usuario
                    st.session_state.tipo_usuario = tipo
                    st.session_state.nome = nome
                    logger.info(f"Variáveis de sessão configuradas - Usuário: {usuario}, Tipo: {tipo}")
                    st.rerun()
                else:
                    logger.warning(f"Falha no login: {nome}")
                    st.error(nome)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Adiciona os direitos reservados
            st.markdown("""
                <div style='
                    text-align: center;
                    margin-top: 2rem;
                    padding: 1rem;
                    color: #666;
                    font-size: 0.9rem;
                '>
                    <p>© 2024 Novaes Engenharia. Todos os direitos reservados.</p>
                    <p style='font-size: 0.8rem; margin-top: 0.5rem;'>Desenvolvido com ❤️ pela equipe de TI</p>
                </div>
            """, unsafe_allow_html=True)

def logout():
    """Realiza o logout do usuário"""
    logger.info("Realizando logout")
    # Limpa todas as variáveis de sessão
    for key in list(st.session_state.keys()):
        logger.info(f"Removendo variável de sessão: {key}")
        del st.session_state[key]
    st.rerun()
