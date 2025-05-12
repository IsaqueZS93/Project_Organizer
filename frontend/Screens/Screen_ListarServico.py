# frontend/Screens/Screen_ListarServico.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys
import datetime
from frontend.Utils.auth import verificar_permissao_admin

# Importa models
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_servico, model_funcionario, model_servico_funcionarios

def exibir_tela_listar_servicos():
    """Exibe a tela de listagem de serviços"""
    # Estilo e segurança
    aplicar_estilo_geral()

    # Verifica permissão de administrador
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()

    st.title("🧾 Lista de Serviços Cadastrados")

    # Filtros
    st.subheader("🔍 Filtros")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_status = st.selectbox(
            "Status",
            ["Todos"] + ["Ativo", "Em andamento", "Pausada", "Encerrado"]
        )
    
    with col2:
        filtro_data_inicio = st.date_input(
            "Data Início",
            value=None
        )
    
    with col3:
        filtro_data_fim = st.date_input(
            "Data Fim",
            value=None
        )

    # Busca serviços
    servicos = model_servico.listar_servicos()

    # Aplica filtros
    if filtro_status != "Todos":
        servicos = [s for s in servicos if s[5] == filtro_status]
    
    if filtro_data_inicio:
        servicos = [s for s in servicos if s[3] and datetime.datetime.strptime(s[3], "%Y-%m-%d").date() >= filtro_data_inicio]
    
    if filtro_data_fim:
        servicos = [s for s in servicos if s[3] and datetime.datetime.strptime(s[3], "%Y-%m-%d").date() <= filtro_data_fim]

    if not servicos:
        st.info("Nenhum serviço encontrado com os filtros selecionados.")
    else:
        for s in servicos:
            with st.expander(f"🔧 {s[0]} - {s[2]} ({s[5]})"):
                st.markdown(f"**Unidade:** {s[1]}")
                st.markdown(f"**Tipo:** {s[2]}")
                st.markdown(f"**Data de Criação:** {s[3]}")
                st.markdown(f"**Data de Execução:** {s[4] or '---'}")
                st.markdown(f"**Status:** {s[5]}")
                st.markdown(f"**Observações:** {s[6] or '---'}")

                # Seção de funcionários
                st.markdown("---")
                st.subheader("👥 Funcionários Responsáveis")
                
                # Lista funcionários atuais
                funcionarios = model_servico_funcionarios.listar_funcionarios_por_servico(s[0])
                if funcionarios:
                    for f in funcionarios:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**{f[1]}** ({f[0]})")
                            st.markdown(f"*{f[2]}*")
                        with col2:
                            if st.button("❌ Remover", key=f"rem_func_{s[0]}_{f[0]}"):
                                if model_servico_funcionarios.remover_funcionario_de_servico(s[0], f[0]):
                                    st.success(f"Funcionário {f[1]} removido com sucesso!")
                                    st.rerun()
                                else:
                                    st.error(f"Erro ao remover funcionário {f[1]}")

                # Adicionar novo funcionário
                todos_funcionarios = model_funcionario.listar_funcionarios()
                funcionarios_disponiveis = [f for f in todos_funcionarios if f[4] not in [func[0] for func in funcionarios]]
                
                if funcionarios_disponiveis:
                    st.markdown("---")
                    st.subheader("➕ Adicionar Funcionário")
                    
                    funcionario_options = [f"{f[1]} ({f[4]})" for f in funcionarios_disponiveis]
                    novo_funcionario = st.selectbox(
                        "Selecione um funcionário para adicionar",
                        funcionario_options,
                        key=f"add_func_{s[0]}"
                    )
                    
                    if st.button("Adicionar", key=f"btn_add_{s[0]}"):
                        cod_funcionario = funcionarios_disponiveis[funcionario_options.index(novo_funcionario)][4]
                        if model_servico_funcionarios.atribuir_funcionario_a_servico(s[0], cod_funcionario):
                            st.success(f"Funcionário {novo_funcionario} adicionado com sucesso!")
                            st.rerun()
                        else:
                            st.error(f"Erro ao adicionar funcionário {novo_funcionario}")
                else:
                    st.info("Todos os funcionários já estão associados a este serviço.")

                # Seção de arquivos
                st.markdown("---")
                st.subheader("📎 Arquivos")
                
                # Upload múltiplo de arquivos
                arquivos = st.file_uploader(
                    "Upload de arquivos (múltiplos)",
                    type=["pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"],
                    accept_multiple_files=True,
                    key=f"upload_{s[0]}"
                )
                
                if arquivos:
                    descricao = st.text_input("Descrição para todos os arquivos", key=f"desc_{s[0]}")
                    if st.button("Enviar Todos", key=f"send_{s[0]}"):
                        sucesso_total = True
                        for arquivo in arquivos:
                            sucesso = model_servico.upload_arquivo_servico(
                                cod_servico=s[0],
                                arquivo=arquivo.getvalue(),
                                nome_arquivo=arquivo.name,
                                tipo_arquivo=arquivo.type,
                                descricao=descricao
                            )
                            if not sucesso:
                                sucesso_total = False
                                st.error(f"Erro ao enviar arquivo: {arquivo.name}")
                        
                        if sucesso_total:
                            st.success("Todos os arquivos foram enviados com sucesso!")
                            st.rerun()

                # Lista de arquivos com filtros
                st.subheader("Arquivos Anexados")
                
                # Filtros para arquivos
                col1, col2 = st.columns(2)
                with col1:
                    filtro_tipo = st.selectbox(
                        "Tipo de Arquivo",
                        ["Todos"] + ["pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"],
                        key=f"filtro_tipo_{s[0]}"
                    )
                
                with col2:
                    filtro_data = st.date_input(
                        "Data de Upload",
                        value=None,
                        key=f"filtro_data_{s[0]}"
                    )

                arquivos = model_servico.listar_arquivos_servico(s[0])
                
                # Aplica filtros nos arquivos
                if filtro_tipo != "Todos":
                    arquivos = [a for a in arquivos if a[2].split('/')[-1] == filtro_tipo]
                
                if filtro_data:
                    arquivos = [a for a in arquivos if a[3] and datetime.datetime.strptime(a[3], "%Y-%m-%d %H:%M:%S").date() == filtro_data]

                if arquivos:
                    for a in arquivos:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.markdown(f"**{a[1]}** ({a[2]})")
                            st.markdown(f"*{a[4] or 'Sem descrição'}*")
                            st.markdown(f"Upload: {a[3]}")
                        with col2:
                            if st.button("📥 Download", key=f"down_{a[0]}"):
                                arquivo_bytes = model_servico.download_arquivo_servico(a[0])
                                if arquivo_bytes:
                                    st.download_button(
                                        label="Baixar Arquivo",
                                        data=arquivo_bytes,
                                        file_name=a[1],
                                        mime=a[2],
                                        key=f"download_{a[0]}"
                                    )
                                else:
                                    st.error("Erro ao baixar arquivo")
                        with col3:
                            if st.button("🗑 Excluir", key=f"del_file_{a[0]}"):
                                if model_servico.deletar_arquivo_servico(a[0]):
                                    st.success("Arquivo excluído com sucesso!")
                                    st.rerun()
                                else:
                                    st.error("Erro ao excluir arquivo.")
                else:
                    st.info("Nenhum arquivo encontrado com os filtros selecionados.")

                # Botões de ação
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Editar", key=f"edit_{s[0]}"):
                        st.session_state["editando_servico"] = s
                        st.rerun()
                with col2:
                    if st.button("🗑 Excluir", key=f"del_{s[0]}"):
                        model_servico.deletar_servico(s[0])
                        st.success("Serviço excluído com sucesso!")
                        st.rerun()

    # Edição de serviço
    if st.session_state.get("editando_servico"):
        s = st.session_state["editando_servico"]
        st.markdown("---")
        st.subheader("✏️ Editar Serviço")

        with st.form("form_edita_servico"):
            tipo = st.text_input("Tipo de Serviço", value=s[2])
            data_exec = st.date_input("Data de Execução", value=s[4] or None)
            status = st.selectbox("Status", ["Ativo", "Em andamento", "Pausada", "Encerrado"], index=["Ativo", "Em andamento", "Pausada", "Encerrado"].index(s[5]))
            obs = st.text_area("Observações", value=s[6] or "")

            enviado = st.form_submit_button("Salvar")

            if enviado:
                sucesso = model_servico.atualizar_servico(
                    cod_servico=s[0],
                    tipo_servico=tipo,
                    data_execucao=str(data_exec),
                    status=status,
                    observacoes=obs
                )
                if sucesso:
                    st.success("Serviço atualizado com sucesso!")
                    st.session_state["editando_servico"] = None
                    st.rerun()
                else:
                    st.error("Erro ao atualizar serviço.")
