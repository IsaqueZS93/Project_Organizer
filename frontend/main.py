# frontend/app.py
# ------------------------------------------------------------------------------
#  Sistema de Gestão – App principal (Streamlit)
#  • Imports tardios para reduzir tempo de carregamento
#  • Navegação sem st.rerun() desnecessário
#  • Estado padronizado em st.session_state
# ------------------------------------------------------------------------------

import streamlit as st
import importlib

# ------------------------------------------------------------------------------
# 1. Configurações básicas da página
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Sistema de Gestão", page_icon="🏢", layout="wide")

# ------------------------------------------------------------------------------
# 2. Estado inicial
# ------------------------------------------------------------------------------
DEFAULTS = {"usuario": None, "tipo": None, "pagina": "empresas"}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

# ------------------------------------------------------------------------------
# 3. Mapeamento de telas (módulo, função)
# ------------------------------------------------------------------------------
TELAS = {
    "login":        ("Screens.Screen_Login",        "exibir_tela_login"),
    "empresas":     ("Screens.Screen_Empresas",     "exibir_tela_empresas"),
    "contratos":    ("Screens.Screen_Contratos",    "exibir_tela_contratos"),
    "unidades":     ("Screens.Screen_Unidades",     "exibir_tela_unidades"),
    "servicos":     ("Screens.Screen_Servicos",     "exibir_tela_servicos"),
    "servicos_ope": ("Screens.Screen_ServicosOPE",  "exibir_tela_servicos_ope"),
    "usuarios":     ("Screens.Screen_Usuarios",     "exibir_tela_usuarios"),
    "pastas":       ("Screens.Screen_GridPastas",   "exibir_tela_grid_pastas"),
    "backup":       ("Screens.Screen_Backup",       "exibir_tela_backup"),
}

# ------------------------------------------------------------------------------
# 4. Função auxiliar de carregamento tardio
# ------------------------------------------------------------------------------

def carregar_tela(nome: str):
    """Importa o módulo e executa a função da tela solicitada."""
    modulo, funcao = TELAS[nome]
    mod = importlib.import_module(modulo)
    getattr(mod, funcao)()

# ------------------------------------------------------------------------------
# 5. Construção do menu lateral
# ------------------------------------------------------------------------------
with st.sidebar:
    st.title("🏢 Sistema de Gestão")

    # Usuário autenticado -------------------------------------------------------
    if st.session_state["usuario"]:
        st.markdown(f"### 👤 {st.session_state['usuario']}")
        tipo_legivel = "Administrador" if st.session_state["tipo"] == "admin" else "OPE"
        st.markdown(f"Tipo: {tipo_legivel}")

        # Botão de logout -------------------------------------------------------
        if st.button("🚪 Sair", use_container_width=True):
            for key in ["usuario", "tipo", "pagina"]:
                st.session_state.pop(key, None)
            st.experimental_rerun()  # força redraw imediato

        st.markdown("---")

        # Navegação -------------------------------------------------------------
        if st.session_state["tipo"] == "admin":
            st.markdown("#### 📋 Menu Principal")

            OP_MENU = {
                "🏢 Empresas":   "empresas",
                "📄 Contratos":  "contratos",
                "🏭 Unidades":   "unidades",
                "🔧 Serviços":   "servicos",
                "👥 Usuários":   "usuarios",
                "📁 Pastas":     "pastas",
                "💾 Backup":     "backup",
            }

            # Callback para mudar a página -------------------------------------
            def _mudar_pagina():
                escolha = st.session_state["menu_admin"]
                st.session_state["pagina"] = OP_MENU[escolha]

            st.selectbox(
                label="Selecione uma opção:",
                options=list(OP_MENU.keys()),
                index=list(OP_MENU.values()).index(st.session_state["pagina"]),
                key="menu_admin",
                on_change=_mudar_pagina,
            )
        else:
            # Tipo OPE ----------------------------------------------------------
            if st.button("🔧 Serviços", use_container_width=True):
                st.session_state["pagina"] = "servicos_ope"

# ------------------------------------------------------------------------------
# 6. Renderização da tela principal
# ------------------------------------------------------------------------------
if not st.session_state["usuario"]:
    carregar_tela("login")
else:
    pagina = st.session_state.get("pagina", "empresas")
    carregar_tela(pagina)
