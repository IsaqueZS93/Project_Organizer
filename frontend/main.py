import streamlit as st
from pathlib import Path
import sys
from Screens.Screen_Login import exibir_tela_login
from Screens.Screen_Empresas import exibir_tela_empresas
from Screens.Screen_Contratos import exibir_tela_contratos
from Screens.Screen_Unidades import exibir_tela_unidades
from Screens.Screen_Servicos import exibir_tela_servicos
from Screens.Screen_ServicosOPE import exibir_tela_servicos_ope
from Screens.Screen_Usuarios import exibir_tela_usuarios
from Screens.Screen_GridPastas import exibir_tela_grid_pastas
from Screens.Screen_Backup import exibir_tela_backup

# Configuração da página
st.set_page_config(
    page_title="Sistema de Gestão",
    page_icon="🏢",
    layout="wide"
)

# Inicializa variáveis de sessão
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None
if "tipo" not in st.session_state:
    st.session_state["tipo"] = None
if "pagina" not in st.session_state:
    st.session_state["pagina"] = "empresas"

# Menu lateral
with st.sidebar:
    st.title("🏢 Sistema de Gestão")
    
    if st.session_state["usuario"]:
        st.markdown(f"### 👤 {st.session_state['usuario']}")
        st.markdown(f"Tipo: {'Administrador' if st.session_state['tipo'] == 'admin' else 'OPE'}")
        
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state["usuario"] = None
            st.session_state["tipo"] = None
            st.session_state["pagina"] = "empresas"
            st.rerun()
        
        st.markdown("---")
        
        # Menu de navegação
        if st.session_state["tipo"] == "admin":
            # Menu principal
            st.markdown("#### 📋 Menu Principal")
            
            # Opções do menu
            opcoes_menu = {
                "🏢 Empresas": "empresas",
                "📄 Contratos": "contratos",
                "🏭 Unidades": "unidades",
                "🔧 Serviços": "servicos",
                "👥 Usuários": "usuarios",
                "📁 Pastas": "pastas",
                "💾 Backup": "backup"
            }
            
            # Selectbox para navegação
            pagina_selecionada = st.selectbox(
                "Selecione uma opção:",
                options=list(opcoes_menu.keys()),
                index=list(opcoes_menu.keys()).index(st.session_state["pagina"]),
                format_func=lambda x: x
            )
            
            # Atualiza a página selecionada
            if pagina_selecionada:
                st.session_state["pagina"] = opcoes_menu[pagina_selecionada]
                st.rerun()
        
        else:  # Tipo OPE
            if st.button("🔧 Serviços", use_container_width=True):
                st.session_state["pagina"] = "servicos_ope"
                st.rerun()

# Exibe a página apropriada
if not st.session_state["usuario"]:
    exibir_tela_login()
else:
    pagina = st.session_state.get("pagina", "servicos" if st.session_state["tipo"] == "ope" else "empresas")
    
    if pagina == "empresas":
        exibir_tela_empresas()
    elif pagina == "contratos":
        exibir_tela_contratos()
    elif pagina == "unidades":
        exibir_tela_unidades()
    elif pagina == "servicos":
        exibir_tela_servicos()
    elif pagina == "servicos_ope":
        exibir_tela_servicos_ope()
    elif pagina == "usuarios":
        exibir_tela_usuarios()
    elif pagina == "pastas":
        exibir_tela_grid_pastas()
    elif pagina == "backup":
        exibir_tela_backup() 