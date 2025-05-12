# frontend/Screens/Screen_ListarContrato.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys

# Importa models
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_contrato

def exibir_tela_listar_contratos():
    # Aplica o tema
    aplicar_estilo_geral()

    # Proteção admin
    if st.session_state.get("tipo") != "admin":
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    st.title("📑 Lista de Contratos")

    contratos = model_contrato.listar_contratos()

    if not contratos:
        st.info("Nenhum contrato cadastrado.")
    else:
        for c in contratos:
            with st.expander(f"📄 Contrato {c[0]} - {c[3]}"):
                st.markdown(f"**Empresa:** {c[2]}")
                st.markdown(f"**Título:** {c[3]}")
                st.markdown(f"**Especificações:**\n{c[4]}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Editar", key=f"edit_{c[0]}"):
                        st.session_state["editando_contrato"] = c
                        st.rerun()

                with col2:
                    if st.button("🗑 Excluir", key=f"del_{c[0]}"):
                        model_contrato.deletar_contrato(c[0])
                        st.success("Contrato excluído com sucesso! A pasta no Drive permanece intacta.")
                        st.rerun()

    # Formulário de edição
    if st.session_state.get("editando_contrato"):
        st.markdown("---")
        st.subheader("✏️ Editar Contrato")

        c = st.session_state["editando_contrato"]

        with st.form("form_edita_contrato"):
            titulo = st.text_input("Título", value=c[3])
            especificacoes = st.text_area("Especificações", value=c[4])

            enviado = st.form_submit_button("Salvar alterações")

            if enviado:
                sucesso = model_contrato.atualizar_contrato(
                    numero_contrato=c[0],
                    cod_empresa=c[1],
                    empresa_contratada=c[2],
                    titulo=titulo,
                    especificacoes=especificacoes
                )
                if sucesso:
                    st.success("Contrato atualizado com sucesso!")
                    st.session_state["editando_contrato"] = None
                    st.rerun()
                else:
                    st.error("Erro ao atualizar contrato.")
