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

    servicos = model_servico.listar_servicos(
        status=None if filtro_status == "Todos" else [filtro_status],
        data_ini=filtro_data_inicio.isoformat() if filtro_data_inicio else None,
        data_fim=filtro_data_fim.isoformat() if filtro_data_fim else None,
    )

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
                st.subheader("�� Upload de Arquivos")
                
                with st.form(f"form_up_{s[0]}"):
                    files = st.file_uploader("Arquivos", type=["pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"], accept_multiple_files=True)
                    desc = st.text_input("Descrição padrão (opcional)")
                    send = st.form_submit_button("Enviar")
                
                if send and files:
                    for f in files:
                        model_servico.upload_arquivo_servico(
                            cod_servico=s[0],
                            arquivo=f.read(),
                            nome_arquivo=f.name,
                            tipo_arquivo=f.type,
                            descricao=desc or None,
                        )
                    st.success("Enviados!")
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
                    num_cols = max(1, int(st.get_option("client.viewportWidth") / 260))
                    cols = st.columns(num_cols)
                    for i, arquivo in enumerate(arquivos):
                        col = cols[i % num_cols]
                        with col:
                            with st.container():
                                # Checagem robusta para evitar TypeError
                                try:
                                    tipo_arquivo = arquivo[2] if len(arquivo) > 2 else ''
                                    drive_file_id = arquivo[5] if len(arquivo) > 5 else ''
                                    if tipo_arquivo.startswith("image/") and drive_file_id:
                                        thumb = f"https://drive.google.com/thumbnail?id={drive_file_id}"
                                        st.image(thumb, use_container_width=True)
                                    else:
                                        st.markdown(get_file_icon(tipo_arquivo), unsafe_allow_html=True)
                                    st.write(arquivo[1] if len(arquivo) > 1 else "(sem nome)")
                                    st.write(f"📅 {arquivo[3] if len(arquivo) > 3 else ''}")
                                    if len(arquivo) > 4 and arquivo[4]:
                                        st.write(f"📝 {arquivo[4]}")
                                    if drive_file_id:
                                        dl_url = f"https://drive.google.com/uc?export=download&id={drive_file_id}"
                                        st.markdown(f"[⬇️ Download]({dl_url})", unsafe_allow_html=True)
                                    else:
                                        st.info("Arquivo sem ID do Drive para download.")
                                except Exception as e:
                                    st.error(f"Erro ao exibir arquivo: {e}")
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
