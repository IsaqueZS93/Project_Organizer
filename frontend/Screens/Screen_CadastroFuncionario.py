# frontend/Screens/Screen_CadastroFuncionario.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys
import datetime
from frontend.Utils.auth import verificar_permissao_admin

# Importa model do funcionário
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_funcionario

def exibir_tela_cadastro_funcionario():
    # Aplica estilo
    aplicar_estilo_geral()

    # Verifica permissão de administrador
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    # Título e instruções
    st.title("👷 Cadastro de Funcionário")
    st.markdown("Insira os dados do novo funcionário.")

    with st.form("form_funcionario"):
        nome = st.text_input("Nome completo")
        
        # Data de nascimento com range amplo
        min_date = datetime.date(1900, 1, 1)
        max_date = datetime.date.today()
        nascimento = st.date_input(
            "Data de nascimento",
            min_value=min_date,
            max_value=max_date,
            value=datetime.date(1990, 1, 1)
        )
        
        cpf = st.text_input("CPF")
        cod_funcionario = st.text_input("Código do Funcionário (único)")
        funcao = st.text_input("Função")

        enviar = st.form_submit_button("Cadastrar")

        if enviar:
            if not nome or not cpf or not cod_funcionario:
                st.warning("Por favor, preencha todos os campos obrigatórios.")
            else:
                try:
                    sucesso = model_funcionario.criar_funcionario(
                        nome=nome,
                        data_nascimento=str(nascimento),
                        cpf=cpf,
                        cod_funcionario=cod_funcionario,
                        funcao=funcao
                    )
                    if sucesso:
                        st.success("Funcionário cadastrado com sucesso!")
                        st.rerun()  # Recarrega a página para limpar o formulário
                    else:
                        st.error("Erro ao cadastrar funcionário. Verifique se o CPF ou código já existe.")
                except Exception as e:
                    st.error(f"Erro ao cadastrar funcionário: {str(e)}")
