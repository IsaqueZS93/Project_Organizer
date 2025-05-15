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

    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    st.title("🏗️ Lista de Unidades")

    # ---------- Botão inicial ----------------------------------------------
    if "mostrar_unidades" not in st.session_state:
        if st.button("🔍 Mostrar unidades", type="primary"):
            st.session_state["mostrar_unidades"] = True
            st.session_state["filtro_contrato_val"] = "Todos"
        else:
            st.info("Clique em **Mostrar unidades** para carregar a lista.")
            return

    # ---------- Pré‑carrega todas para montar filtro -----------------------
    todas_unidades = model_unidade.listar_unidades()
    if not todas_unidades:
        st.info("Nenhuma unidade cadastrada.")
        return

    contratos_unicos = sorted({u[1] for u in todas_unidades})
    # cria rótulos "Nº – Empresa"
    opcoes_radio: dict[str, str] = {"Todos": "Todos"}
    for num in contratos_unicos:
        empresa = model_unidade.obter_nome_empresa_por_contrato(num) or "?"
        opcoes_radio[num] = f"{num} – {empresa}"

    # exibe radio em coluna larga para layout melhor
    with st.container():
        st.markdown("### Filtro de contrato")
        contrato_escolhido = st.radio(
            label="Selecione o contrato",
            options=list(opcoes_radio.keys()),
            format_func=lambda k: opcoes_radio[k],
            horizontal=True,
            key="rad_contrato",
        )
        st.session_state["filtro_contrato_val"] = contrato_escolhido

    # ---------- Lista conforme filtro --------------------------------------
    if contrato_escolhido == "Todos":
        unidades = todas_unidades
    else:
        unidades = model_unidade.listar_unidades(numero_contrato=contrato_escolhido)

    if not unidades:
        st.info("Nenhuma unidade encontrada para este contrato.")
        return

    # ---------- Renderização ----------------------------------------------
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

    # ---------- Formulário de edição ---------------------------------------
    if "editando_unidade" in st.session_state:
        cod, contrato, nome_cur, est_cur, cid_cur, loc_cur = st.session_state["editando_unidade"]
        st.markdown("---")
        st.subheader("✏️ Editar Unidade")

        with st.form("form_edit_unid"):
            nome_edit = st.text_input("Nome da Unidade", value=nome_cur)
            estado_edit = st.text_input("Estado", value=est_cur)
            cidade_edit = st.text_input("Cidade", value=cid_cur)
            local_edit = st.text_input("Localização", value=loc_cur)
            enviar = st.form_submit_button("Salvar alterações")

        if enviar:
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
