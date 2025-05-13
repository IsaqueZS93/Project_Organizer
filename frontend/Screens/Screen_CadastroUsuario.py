# frontend/Screens/Screen_CadastroUsuario.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys
from frontend.Utils.auth import verificar_permissao_admin
import datetime

# Importa model de usuário
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_usuario

def exibir_tela_cadastro_usuario():
    """Exibe a tela de cadastro de usuário"""
    # Aplica estilo visual
    aplicar_estilo_geral()

    # Verifica permissão de administrador
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()
        
    # ──── Título e layout ────
    st.title("👤 Cadastro de Usuário")
    st.markdown("Cadastre um novo usuário no sistema.")

    # ──── Formulário ────
    with st.form("form_usuario"):
        nome = st.text_input("Nome completo")
        
        # Data de nascimento com range amplo
        min_date = datetime.date(1900, 1, 1)
        max_date = datetime.date.today()
        nascimento = st.date_input(
            "Data de nascimento",
            min_value=min_date,
            max_value=max_date,
            value=datetime.date(1990, 1, 1)
        )
        
        funcao = st.text_input("Função")
        usuario = st.text_input("Nome de usuário")
        senha = st.text_input("Senha", type="password")
        tipo = st.selectbox("Tipo de usuário", ["admin", "ope"])

        enviado = st.form_submit_button("Cadastrar")

        if enviado:
            if not nome or not usuario or not senha:
                st.warning("Preencha todos os campos obrigatórios.")
            else:
                sucesso = model_usuario.criar_usuario(
                    nome=nome,
                    data_nascimento=str(nascimento),
                    funcao=funcao,
                    usuario=usuario,
                    senha=senha,
                    tipo=tipo
                )
                if sucesso:
                    st.success("Usuário cadastrado com sucesso!")
                else:
                    st.error("Erro ao cadastrar usuário. Verifique se o nome de usuário já existe.")
