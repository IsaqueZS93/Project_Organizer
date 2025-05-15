# frontend/Screens/Screen_ListarUnidade.py
# -----------------------------------------------------------------------------
#  Lista de Unidades (Streamlit)
#  • Lazy‑load + filtro por contrato (radio) "Nº – Empresa"
#  • Admin somente
# -----------------------------------------------------------------------------

from __future__ import annotations

import streamlit as st

from Styles.theme import aplicar_estilo_geral
from frontend.Utils.auth import verificar_permissao_admin
from Models import model_unidade

# -----------------------------------------------------------------------------
# Tela principal
# -----------------------------------------------------------------------------

def exibir_tela_listar_unidades() -> None:
    aplicar_estilo_geral()

    # ---- proteção ---------------------------------------------------------
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    st.title("🏗️ Lista de Unidades")

    # ---- botão inicial ----------------------------------------------------
    if "mostrar_unidades" not in st.session_state:
        if st.button("🔍 Mostrar unidades", type="primary"):
            st.session_state["mostrar_unidades"] = True
            st.session_state["filtro_contrato_val"] = "Todos"
        else:
            st.info("Clique em **Mostrar unidades** para carregar a lista.")
            return

    # ---- carrega todas para montar filtro ---------------------------------
    todas = model_unidade.listar_unidades()
    if not todas:
        st.info("Nenhuma unidade cadastrada.")
        return

    contratos = sorted({u[1] for u in todas})
    radio_vals = ["Todos"] + contratos
    radio_labels = ["Todos"] + [
        f"{num} – {model_unidade.obter_nome_empresa_por_contrato(num) or '?'}"
        for num in contratos
    ]

    # ---- radio filtro -----------------------------------------------------
    with st.container():
        st.markdown("### Filtro por contrato")
        idx = st.radio(
            label="",  # vazio, escondemos label
            options=list(range(len(radio_vals))),
            format_func=lambda i: radio_labels[i],
            horizontal=True,
            key="rad_contrato",
            label_visibility="collapsed",
        )
        contrato_sel = radio_vals[idx]
        st.session_state["filtro_contrato_val"] = contrato_sel

    # ---- obtém lista conforme filtro --------------------------------------
    unidades = todas if contrato_sel == "Todos" else model_unidade.listar_unidades(contrato_sel)

    if not unidades:
        st.info("Nenhuma unidade encontrada para este contrato.")
        return

    # ---- renderização -----------------------------------------------------
    for cod, contrato, nome, estado, cidade, local in unidades:
        with st.expander(f"🏢 {nome} – {cod}"):
            st.markdown(f"**Contrato:** {contrato}")
            st.markdown(f"**Estado:** {estado}")
            st.markdown(f"**Cidade:** {cidade}")
            st.markdown(f"**Localização:** {local}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✏️ Editar", key=f"edit_{cod}"):
                    st.session_state["editando_unidade"] = (cod, contrato, nome, estado, cidade, local)
                    st.rerun()
            with col2:
                if st.button("🗑 Excluir", key=f"del_{cod}"):
                    ok = model_unidade.deletar_unidade(cod)
                    if ok:
                        st.success("Unidade excluída com sucesso! A pasta no Drive permanece intacta.")
                    st.rerun()

    # ---- edição -----------------------------------------------------------
    if "editando_unidade" in st.session_state:
        cod, contrato, nome_cur, est_cur, cid_cur, loc_cur = st.session_state["editando_unidade"]
        st.markdown("---")
        st.subheader("✏️ Editar Unidade")

        with st.form("form_edit_unid"):
            nome_edit = st.text_input("Nome da Unidade", value=nome_cur)
            estado_edit = st.text_input("Estado", value=est_cur)
            cidade_edit = st.text_input("Cidade", value=cid_cur)
            local_edit = st.text_input("Localização", value=loc_cur)
            if st.form_submit_button("Salvar alterações"):
                ok = model_unidade.atualizar_unidade(
                    cod_unidade=cod,
                    numero_contrato=contrato,
                    nome_unidade=nome_edit,
                    estado=estado_edit,
                    cidade=cidade_edit,
                    localizacao=local_edit,
                )
                if ok:
                    st.success("Unidade atualizada com sucesso!")
                    st.session_state.pop("editando_unidade")
                    st.rerun()
                else:
                    st.error("Erro ao atualizar unidade.")
