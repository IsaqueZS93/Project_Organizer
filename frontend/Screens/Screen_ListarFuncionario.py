# frontend/Screens/Screen_ListarFuncionario.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys

# Importa model de funcionário
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_funcionario

def exibir_tela_listar_funcionarios():
    # Aplica o estilo visual
    aplicar_estilo_geral()

    # Proteção de acesso
    if st.session_state.get("tipo") != "admin":
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    # Título
    st.title("📋 Lista de Funcionários")

    funcionarios = model_funcionario.listar_funcionarios()

    if not funcionarios:
        st.info("Nenhum funcionário cadastrado.")
    else:
        for f in funcionarios:
            with st.expander(f"👷 {f[1]} - {f[5]}"):
                st.markdown(f"**Nascimento:** {f[2]}")
                st.markdown(f"**CPF:** {f[3]}")
                st.markdown(f"**Código:** {f[4]}")
                st.markdown(f"**Função:** {f[5]}")

                col1, col2 = st.columns([1, 1])

                with col1:
                    if st.button("✏️ Editar", key=f"edit_{f[0]}"):
                        st.session_state["editando_funcionario"] = f
                        st.rerun()

                with col2:
                    if st.button("🗑 Excluir", key=f"del_{f[0]}"):
                        model_funcionario.deletar_funcionario(f[0])
                        st.success("Funcionário excluído com sucesso!")
                        st.rerun()

    # Formulário de edição
    if st.session_state.get("editando_funcionario"):
        st.markdown("---")
        st.subheader("✏️ Editar Funcionário")

        f = st.session_state["editando_funcionario"]

        with st.form("form_edicao_func"):
            nome = st.text_input("Nome completo", value=f[1])
            nascimento = st.date_input("Data de nascimento", value=f[2])
            cpf = st.text_input("CPF", value=f[3])
            cod_func = st.text_input("Código do Funcionário", value=f[4])
            funcao = st.text_input("Função", value=f[5])

            enviado = st.form_submit_button("Salvar alterações")

            if enviado:
                sucesso = model_funcionario.atualizar_funcionario(
                    func_id=f[0],
                    nome=nome,
                    data_nascimento=str(nascimento),
                    cpf=cpf,
                    cod_funcionario=cod_func,
                    funcao=funcao
                )
                if sucesso:
                    st.success("Funcionário atualizado com sucesso!")
                    st.session_state["editando_funcionario"] = None
                    st.rerun()
                else:
                    st.error("Erro ao atualizar funcionário.")
