# frontend/Screens/Screen_CadastroServico.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys
import datetime

# Importa models e serviço do Google Drive
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_servico, model_unidade, model_funcionario, model_servico_funcionarios

def exibir_tela_cadastro_servico():
    # Estilização
    aplicar_estilo_geral()

    if st.session_state.get("tipo") != "admin":
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    st.title("🛠️ Cadastro de Serviço (OS)")

    unidades = model_unidade.listar_unidades()
    funcionarios = model_funcionario.listar_funcionarios()

    if not unidades:
        st.warning("Cadastre uma unidade antes de criar um serviço.")
        st.stop()

    if not funcionarios:
        st.warning("Cadastre funcionários antes de criar um serviço.")
        st.stop()

    unidade_options = [f"{u[2]} ({u[0]})" for u in unidades]
    funcionario_options = [f"{f[1]} ({f[4]})" for f in funcionarios]

    with st.form("form_servico"):
        unidade_selecionada = st.selectbox("Unidade Vinculada", unidade_options)
        unidade_obj = unidades[unidade_options.index(unidade_selecionada)]

        # Gera o código do serviço automaticamente
        cod_servico = model_servico.gerar_codigo_servico()
        st.info(f"📝 Código do Serviço: {cod_servico}")

        tipo_servico = st.selectbox("Tipo de Serviço", [
            "Pitometria", "Instalação de Macromedidor", "Escavação Manual",
            "Escavação Mecânica", "Alvenaria", "Serviços Diversos..."
        ])
        data_criacao = st.date_input("Data de Criação", value=datetime.date.today())
        data_execucao = st.date_input("Data de Execução (opcional)", value=None)
        status = st.selectbox("Status", ["Ativo", "Em andamento", "Pausada", "Encerrado"])
        observacoes = st.text_area("Observações")

        # Seleção múltipla de funcionários
        st.subheader("👥 Funcionários Responsáveis")
        funcionarios_selecionados = st.multiselect(
            "Selecione os funcionários que executarão o serviço",
            funcionario_options,
            key="funcionarios_servico"
        )

        enviado = st.form_submit_button("Cadastrar Serviço")

        if enviado:
            # Primeiro cria o serviço
            sucesso = model_servico.criar_servico(
                cod_servico=cod_servico,
                cod_unidade=unidade_obj[0],
                tipo_servico=tipo_servico,
                data_criacao=str(data_criacao),
                data_execucao=str(data_execucao) if data_execucao else None,
                status=status,
                observacoes=observacoes
            )

            if sucesso:
                # Se o serviço foi criado com sucesso, associa os funcionários
                sucesso_funcionarios = True
                for func in funcionarios_selecionados:
                    cod_funcionario = funcionarios[funcionario_options.index(func)][4]
                    if not model_servico_funcionarios.atribuir_funcionario_a_servico(cod_servico, cod_funcionario):
                        sucesso_funcionarios = False
                        st.error(f"Erro ao associar funcionário: {func}")

                if sucesso_funcionarios:
                    st.success("Serviço cadastrado e funcionários associados com sucesso!")
                else:
                    st.warning("Serviço cadastrado, mas houve erro ao associar alguns funcionários.")
            else:
                st.error("Erro ao cadastrar serviço.")
