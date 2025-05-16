# frontend/Screens/Screen_CadastroUsuario.py
# ------------------------------------------------------------------------------
#  Tela de Cadastro de Usuário (Streamlit)
#  • Código enxuto, sem hash de senha (a ser implementado futuramente)
#  • Validação de dados e UX com clear_on_submit + toast
# ------------------------------------------------------------------------------

import datetime

import streamlit as st

from Styles.theme import aplicar_estilo_geral
from frontend.Utils.auth import verificar_permissao_admin
from Models import model_usuario  # projeto já deve estar no PYTHONPATH


# ------------------------------------------------------------------------------
#  Tela principal ---------------------------------------------------------------
# ------------------------------------------------------------------------------

def exibir_tela_cadastro_usuario() -> None:
    """Exibe a interface de cadastro de usuário (apenas admins)."""

    aplicar_estilo_geral()

    # ------------ Permissão ----------------------------------------------------
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    # ------------ Layout -------------------------------------------------------
    st.title("👤 Cadastro de Usuário")
    st.markdown("Cadastre um novo usuário no sistema.")

    min_date = datetime.date(1900, 1, 1)
    max_date = datetime.date.today()

    with st.form("form_usuario", clear_on_submit=True):
        nome = st.text_input("Nome completo", max_chars=80)
        nascimento = st.date_input(
            "Data de nascimento",
            value=datetime.date(1990, 1, 1),
            min_value=min_date,
            max_value=max_date,
        )
        funcao = st.text_input("Função", placeholder="Ex.: Analista")
        usuario = st.text_input("Nome de usuário", max_chars=30)
        senha = st.text_input("Senha", type="password")
        tipo = st.selectbox("Tipo de usuário", ["admin", "ope"], index=1)

        enviar = st.form_submit_button("Cadastrar")

    # ------------ Processamento ------------------------------------------------
    if not enviar:
        return

    # Campos obrigatórios -------------------------------------------------------
    if not (nome.strip() and usuario.strip() and senha):
        st.warning("Preencha todos os campos obrigatórios – nome, usuário e senha.")
        return

    # NOTA: Hash de senha será implementado futuramente.
    sucesso = model_usuario.criar_usuario(
        nome=nome.strip(),
        data_nascimento=str(nascimento),
        funcao=funcao.strip(),
        usuario=usuario.strip(),
        senha=senha,  # armazenado em texto puro por enquanto
        tipo=tipo,
    )

    if sucesso:
        st.success("Usuário cadastrado com sucesso!")
        st.toast("Novo usuário criado ✅", icon="🎉")
    else:
        st.error("Erro ao cadastrar usuário. Verifique se o nome de usuário já existe.")
