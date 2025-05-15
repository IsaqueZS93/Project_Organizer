# frontend/Screens/Screen_ListarFuncionario.py
# -----------------------------------------------------------------------------
#  Lista de Funcionários (Streamlit)
#  • Lazy‑load sem filtros (apenas botão "Mostrar funcionários")
#  • Admin somente
#  • Evita chamadas ao banco até o usuário solicitar
# -----------------------------------------------------------------------------

from __future__ import annotations

import datetime
from typing import List, Tuple

import streamlit as st

from Styles.theme import aplicar_estilo_geral
from frontend.Utils.auth import verificar_permissao_admin
from Models import model_funcionario

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _carregar_funcionarios() -> List[Tuple]:
    """Busca todos os funcionários, ordenados por nome."""
    return model_funcionario.listar_funcionarios()

# -----------------------------------------------------------------------------
# Tela principal
# -----------------------------------------------------------------------------

def exibir_tela_listar_funcionarios() -> None:
    aplicar_estilo_geral()

    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    st.title("📋 Lista de Funcionários")

    # ── Botão inicial ---------------------------------------------------------
    if "mostrar_funcionarios" not in st.session_state:
        if st.button("🔍 Mostrar funcionários", type="primary"):
            st.session_state["mostrar_funcionarios"] = True
        else:
            st.info("Clique em **Mostrar funcionários** para carregar a lista.")
            return

    # ── Carrega dados ---------------------------------------------------------
    funcionarios = _carregar_funcionarios()

    if not funcionarios:
        st.info("Nenhum funcionário cadastrado.")
        return

    # ── Renderização ----------------------------------------------------------
    for f in funcionarios:
        # (cod_func, nome, cpf, data_nasc, funcao, id)
        cod, nome, cpf, nasc, funcao, fid = f
        with st.expander(f"👷 {nome} - {funcao or '—'}"):
            st.markdown(f"**Nascimento:** {nasc or '—'}")
            st.markdown(f"**CPF:** {cpf}")
            st.markdown(f"**Código:** {cod}")
            st.markdown(f"**Função:** {funcao or '—'}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✏️ Editar", key=f"edit_{cod}"):
                    st.session_state["editando_funcionario"] = f
                    st.rerun()
            with col2:
                if st.button("🗑 Excluir", key=f"del_{cod}"):
                    ok = model_funcionario.deletar_funcionario(cod)
                    if ok:
                        st.success("Funcionário excluído com sucesso!")
                    else:
                        st.warning("Não foi possível excluir (pode estar vinculado a serviços).")
                    st.rerun()

    # ── Formulário de edição ---------------------------------------------------
    if "editando_funcionario" in st.session_state:
        st.markdown("---")
        st.subheader("✏️ Editar Funcionário")

        cod, nome_cur, cpf_cur, nasc_cur, funcao_cur, _fid = st.session_state["editando_funcionario"]
        nasc_date = (
            datetime.datetime.strptime(nasc_cur, "%Y-%m-%d").date() if nasc_cur else datetime.date(1990, 1, 1)
        )

        with st.form("form_edit_func"):
            nome_edit = st.text_input("Nome completo", value=nome_cur)
            nasc_edit = st.date_input(
                "Data de nascimento",
                value=nasc_date,
                min_value=datetime.date(1900, 1, 1),
                max_value=datetime.date.today(),
            )
            cpf_edit = st.text_input("CPF", value=cpf_cur)
            st.text_input("Código do Funcionário", value=cod, disabled=True)
            funcao_edit = st.text_input("Função", value=funcao_cur or "")

            enviar = st.form_submit_button("Salvar alterações")

        if enviar:
            nasc_str = nasc_edit.strftime("%Y-%m-%d")
            sucesso = model_funcionario.atualizar_funcionario(
                cod_funcionario_original=cod,
                novo_nome=nome_edit,
                nova_data_nascimento=nasc_str,
                novo_cpf=cpf_edit,
                nova_funcao=funcao_edit,
            )
            if sucesso:
                st.success("Funcionário atualizado com sucesso!")
                st.session_state.pop("editando_funcionario")
                st.rerun()
            else:
                st.error("Erro ao atualizar funcionário.")
