# frontend/Screens/Screen_CadastroEmpresa.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys

# Importa model e drive
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_empresa
from Services import Service_googledrive as gdrive

def exibir_tela_cadastro_empresa():
    # Estilização e segurança
    aplicar_estilo_geral()

    if st.session_state.get("tipo") != "admin":
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    st.title("🏢 Cadastro de Empresa")
    st.markdown("Insira os dados da empresa contratada.")

    with st.form("form_empresa"):
        nome = st.text_input("Nome da Empresa")
        cnpj = st.text_input("CNPJ")
        cod_empresa = st.text_input("Código da Empresa (único)")

        enviado = st.form_submit_button("Cadastrar")

        if enviado:
            if not nome or not cnpj or not cod_empresa:
                st.warning("Preencha todos os campos obrigatórios.")
            else:
                sucesso = model_empresa.criar_empresa(nome=nome, cnpj=cnpj, cod_empresa=cod_empresa)

                if sucesso:
                    # Cria pasta no Google Drive
                    pasta_id = gdrive.ensure_folder(nome)
                    st.success(f"Empresa cadastrada e pasta '{nome}' criada no Drive!")
                else:
                    st.error("Erro ao cadastrar empresa. Verifique se o CNPJ ou código já está em uso.")
