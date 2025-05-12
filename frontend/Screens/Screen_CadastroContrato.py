# frontend/Screens/Screen_CadastroContrato.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys

# Importa model e Google Drive
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_contrato, model_empresa
from Services import Service_googledrive as gdrive

def exibir_tela_cadastro_contrato():
    # Aplica estilo visual
    aplicar_estilo_geral()

    # Restrito a admin
    if st.session_state.get("tipo") != "admin":
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    st.title("📑 Cadastro de Contrato")
    st.markdown("Insira os dados do contrato e selecione a empresa vinculada.")

    # Lista de empresas cadastradas
    empresas = model_empresa.listar_empresas()
    nomes_empresas = [f"{e[1]} ({e[3]})" for e in empresas]

    if not empresas:
        st.warning("Cadastre uma empresa antes de criar um contrato.")
        st.stop()

    with st.form("form_contrato", clear_on_submit=True):
        empresa_escolhida = st.selectbox("Empresa", nomes_empresas)
        empresa_obj = empresas[nomes_empresas.index(empresa_escolhida)]

        numero_contrato = st.text_input("Número do Contrato")
        titulo = st.text_input("Título do Contrato")
        especificacoes = st.text_area("Especificações")

        enviado = st.form_submit_button("Cadastrar")

        if enviado:
            cod_empresa = empresa_obj[3]
            nome_empresa = empresa_obj[1]

            sucesso = model_contrato.criar_contrato(
                numero_contrato=numero_contrato,
                cod_empresa=cod_empresa,
                empresa_contratada=nome_empresa,
                titulo=titulo,
                especificacoes=especificacoes
            )

            if sucesso:
                st.success("Contrato cadastrado e pasta criada no Google Drive!")
            else:
                st.error("Erro ao cadastrar contrato. Verifique se o número já está em uso.")
