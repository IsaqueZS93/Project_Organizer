import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys

# Importa models
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_usuario

def verificar_permissao_edicao():
    """Verifica se o usuário atual tem permissão para editar usuários"""
    usuario_atual = st.session_state.get("usuario")
    return usuario_atual in ["Isaque.Z", "Ismaque.Z"]

def exibir_tela_usuarios():
    # Aplica tema
    aplicar_estilo_geral()

    # Acesso permitido para admin
    tipo = st.session_state.get("tipo")
    if tipo != "admin":
        st.error("❌ Acesso negado. Apenas administradores podem acessar esta tela.")
        st.stop()

    st.title("👥 Usuários")

    # Verifica permissão de edição
    tem_permissao = verificar_permissao_edicao()
    if not tem_permissao:
        st.warning("⚠️ Apenas Isaque.Z e Ismaque.Z podem editar e excluir usuários.")

    # Lista usuários
    usuarios = model_usuario.listar_usuarios()
    if not usuarios:
        st.info("Nenhum usuário cadastrado.")
        return

    # Exibe tabela de usuários
    st.markdown("### Lista de Usuários")
    
    # Cabeçalho da tabela
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
    with col1:
        st.markdown("**Usuário**")
    with col2:
        st.markdown("**Nome**")
    with col3:
        st.markdown("**Tipo**")
    with col4:
        st.markdown("**Editar**")
    with col5:
        st.markdown("**Excluir**")

    # Linhas da tabela
    for usuario in usuarios:
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
        with col1:
            st.markdown(usuario[0])  # Usuário
        with col2:
            st.markdown(usuario[1])  # Nome
        with col3:
            st.markdown(usuario[2])  # Tipo
        with col4:
            if tem_permissao:
                if st.button("✏️", key=f"edit_{usuario[0]}"):
                    st.session_state['editando_usuario'] = usuario[0]
                    st.rerun()
            else:
                st.markdown("🔒")
        with col5:
            if tem_permissao:
                if st.button("🗑️", key=f"del_{usuario[0]}"):
                    if st.button("Confirmar Exclusão", key=f"confirm_del_{usuario[0]}"):
                        if model_usuario.deletar_usuario(usuario[0]):
                            st.success("✅ Usuário excluído com sucesso!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao excluir usuário")
            else:
                st.markdown("🔒")

    # Formulário de edição
    if 'editando_usuario' in st.session_state:
        st.markdown("### ✏️ Editar Usuário")
        usuario = model_usuario.buscar_usuario(st.session_state['editando_usuario'])
        if usuario:
            with st.form("editar_usuario"):
                nome = st.text_input("Nome", value=usuario[1])
                tipo = st.selectbox("Tipo", ["admin", "ope"], index=0 if usuario[2] == "admin" else 1)
                senha = st.text_input("Nova Senha (deixe em branco para manter a atual)", type="password")
                
                if st.form_submit_button("Salvar"):
                    if model_usuario.atualizar_usuario(usuario[0], nome, tipo, senha if senha else None):
                        st.success("✅ Usuário atualizado com sucesso!")
                        del st.session_state['editando_usuario']
                        st.rerun()
                    else:
                        st.error("❌ Erro ao atualizar usuário")

    # Formulário de cadastro
    st.markdown("### ➕ Novo Usuário")
    with st.form("novo_usuario"):
        usuario = st.text_input("Usuário")
        nome = st.text_input("Nome")
        tipo = st.selectbox("Tipo", ["admin", "ope"])
        senha = st.text_input("Senha", type="password")
        
        if st.form_submit_button("Cadastrar"):
            if model_usuario.criar_usuario(usuario, nome, tipo, senha):
                st.success("✅ Usuário cadastrado com sucesso!")
                st.rerun()
            else:
                st.error("❌ Erro ao cadastrar usuário") 