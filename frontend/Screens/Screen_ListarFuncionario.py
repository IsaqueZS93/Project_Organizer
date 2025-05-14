# frontend/Screens/Screen_ListarFuncionario.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys
import datetime
from frontend.Utils.auth import verificar_permissao_admin

# Importa model de funcionário
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_funcionario

def exibir_tela_listar_funcionarios():
    # Aplica o estilo visual
    aplicar_estilo_geral()

    # Verifica permissão de administrador
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    # Título
    st.title("📋 Lista de Funcionários")

    funcionarios = model_funcionario.listar_funcionarios()

    if not funcionarios:
        st.info("Nenhum funcionário cadastrado.")
    else:
        for f in funcionarios:
            with st.expander(f"👷 {f[1]} - {f[4]}"):
                st.markdown(f"**Nascimento:** {f[3]}")
                st.markdown(f"**CPF:** {f[2]}")
                st.markdown(f"**Código:** {f[0]}")
                st.markdown(f"**Função:** {f[4]}")

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
            nome_edit = st.text_input("Nome completo", value=f[1])
            
            min_date = datetime.date(1900, 1, 1)
            max_date = datetime.date.today()
            data_nascimento_val = datetime.datetime.strptime(f[3], "%Y-%m-%d").date() if f[3] else None
            nascimento_edit = st.date_input(
                "Data de nascimento",
                min_value=min_date,
                max_value=max_date,
                value=data_nascimento_val
            )
            
            cpf_edit = st.text_input("CPF", value=f[2])
            cod_func_edit = st.text_input("Código do Funcionário", value=f[0], disabled=True)
            funcao_edit = st.text_input("Função", value=f[4])

            enviado = st.form_submit_button("Salvar alterações")

            if enviado:
                data_nascimento_str = nascimento_edit.strftime("%Y-%m-%d") if nascimento_edit else None
                
                sucesso = model_funcionario.atualizar_funcionario(
                    cod_funcionario_original=f[0],
                    novo_nome=nome_edit,
                    nova_data_nascimento=data_nascimento_str,
                    novo_cpf=cpf_edit,
                    nova_funcao=funcao_edit
                )
                if sucesso:
                    st.success("Funcionário atualizado com sucesso!")
                    st.session_state["editando_funcionario"] = None
                    st.rerun()
                else:
                    st.error("Erro ao atualizar funcionário.")
