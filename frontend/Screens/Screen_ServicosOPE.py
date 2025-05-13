# frontend/Screens/Screen_ServicosOPE.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys
import datetime

# Importa model
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_servico, model_servico_funcionarios

def exibir_tela_servicos_ope():
    # Aplica tema
    aplicar_estilo_geral()

    # Verifica se o usuário está autenticado
    if not st.session_state.get("autenticado"):
        st.error("Acesso negado. Faça login para acessar esta tela.")
        st.stop()

    st.title("🔎 Serviços Disponíveis (Execução)")

    # Filtros
    st.subheader("🔍 Filtros")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_status = st.selectbox(
            "Status",
            ["Todos"] + ["Ativo", "Em andamento", "Pausada"]
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

    servicos = model_servico.listar_servicos()

    # Aplica filtros
    if filtro_status != "Todos":
        servicos = [s for s in servicos if s[5] == filtro_status]
    else:
        # Filtra por status relevantes
        servicos = [s for s in servicos if s[5] in ("Ativo", "Em andamento", "Pausada")]
    
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
                        st.markdown(f"**{f[1]}** ({f[0]})")
                        st.markdown(f"*{f[2]}*")
                else:
                    st.info("Nenhum funcionário associado a este serviço.")

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
                    # Campo de descrição opcional
                    descricao = st.text_input("Descrição para todos os arquivos (opcional)", key=f"desc_{s[0]}")
                    
                    if st.button("Enviar Todos", key=f"send_{s[0]}"):
                        sucesso_total = True
                        for arquivo in arquivos:
                            # Trata a descrição para evitar valores nulos
                            descricao_arquivo = descricao.strip() if descricao else None
                            
                            sucesso = model_servico.upload_arquivo_servico(
                                cod_servico=s[0],
                                arquivo=arquivo.getvalue(),
                                nome_arquivo=arquivo.name,
                                tipo_arquivo=arquivo.type,
                                descricao=descricao_arquivo
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
                    st.subheader("📁 Arquivos do Serviço")
                    
                    # Grid de arquivos
                    cols = st.columns(4)
                    for i, arquivo in enumerate(arquivos):
                        col = cols[i % 4]
                        with col:
                            # Container para cada arquivo
                            with st.container():
                                # Ícone baseado no tipo de arquivo
                                if arquivo[2].startswith('image/'):
                                    st.image("https://drive.google.com/uc?export=view&id=" + arquivo[5], use_column_width=True)
                                else:
                                    st.write(get_file_icon(arquivo[2]))
                                
                                # Nome do arquivo
                                st.write(arquivo[1])
                                
                                # Data de upload
                                st.write(f"📅 {arquivo[3]}")
                                
                                # Descrição (se houver)
                                if arquivo[4]:
                                    st.write(f"📝 {arquivo[4]}")
                                
                                # Botão de download
                                if st.button("⬇️ Download", key=f"download_{arquivo[0]}"):
                                    with st.spinner("Baixando arquivo..."):
                                        try:
                                            arquivo_bytes = model_servico.download_arquivo_servico(arquivo[0])
                                            if arquivo_bytes:
                                                st.download_button(
                                                    label="Clique para salvar",
                                                    data=arquivo_bytes,
                                                    file_name=arquivo[1],
                                                    mime=arquivo[2],
                                                    key=f"save_{arquivo[0]}"
                                                )
                                            else:
                                                st.error("❌ Erro ao baixar arquivo. Tente novamente.")
                                        except Exception as e:
                                            st.error(f"❌ Erro ao baixar arquivo: {str(e)}")
                                            st.error("Tente novamente.")
                else:
                    st.info("Nenhum arquivo encontrado com os filtros selecionados.")

                if st.button("✏️ Preencher Dados / Atualizar", key=f"exec_{s[0]}"):
                    st.session_state["executando_servico"] = s
                    st.rerun()

    if st.session_state.get("executando_servico"):
        s = st.session_state["executando_servico"]
        st.markdown("---")
        st.subheader("📝 Atualizar Serviço")

        with st.form("form_execucao"):
            tipo = st.text_input("Tipo de Serviço", value=s[2])
            data_exec = st.date_input("Data de Execução", value=s[4] or None)
            status = st.selectbox("Status", ["Ativo", "Em andamento", "Pausada", "Encerrado"], index=["Ativo", "Em andamento", "Pausada", "Encerrado"].index(s[5]))
            obs = st.text_area("Observações", value=s[6] or "")

            enviado = st.form_submit_button("Salvar Atualizações")

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
                    st.session_state["executando_servico"] = None
                    st.rerun()
                else:
                    st.error("Erro ao atualizar o serviço.")
