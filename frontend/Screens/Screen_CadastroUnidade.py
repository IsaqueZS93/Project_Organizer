# frontend/Screens/Screen_CadastroUnidade.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys
import datetime
from frontend.Utils.auth import verificar_permissao_admin

# Importa models e serviço do Google Drive
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_unidade, model_contrato
from Services import Service_googledrive as gdrive

def exibir_tela_cadastro_unidade():
    """Exibe a tela de cadastro de unidades"""
    # Aplica estilo visual
    aplicar_estilo_geral()

    # Verifica permissão de administrador
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    st.title("🏗️ Cadastro de Unidade")

    contratos = model_contrato.listar_contratos()

    if not contratos:
        st.warning("Cadastre um contrato antes de criar unidades.")
        st.stop()

    contrato_options = [f"{c[0]} - {c[2]}" for c in contratos]

    with st.form("form_unidade"):
        contrato_selecionado = st.selectbox("Contrato Vinculado", contrato_options)
        contrato = contratos[contrato_options.index(contrato_selecionado)]

        cod_unidade = st.text_input("Código da Unidade (único)")
        nome_unidade = st.text_input("Nome da Unidade")
        estado = st.text_input("Estado")
        cidade = st.text_input("Cidade")
        localizacao = st.text_input("Coordenadas (lat,long)")

        enviado = st.form_submit_button("Cadastrar")

        if enviado:
            if not cod_unidade or not nome_unidade:
                st.warning("Preencha todos os campos obrigatórios.")
            else:
                sucesso = model_unidade.criar_unidade(
                    cod_unidade=cod_unidade,
                    numero_contrato=contrato[0],
                    nome_unidade=nome_unidade,
                    estado=estado,
                    cidade=cidade,
                    localizacao=localizacao
                )

                if sucesso:
                    st.success("Unidade cadastrada e pasta criada no Drive com sucesso!")
                else:
                    st.error("Erro ao cadastrar unidade. Verifique se o código já está em uso.")
