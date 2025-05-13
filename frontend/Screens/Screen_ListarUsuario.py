# frontend/Screens/Screen_ListarUsuario.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys
from frontend.Utils.auth import verificar_permissao_admin

# Importa model de usuário
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_usuario

def verificar_permissao_edicao():
    """Verifica se o usuário tem permissão para editar usuários"""
    usuario_atual = st.session_state.get("usuario")
    return usuario_atual in ["Isaque.Z", "Isaque.S", "Ismaque.Z"]

def exibir_tela_listar_usuarios():
    """Exibe a tela de listagem de usuários"""
    # Aplica o estilo global
    aplicar_estilo_geral()

    # Verifica permissão de administrador
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    # Título
    st.title("📋 Lista de Usuários")

    usuarios = model_usuario.listar_usuarios()
    usuario_atual = st.session_state.get("usuario")

    if not usuarios:
        st.info("Nenhum usuário cadastrado.")
    else:
        for u in usuarios:
            with st.expander(f"👤 {u[1]} ({u[3]})"):  # nome (u[1]), tipo (u[3])
                st.markdown(f"**Função:** {u[4]}")
                st.markdown(f"**Usuário:** {u[2]}")
                st.markdown(f"**Tipo:** {u[3]}")

                # Mostra senha apenas para usuários autorizados ou para o próprio usuário
                if verificar_permissao_edicao() or u[2] == usuario_atual:
                    st.markdown(f"**Senha:** {u[5]}")

                col1, col2 = st.columns([1, 1])

                # Botão de edição apenas para usuários autorizados ou para o próprio usuário
                if verificar_permissao_edicao() or u[2] == usuario_atual:
                    with col1:
                        if st.button(f"✏️ Editar", key=f"edit_{u[0]}"):
                            st.session_state["editando_usuario"] = u
                            st.rerun()

                # Botão de exclusão apenas para usuários autorizados
                if verificar_permissao_edicao():
                    with col2:
                        if st.button(f"🗑 Excluir", key=f"del_{u[0]}"):
                            model_usuario.deletar_usuario(u[0])
                            st.success("Usuário excluído com sucesso!")
                            st.rerun()

    # Edição se houver usuário em edição
    if st.session_state.get("editando_usuario"):
        st.markdown("---")
        st.subheader("✏️ Editar Usuário")

        usuario = st.session_state["editando_usuario"]
        dados_completos = model_usuario.buscar_usuario_por_id(usuario[0])

        # Verifica se o usuário atual tem permissão para editar
        if not verificar_permissao_edicao() and usuario[2] != usuario_atual:
            st.error("Você não tem permissão para editar este usuário.")
            st.session_state["editando_usuario"] = None
            st.rerun()

        with st.form("form_edicao_usuario"):
            nome = st.text_input("Nome completo", value=dados_completos[1])
            nascimento = st.date_input("Data de nascimento", value=dados_completos[2])
            funcao = st.text_input("Função", value=dados_completos[3])
            login = st.text_input("Usuário", value=dados_completos[4])
            
            # Campo de senha apenas para usuários autorizados ou para o próprio usuário
            if verificar_permissao_edicao() or usuario[2] == usuario_atual:
                senha = st.text_input("Senha", value=dados_completos[5])
            else:
                senha = dados_completos[5]  # Mantém a senha atual

            # Tipo de usuário apenas para usuários autorizados
            if verificar_permissao_edicao():
                tipo = st.selectbox("Tipo de usuário", ["admin", "ope"], index=0 if dados_completos[6] == "admin" else 1)
            else:
                tipo = dados_completos[6]  # Mantém o tipo atual

            enviado = st.form_submit_button("Salvar Alterações")

            if enviado:
                sucesso = model_usuario.atualizar_usuario(
                    usuario_id=usuario[0],
                    nome=nome,
                    data_nascimento=str(nascimento),
                    funcao=funcao,
                    usuario=login,
                    senha=senha,
                    tipo=tipo
                )
                if sucesso:
                    st.success("Usuário atualizado com sucesso!")
                    st.session_state["editando_usuario"] = None
                    st.rerun()
                else:
                    st.error("Erro ao atualizar o usuário.")
