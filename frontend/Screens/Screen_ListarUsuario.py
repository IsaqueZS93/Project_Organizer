# frontend/Screens/Screen_ListarUsuario.py
# ------------------------------------------------------------------------------
#  Lista de Usuários (Streamlit)
#  • Carregamento sob demanda + filtros (nome / tipo)
#  • Sem sys.path hacks; import direto
#  • Permissões: admin pode tudo, usuário comum edita apenas o próprio registro
#  • Usa st.query_params? → adiado p/ futura paginação; mantém sessão interna
# ------------------------------------------------------------------------------

from __future__ import annotations

import datetime
from typing import List, Tuple

import streamlit as st

from Styles.theme import aplicar_estilo_geral
from frontend.Utils.auth import verificar_permissao_admin
from Models import model_usuario

# ------------------------------------------------------------------------------
# 1. Helpers -------------------------------------------------------------------
# ------------------------------------------------------------------------------

def _pode_editar(user_login: str) -> bool:
    """Admin pode editar tudo; caso contrário, apenas seu próprio usuário."""
    return (
        st.session_state.get("tipo") == "admin"
        or user_login == st.session_state.get("usuario")
    )


def _carregar_usuarios(nome_filtro: str | None, tipos: List[str] | None) -> List[Tuple]:
    """Wrapper para model_usuario.listar_usuarios() com filtros opcionais."""
    return model_usuario.listar_usuarios(nome_like=nome_filtro, tipos=tipos)

# ------------------------------------------------------------------------------
# 2. Tela principal ------------------------------------------------------------
# ------------------------------------------------------------------------------

def exibir_tela_listar_usuarios() -> None:
    aplicar_estilo_geral()

    # ---------- Permissão -----------------------------------------------------
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    st.title("📋 Lista de Usuários")

    # ---------- Filtros de busca ---------------------------------------------
    with st.expander("🔎 Filtros de busca", expanded=False):
        filtro_nome = st.text_input("Por nome contém", key="flt_nome")
        filtro_tipo = st.multiselect("Tipo", ["admin", "ope"], key="flt_tipo")
        if st.button("Aplicar filtros", key="btn_filtros"):
            st.session_state["mostrar_usuarios"] = True
            st.session_state["filtro_nome_val"] = filtro_nome
            st.session_state["filtro_tipo_val"] = filtro_tipo

    # ---------- Botão inicial -------------------------------------------------
    if "mostrar_usuarios" not in st.session_state:
        if st.button("🔍 Mostrar usuários", type="primary"):
            st.session_state["mostrar_usuarios"] = True
            st.session_state["filtro_nome_val"] = ""
            st.session_state["filtro_tipo_val"] = []
        else:
            st.info("Clique em **Mostrar usuários** para carregar a lista.")
            return

    # ---------- Carrega dados -------------------------------------------------
    usuarios = _carregar_usuarios(
        st.session_state.get("filtro_nome_val"),
        st.session_state.get("filtro_tipo_val"),
    )

    if not usuarios:
        st.info("Nenhum usuário encontrado com esses critérios.")
        return

    # ---------- Renderização --------------------------------------------------
    for u in usuarios:
        # Estrutura esperada: (id, nome, usuario, tipo, funcao, senha, data_nasc)
        user_id, nome, login, tipo_u, funcao, senha, *_ = u
        with st.expander(f"👤 {nome} ({tipo_u})"):
            st.markdown(f"**Função:** {funcao or '—'}")
            st.markdown(f"**Usuário:** {login}")
            st.markdown(f"**Tipo:** {tipo_u}")

            if _pode_editar(login):
                st.markdown(f"**Senha:** {senha}")

            col1, col2 = st.columns(2)

            if _pode_editar(login):
                with col1:
                    if st.button("✏️ Editar", key=f"edit_{user_id}"):
                        st.session_state["editando_usuario"] = u
                        st.rerun()

            if st.session_state.get("tipo") == "admin":
                with col2:
                    if st.button("🗑 Excluir", key=f"del_{user_id}"):
                        model_usuario.deletar_usuario(user_id)
                        st.success("Usuário excluído com sucesso!")
                        st.rerun()

    # ---------- Edição --------------------------------------------------------
    if "editando_usuario" in st.session_state:
        st.markdown("---")
        st.subheader("✏️ Editar Usuário")

        usuario = st.session_state["editando_usuario"]
        (
            user_id,
            nome_atual,
            login_atual,
            tipo_atual,
            funcao_atual,
            senha_atual,
            data_nasc_atual,
        ) = usuario

        # Permissão final (caso o usuário perca status no meio do caminho)
        if not _pode_editar(login_atual):
            st.error("Você não tem permissão para editar este usuário.")
            st.session_state.pop("editando_usuario")
            st.rerun()

        with st.form("form_edicao_usuario"):
            nome = st.text_input("Nome completo", value=nome_atual)
            nascimento = st.date_input(
                "Data de nascimento", value=datetime.date.fromisoformat(data_nasc_atual)
            )
            funcao = st.text_input("Função", value=funcao_atual)
            login = st.text_input("Usuário", value=login_atual)

            if _pode_editar(login_atual):
                senha = st.text_input("Senha", value=senha_atual)
            else:
                senha = senha_atual

            if st.session_state.get("tipo") == "admin":
                tipo_sel = st.selectbox(
                    "Tipo de usuário", ["admin", "ope"], index=0 if tipo_atual == "admin" else 1
                )
            else:
                tipo_sel = tipo_atual

            enviar = st.form_submit_button("Salvar alterações")

        if enviar:
            sucesso = model_usuario.atualizar_usuario(
                usuario_id=user_id,
                nome=nome,
                data_nascimento=str(nascimento),
                funcao=funcao,
                usuario=login,
                senha=senha,
                tipo=tipo_sel,
            )
            if sucesso:
                st.success("Usuário atualizado com sucesso!")
                st.session_state.pop("editando_usuario")
                st.rerun()
            else:
                st.error("Erro ao atualizar o usuário.")
