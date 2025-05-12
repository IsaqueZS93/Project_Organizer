# frontend/Screens/Screen_Principal.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral

def exibir_tela_principal():
    # Aplica o estilo geral da interface
    aplicar_estilo_geral()

    # Inicializa session_state caso necessário
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "usuario" not in st.session_state:
        st.session_state.usuario = ""
    if "tipo" not in st.session_state:
        st.session_state.tipo = ""

    # Garante que apenas logados acessem a tela
    if not st.session_state.autenticado:
        st.warning("Por favor, faça login para acessar o sistema.")
        st.stop()

    # Título de boas-vindas
    st.title("📁 Sistema de Gestão de Contratos")
    st.markdown(f"Bem-vindo, **{st.session_state.usuario}**!")

    # Tutorial básico
    with st.expander("ℹ️ Como usar o sistema?"):
        st.markdown("""
        1. Utilize o menu lateral para acessar as funcionalidades disponíveis.
        2. Cadastre empresas, contratos, unidades e serviços conforme sua permissão.
        3. O sistema salvará automaticamente as alterações no Google Drive.
        4. Operadores podem visualizar e preencher serviços atribuídos a eles.
        """)

    st.info("Escolha uma opção no menu à esquerda para começar.")
