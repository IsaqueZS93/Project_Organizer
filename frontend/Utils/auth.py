import streamlit as st
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verificar_permissao_admin() -> bool:
    """Verifica se o usuário atual é administrador"""
    # Verifica se o usuário está autenticado
    if not st.session_state.get("autenticado", False):
        logger.warning("Usuário não está autenticado")
        return False
        
    # Verifica se o tipo de usuário existe na sessão
    if 'tipo_usuario' not in st.session_state:
        logger.warning("Tipo de usuário não encontrado na sessão")
        return False
        
    # Obtém o tipo de usuário e remove espaços em branco
    tipo_usuario = str(st.session_state.tipo_usuario).strip().lower()
    usuario = st.session_state.get("usuario", "Desconhecido")
    
    logger.info(f"Verificando permissão para usuário: {usuario}")
    logger.info(f"Tipo de usuário na sessão: '{tipo_usuario}'")
    
    # Verifica se é admin (case insensitive)
    is_admin = tipo_usuario == "admin"
    logger.info(f"Resultado da verificação: {is_admin}")
    
    return is_admin 