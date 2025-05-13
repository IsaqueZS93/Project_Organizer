# frontend/Screens/Screen_GridPastas.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys
import datetime
import os
from tempfile import gettempdir
from frontend.Utils.auth import verificar_permissao_admin

# Importa models
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_empresa, model_contrato, model_unidade, model_servico
from Services import Service_googledrive as gdrive

def get_file_icon(mime_type: str) -> str:
    """Retorna o ícone apropriado para o tipo de arquivo"""
    if mime_type == 'application/vnd.google-apps.folder':
        return "📁"
    
    # Mapeamento de tipos MIME para ícones
    mime_icons = {
        'image/': '🖼️',
        'video/': '🎥',
        'audio/': '🎵',
        'text/': '📝',
        'application/pdf': '📄',
        'application/msword': '📝',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📝',
        'application/vnd.ms-excel': '📊',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '📊',
        'application/vnd.ms-powerpoint': '📑',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '📑',
        'application/zip': '🗜️',
        'application/x-rar-compressed': '🗜️',
    }
    
    for mime_prefix, icon in mime_icons.items():
        if mime_type.startswith(mime_prefix):
            return icon
    
    return '📄'  # Ícone padrão para outros tipos de arquivo

def format_file_size(size_bytes: int) -> str:
    """Formata o tamanho do arquivo em uma string legível"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def get_folder_id():
    """Obtém o ID da pasta do Drive do session_state ou do secrets.toml"""
    try:
        # Tenta obter do session_state
        if "GDRIVE_EMPRESAS_FOLDER_ID" in st.session_state:
            return st.session_state["GDRIVE_EMPRESAS_FOLDER_ID"]
            
        # Se não estiver no session_state, tenta obter do secrets.toml
        if "gdrive" in st.secrets and "empresas_folder_id" in st.secrets["gdrive"]:
            folder_id = st.secrets["gdrive"]["empresas_folder_id"]
            st.session_state["GDRIVE_EMPRESAS_FOLDER_ID"] = folder_id
            return folder_id
            
        # Se não encontrar em nenhum lugar, usa o valor padrão
        default_id = "1H1y0x5RPzfcm6xD95OaOcJ023u4RcPk5"
        st.session_state["GDRIVE_EMPRESAS_FOLDER_ID"] = default_id
        return default_id
        
    except Exception as e:
        logger.error(f"Erro ao obter folder_id: {str(e)}")
        # Em caso de erro, retorna o valor padrão
        return "1H1y0x5RPzfcm6xD95OaOcJ023u4RcPk5"

def get_folder_name(folder_id: str) -> str:
    """Obtém o nome de uma pasta do Drive"""
    try:
        file = gdrive.get_file_info(folder_id)
        return file.get('name', 'Pasta sem nome')
    except:
        return 'Pasta sem nome'

def exibir_conteudo_pasta(folder_id: str):
    """Exibe o conteúdo de uma pasta do Drive em formato de grade"""
    try:
        if not folder_id:
            st.error("ID da pasta não encontrado. Por favor, verifique as configurações.")
            return
            
        # Lista arquivos e pastas
        items = gdrive.list_files_in_folder(folder_id)
        
        # Separa pastas e arquivos
        pastas = [item for item in items if item['mimeType'] == 'application/vnd.google-apps.folder']
        arquivos = [item for item in items if item['mimeType'] != 'application/vnd.google-apps.folder']
        
        # Exibe pastas em grade
        if pastas:
            st.markdown("### 📁 Pastas")
            cols = st.columns(2)  # Reduzido para 2 colunas para mais espaço
            for idx, pasta in enumerate(pastas):
                with cols[idx % 2]:
                    st.markdown(f"""
                    <div style='text-align: center; padding: 20px; border: 1px solid #ddd; border-radius: 8px; margin: 15px; background-color: #f8f9fa;'>
                        <div style='font-size: 3em; margin-bottom: 15px;'>{get_file_icon(pasta['mimeType'])}</div>
                        <div style='font-weight: bold; font-size: 1.3em; margin: 15px 0;'>{pasta['name']}</div>
                        <div style='font-size: 1em; color: #666; margin-bottom: 10px;'>{pasta['createdTime'].split('T')[0]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Botões em coluna única para mais espaço
                    if st.button("📂 Abrir Pasta", key=f"view_{pasta['id']}", use_container_width=True):
                        # Adiciona a pasta atual ao histórico antes de navegar
                        if 'folder_history' not in st.session_state:
                            st.session_state['folder_history'] = []
                        st.session_state['folder_history'].append({
                            'id': st.session_state['current_folder'],
                            'name': get_folder_name(st.session_state['current_folder'])
                        })
                        st.session_state['current_folder'] = pasta['id']
                        st.rerun()
                    if st.button("🔄 Atualizar", key=f"refresh_{pasta['id']}", use_container_width=True):
                        st.rerun()
                    st.markdown("---")  # Separador entre pastas
        
        # Exibe arquivos em grade
        if arquivos:
            st.markdown("### 📄 Arquivos")
            cols = st.columns(2)  # Reduzido para 2 colunas para mais espaço
            for idx, arquivo in enumerate(arquivos):
                with cols[idx % 2]:
                    st.markdown(f"""
                    <div style='text-align: center; padding: 20px; border: 1px solid #ddd; border-radius: 8px; margin: 15px; background-color: #f8f9fa;'>
                        <div style='font-size: 3em; margin-bottom: 15px;'>{get_file_icon(arquivo['mimeType'])}</div>
                        <div style='font-weight: bold; font-size: 1.3em; margin: 15px 0;'>{arquivo['name']}</div>
                        <div style='font-size: 1em; color: #666; margin-bottom: 5px;'>{format_file_size(int(arquivo.get('size', 0)))}</div>
                        <div style='font-size: 1em; color: #666; margin-bottom: 10px;'>{arquivo['createdTime'].split('T')[0]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Botões em coluna única para mais espaço
                    if st.button("📥 Download", key=f"down_{arquivo['id']}", use_container_width=True):
                        temp_file = Path(gettempdir()) / arquivo['name']
                        if gdrive.download_file(arquivo['id'], str(temp_file)):
                            with open(temp_file, 'rb') as f:
                                st.download_button(
                                    label="Baixar Arquivo",
                                    data=f,
                                    file_name=arquivo['name'],
                                    mime=arquivo['mimeType'],
                                    key=f"dl_{arquivo['id']}",
                                    use_container_width=True
                                )
                        temp_file.unlink()
                    
                    if st.button("↗️ Transferir", key=f"move_{arquivo['id']}", use_container_width=True):
                        # Lista todas as pastas disponíveis
                        todas_pastas = []
                        def listar_pastas_recursivamente(pasta_id, nivel=0):
                            items = gdrive.list_files_in_folder(pasta_id)
                            for item in items:
                                if item['mimeType'] == 'application/vnd.google-apps.folder':
                                    todas_pastas.append({
                                        'id': item['id'],
                                        'nome': '  ' * nivel + '📁 ' + item['name']
                                    })
                                    listar_pastas_recursivamente(item['id'], nivel + 1)
                        
                        # Inicia a listagem a partir da pasta raiz
                        listar_pastas_recursivamente(get_folder_id())
                        
                        # Remove a pasta atual da lista
                        todas_pastas = [p for p in todas_pastas if p['id'] != folder_id]
                        
                        if todas_pastas:
                            pasta_destino = st.selectbox(
                                "Selecione a pasta de destino:",
                                options=[p['id'] for p in todas_pastas],
                                format_func=lambda x: next(p['nome'] for p in todas_pastas if p['id'] == x),
                                key=f"select_{arquivo['id']}"
                            )
                            
                            if st.button("Confirmar Transferência", key=f"confirm_move_{arquivo['id']}", use_container_width=True):
                                if model_servico.transferir_arquivo_servico(arquivo['id'], pasta_destino):
                                    st.success("✅ Arquivo transferido com sucesso!")
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao transferir arquivo")
                        else:
                            st.info("Não há outras pastas disponíveis para transferência")
                    
                    if st.button("🗑 Excluir", key=f"del_{arquivo['id']}", use_container_width=True):
                        if st.button("Confirmar Exclusão", key=f"confirm_del_{arquivo['id']}", use_container_width=True):
                            st.info("Exclusão em desenvolvimento")
                    
                    st.markdown("---")  # Separador entre arquivos
    
    except Exception as e:
        st.error(f"Erro ao listar conteúdo da pasta: {e}")

def exibir_tela_grid_pastas():
    # Aplica tema
    aplicar_estilo_geral()

    # Verifica permissão de administrador
    if not verificar_permissao_admin():
        st.error("❌ Acesso negado. Apenas administradores podem acessar esta tela.")
        st.stop()

    st.title("📁 Navegador de Pastas")

    # Inicializa estado da pasta atual e histórico
    if 'current_folder' not in st.session_state:
        st.session_state['current_folder'] = get_folder_id()
    if 'folder_history' not in st.session_state:
        st.session_state['folder_history'] = []

    # Barra de navegação
    st.markdown("### 📂 Navegação")
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("🏠 Pasta Raiz"):
            # Limpa o histórico ao voltar para a raiz
            st.session_state['folder_history'] = []
            st.session_state['current_folder'] = get_folder_id()
            st.rerun()
    
    with col2:
        # Botão Voltar só fica ativo se houver histórico
        if st.session_state['folder_history']:
            if st.button("⬅️ Voltar"):
                # Pega a última pasta do histórico
                ultima_pasta = st.session_state['folder_history'].pop()
                st.session_state['current_folder'] = ultima_pasta['id']
                st.rerun()
        else:
            st.button("⬅️ Voltar", disabled=True)
    
    with col3:
        if st.button("🔄 Atualizar"):
            st.rerun()

    # Exibe caminho atual
    if st.session_state['folder_history']:
        caminho = " > ".join([p['name'] for p in st.session_state['folder_history']])
        caminho += f" > {get_folder_name(st.session_state['current_folder'])}"
        st.markdown(f"**Caminho atual:** {caminho}")

    # Exibe conteúdo da pasta atual
    st.markdown("---")
    exibir_conteudo_pasta(st.session_state['current_folder'])

    # Estatísticas
    st.markdown("---")
    st.markdown("### 📊 Estatísticas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total de Pastas", len([f for f in gdrive.list_files_in_folder(st.session_state['current_folder']) 
                                        if f['mimeType'] == 'application/vnd.google-apps.folder']))
    
    with col2:
        st.metric("Total de Arquivos", len([f for f in gdrive.list_files_in_folder(st.session_state['current_folder']) 
                                          if f['mimeType'] != 'application/vnd.google-apps.folder']))
    
    with col3:
        total_size = sum(int(f.get('size', 0)) for f in gdrive.list_files_in_folder(st.session_state['current_folder']) 
                        if f['mimeType'] != 'application/vnd.google-apps.folder')
        st.metric("Tamanho Total", f"{total_size / 1024 / 1024:.2f} MB")
