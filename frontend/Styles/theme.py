# frontend/Styles/theme.py

import streamlit as st

# ────── Paleta de Cores Azul Profissional ──────
PRIMARY_COLOR = "#1E3A8A"  # Azul escuro
SECONDARY_COLOR = "#3B82F6"  # Azul vibrante
LIGHT_BLUE = "#DBEAFE"  # Azul claro para fundo
GRAY_LIGHT = "#F3F4F6"
WHITE = "#FFFFFF"
BLACK = "#111827"

# ────── Funções de Estilo ──────

def aplicar_estilo_geral():
    st.markdown(
        f"""
        <style>
            body, html, .reportview-container {{
                background-color: {LIGHT_BLUE};
                color: {BLACK};
                font-family: 'Segoe UI', sans-serif;
            }}

            .stButton > button {{
                background-color: {PRIMARY_COLOR};
                color: white;
                padding: 0.5rem 1.2rem;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                transition: background-color 0.3s ease;
            }}

            .stButton > button:hover {{
                background-color: {SECONDARY_COLOR};
                color: white;
            }}

            .stTextInput > div > input, .stTextArea > div > textarea {{
                background-color: {WHITE};
                color: {BLACK};
                border: 1px solid {SECONDARY_COLOR};
                border-radius: 6px;
                padding: 0.4rem;
            }}

            .stSelectbox > div > div {{
                background-color: {WHITE};
                border: 1px solid {SECONDARY_COLOR};
                border-radius: 6px;
            }}

            .stDataFrame, .stTable {{
                border: 1px solid {PRIMARY_COLOR};
                border-radius: 6px;
                background-color: {WHITE};
            }}
        </style>
        """,
        unsafe_allow_html=True
    )
