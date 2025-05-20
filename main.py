# main.py

import streamlit as st
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# ────── Ajusta sys.path para importar os módulos corretamente ──────
ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))  # backend
sys.path.append(str(ROOT / "frontend"))  # frontend
sys.path.append(str(ROOT / "frontend" / "Styles"))  # estilos

# Agora importa os módulos do backend
from backend.Database import db_gestaodecontratos as db
from backend.Database.db_gestaodecontratos import atualizar_banco, fechar_conexao

# Importa módulos do frontend
from frontend.Screens.Screen_Login import login, logout
from frontend.Utils.auth import verificar_permissao_admin

# Configuração de logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────── Configura variáveis do Google Drive ──────
def configurar_variaveis_drive():
    """Configura as variáveis do Google Drive no session_state"""
    try:
        # Configura variáveis do Google Drive do secrets.toml
        if "gdrive" in st.secrets:
            if "database_folder_id" in st.secrets["gdrive"]:
                st.session_state["GDRIVE_DATABASE_FOLDER_ID"] = st.secrets["gdrive"]["database_folder_id"]
            if "empresas_folder_id" in st.secrets["gdrive"]:
                st.session_state["GDRIVE_EMPRESAS_FOLDER_ID"] = st.secrets["gdrive"]["empresas_folder_id"]
        
        # Configura variáveis de usuário padrão do secrets.toml
        if "DEFAULT_ADMIN_USER" in st.secrets:
            st.session_state["DEFAULT_ADMIN_USER"] = st.secrets["DEFAULT_ADMIN_USER"]
        if "DEFAULT_ADMIN_PASS" in st.secrets:
            st.session_state["DEFAULT_ADMIN_PASS"] = st.secrets["DEFAULT_ADMIN_PASS"]
            
        # Configura valores padrão se não encontrados no secrets.toml
        if "GDRIVE_DATABASE_FOLDER_ID" not in st.session_state:
            st.session_state["GDRIVE_DATABASE_FOLDER_ID"] = "1OwkYVqfY8jRaYvZzhW9MkekJAGKSqbPX"
        if "GDRIVE_EMPRESAS_FOLDER_ID" not in st.session_state:
            st.session_state["GDRIVE_EMPRESAS_FOLDER_ID"] = "1H1y0x5RPzfcm6xD95OaOcJ023u4RcPk5"
        if "DEFAULT_ADMIN_USER" not in st.session_state:
            st.session_state["DEFAULT_ADMIN_USER"] = "Isaque.Z"
        if "DEFAULT_ADMIN_PASS" not in st.session_state:
            st.session_state["DEFAULT_ADMIN_PASS"] = "071959"
            
        logger.info("Variáveis do Google Drive configuradas com sucesso")
        logger.info(f"Database Folder ID: {st.session_state.get('GDRIVE_DATABASE_FOLDER_ID')}")
        logger.info(f"Empresas Folder ID: {st.session_state.get('GDRIVE_EMPRESAS_FOLDER_ID')}")
        
    except Exception as e:
        logger.warning(f"Erro ao carregar variáveis de ambiente: {e}")
        
        # Configura valores padrão mesmo se houver erro
        if "GDRIVE_DATABASE_FOLDER_ID" not in st.session_state:
            st.session_state["GDRIVE_DATABASE_FOLDER_ID"] = "1OwkYVqfY8jRaYvZzhW9MkekJAGKSqbPX"
        if "GDRIVE_EMPRESAS_FOLDER_ID" not in st.session_state:
            st.session_state["GDRIVE_EMPRESAS_FOLDER_ID"] = "1H1y0x5RPzfcm6xD95OaOcJ023u4RcPk5"
        if "DEFAULT_ADMIN_USER" not in st.session_state:
            st.session_state["DEFAULT_ADMIN_USER"] = "Isaque.Z"
        if "DEFAULT_ADMIN_PASS" not in st.session_state:
            st.session_state["DEFAULT_ADMIN_PASS"] = "071959"
            
        logger.info("Variáveis padrão configuradas")

# Configura as variáveis antes de qualquer operação
configurar_variaveis_drive()

# ────── Controle de autenticação ──────
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    login()
    st.stop()

# ────── Tela principal com navegação ──────
from frontend.Styles.theme import aplicar_estilo_geral
aplicar_estilo_geral()

# Atualiza o banco de dados ao iniciar
try:
    # Garante que as variáveis estejam configuradas antes de atualizar o banco
    configurar_variaveis_drive()
    db.atualizar_banco()
finally:
    db.fechar_conexao()

st.sidebar.title("📁 Menu")

# Define as opções do menu baseado no tipo de usuário
opcoes_menu = [
    "🏠 Principal",
    "👤 Cadastro de Usuário",
    "👥 Lista de Usuários",
    "👷 Cadastro de Funcionário",
    "📋 Lista de Funcionários",
    "🏢 Cadastro de Empresa",
    "📁 Lista de Empresas",
    "📝 Cadastro de Contrato",
    "📑 Lista de Contratos",
    "🏬 Cadastro de Unidade",
    "📍 Lista de Unidades",
    "🛠️ Cadastro de Serviço",
    "🔧 Lista de Serviços",
    "👷‍♂️ Serviços (OPE/Admin)",
    "🗺️ Unidades no Mapa"
]

# Adiciona opções apenas para admin
if verificar_permissao_admin():
    opcoes_menu.extend([
        "📂 Navegar Pastas (Admin)",
        "💾 Backup de Dados (Admin)"
    ])

tela = st.sidebar.selectbox("Escolha a tela:", opcoes_menu)

st.sidebar.markdown("---")
st.sidebar.markdown(f"👤 Usuário logado: `{st.session_state.get('usuario', 'Admin')}`")
st.sidebar.markdown(f"👑 Tipo: `{st.session_state.get('tipo_usuario', '')}`")
if st.sidebar.button("🚪 Sair"):
    logout()
    st.rerun()

# ────── Roteador de telas ──────
if tela == "🏠 Principal":
    from frontend.Screens.Screen_Principal import exibir_tela_principal
    exibir_tela_principal()
elif tela == "👤 Cadastro de Usuário":
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()
    from frontend.Screens.Screen_CadastroUsuario import exibir_tela_cadastro_usuario
    exibir_tela_cadastro_usuario()
elif tela == "👥 Lista de Usuários":
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()
    from frontend.Screens.Screen_ListarUsuario import exibir_tela_listar_usuarios
    exibir_tela_listar_usuarios()
elif tela == "👷 Cadastro de Funcionário":
    from frontend.Screens.Screen_CadastroFuncionario import exibir_tela_cadastro_funcionario
    exibir_tela_cadastro_funcionario()
elif tela == "📋 Lista de Funcionários":
    from frontend.Screens.Screen_ListarFuncionario import exibir_tela_listar_funcionarios
    exibir_tela_listar_funcionarios()
elif tela == "🏢 Cadastro de Empresa":
    from frontend.Screens.Screen_CadastroEmpresa import exibir_tela_cadastro_empresa
    exibir_tela_cadastro_empresa()
elif tela == "📁 Lista de Empresas":
    from frontend.Screens.Screen_ListarEmpresa import exibir_tela_listar_empresas
    exibir_tela_listar_empresas()
elif tela == "📝 Cadastro de Contrato":
    from frontend.Screens.Screen_CadastroContrato import exibir_tela_cadastro_contrato
    exibir_tela_cadastro_contrato()
elif tela == "📑 Lista de Contratos":
    from frontend.Screens.Screen_ListarContrato import exibir_tela_listar_contratos
    exibir_tela_listar_contratos()
elif tela == "🏬 Cadastro de Unidade":
    from frontend.Screens.Screen_CadastroUnidade import exibir_tela_cadastro_unidade
    exibir_tela_cadastro_unidade()
elif tela == "📍 Lista de Unidades":
    from frontend.Screens.Screen_ListarUnidade import exibir_tela_listar_unidades
    exibir_tela_listar_unidades()
elif tela == "🛠️ Cadastro de Serviço":
    from frontend.Screens.Screen_CadastroServico import exibir_tela_cadastro_servico
    exibir_tela_cadastro_servico()
elif tela == "🔧 Lista de Serviços":
    from frontend.Screens.Screen_ListarServico import exibir_tela_listar_servicos
    exibir_tela_listar_servicos()
elif tela == "👷‍♂️ Serviços (OPE/Admin)":
    from frontend.Screens.Screen_ServicosOPE import exibir_tela_servicos_ope
    exibir_tela_servicos_ope()
elif tela == "📂 Navegar Pastas (Admin)":
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()
    from frontend.Screens.Screen_GridPastas import exibir_tela_grid_pastas
    exibir_tela_grid_pastas()
elif tela == "💾 Backup de Dados (Admin)":
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()
    from frontend.Screens.Screen_Backup import exibir_tela_backup
    exibir_tela_backup()
elif tela == "🗺️ Unidades no Mapa":
    from frontend.Screens.Screen_viewmaps import exibir_tela_viewmaps
    exibir_tela_viewmaps()
