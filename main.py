# main_app.py

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv
from backend.Database.db_gestaodecontratos import atualizar_banco, fechar_conexao
import atexit
from Database import db_gestaodecontratos as db

# ────── Ajusta sys.path para importar os módulos corretamente ──────
ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))  # backend
sys.path.append(str(ROOT / "frontend"))  # frontend
sys.path.append(str(ROOT / "frontend" / "Styles"))  # estilos

# ────── Carrega variáveis de ambiente ──────
load_dotenv()

# ────── Controle de autenticação ──────
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    from frontend.Screens.Screen_Login import exibir_login
    exibir_login()
    st.stop()

# ────── Tela principal com navegação ──────
from frontend.Styles.theme import aplicar_estilo_geral
aplicar_estilo_geral()

# Atualiza o banco de dados ao iniciar
try:
    db.atualizar_banco()
finally:
    db.fechar_conexao()

st.sidebar.title("📁 Menu")

tela = st.sidebar.selectbox("Escolha a tela:", [
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
    "📂 Navegar Pastas (Admin)",
    "💾 Backup de Dados (Admin)"
])

st.sidebar.markdown("---")
st.sidebar.markdown(f"👤 Usuário logado: `{st.session_state['usuario']}`")
if st.sidebar.button("🚪 Sair"):
    st.session_state.clear()
    st.rerun()

# ────── Roteador de telas ──────
if tela == "🏠 Principal":
    from frontend.Screens.Screen_Principal import exibir_tela_principal
    exibir_tela_principal()

elif tela == "👤 Cadastro de Usuário":
    from frontend.Screens.Screen_CadastroUsuario import exibir_tela_cadastro_usuario
    exibir_tela_cadastro_usuario()

elif tela == "👥 Lista de Usuários":
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
    from frontend.Screens.Screen_GridPastas import exibir_tela_grid_pastas
    exibir_tela_grid_pastas()

elif tela == "💾 Backup de Dados (Admin)":
    from frontend.Screens.Screen_Backup import exibir_tela_backup
    exibir_tela_backup()
