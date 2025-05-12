# frontend/Screens/Screen_ListarEmpresa.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys

# Importa model
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_empresa

def exibir_tela_listar_empresas():
    # Aplica estilo visual
    aplicar_estilo_geral()

    # Proteção de acesso
    if st.session_state.get("tipo") != "admin":
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    st.title("🏢 Lista de Empresas")

    empresas = model_empresa.listar_empresas()

    if not empresas:
        st.info("Nenhuma empresa cadastrada.")
    else:
        for emp in empresas:
            with st.expander(f"🏢 {emp[1]} (Cód: {emp[3]})"):
                st.markdown(f"**CNPJ:** {emp[2]}")

                col1, col2 = st.columns([1, 1])

                with col1:
                    if st.button("✏️ Editar", key=f"edit_{emp[0]}"):
                        st.session_state["editando_empresa"] = emp
                        st.rerun()

                with col2:
                    if st.button("❌ Excluir", key=f"excluir_{emp[0]}"):
                        if model_empresa.deletar_empresa(emp[0]):
                            st.success("✅ Empresa excluída com sucesso!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao excluir empresa")

    # Formulário de edição
    if st.session_state.get("editando_empresa"):
        st.markdown("---")
        st.subheader("✏️ Editar Empresa")

        emp = st.session_state["editando_empresa"]

        with st.form("form_edicao_empresa"):
            nome = st.text_input("Nome da Empresa", value=emp[1])
            cnpj = st.text_input("CNPJ", value=emp[2])
            cod = st.text_input("Código da Empresa", value=emp[3])

            enviado = st.form_submit_button("Salvar alterações")

            if enviado:
                sucesso = model_empresa.atualizar_empresa(
                    id_empresa=emp[0],
                    nome=nome,
                    cnpj=cnpj,
                    cod_empresa=cod
                )
                if sucesso:
                    st.success("Empresa atualizada com sucesso!")
                    st.session_state["editando_empresa"] = None
                    st.rerun()
                else:
                    st.error("Erro ao atualizar a empresa.")
