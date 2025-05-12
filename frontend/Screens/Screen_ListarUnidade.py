# frontend/Screens/Screen_ListarUnidade.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys

# Importa models
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_unidade

def exibir_tela_listar_unidades():
    # Estilização e proteção
    aplicar_estilo_geral()

    if st.session_state.get("tipo") != "admin":
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    st.title("🏗️ Lista de Unidades")

    unidades = model_unidade.listar_unidades()

    if not unidades:
        st.info("Nenhuma unidade cadastrada.")
    else:
        for u in unidades:
            with st.expander(f"🏢 {u[2]} - {u[0]}"):
                st.markdown(f"**Contrato:** {u[1]}")
                st.markdown(f"**Estado:** {u[3]}")
                st.markdown(f"**Cidade:** {u[4]}")
                st.markdown(f"**Localização:** {u[5]}")

                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✏️ Editar", key=f"edit_{u[0]}"):
                        st.session_state["editando_unidade"] = u
                        st.rerun()
                with col2:
                    if st.button("🗑 Excluir", key=f"del_{u[0]}"):
                        model_unidade.deletar_unidade(u[0])
                        st.success("Unidade excluída com sucesso! A pasta no Drive permanece intacta.")
                        st.rerun()

    # Formulário de edição
    if st.session_state.get("editando_unidade"):
        st.markdown("---")
        st.subheader("✏️ Editar Unidade")

        u = st.session_state["editando_unidade"]

        with st.form("form_edita_unidade"):
            nome_unidade = st.text_input("Nome da Unidade", value=u[2])
            estado = st.text_input("Estado", value=u[3])
            cidade = st.text_input("Cidade", value=u[4])
            localizacao = st.text_input("Localização", value=u[5])

            enviado = st.form_submit_button("Salvar alterações")

            if enviado:
                sucesso = model_unidade.atualizar_unidade(
                    cod_unidade=u[0],
                    numero_contrato=u[1],
                    nome_unidade=nome_unidade,
                    estado=estado,
                    cidade=cidade,
                    localizacao=localizacao
                )
                if sucesso:
                    st.success("Unidade atualizada com sucesso!")
                    st.session_state["editando_unidade"] = None
                    st.rerun()
                else:
                    st.error("Erro ao atualizar unidade.")
