# frontend/Screens/Screen_Backup.py

import streamlit as st
from Styles.theme import aplicar_estilo_geral
from pathlib import Path
import sys
import json
import sqlite3
import datetime
import os
from tempfile import gettempdir
from frontend.Utils.auth import verificar_permissao_admin
import logging

# Importa models
sys.path.append(str(Path(__file__).resolve().parents[2]))
from Models import model_empresa, model_contrato, model_unidade, model_servico, model_usuario
from Database import db_gestaodecontratos as db
from Services import Service_googledrive as gdrive

logger = logging.getLogger(__name__)

def obter_banco_temp():
    """Baixa o banco de dados do Google Drive para um arquivo temporário"""
    try:
        # ID do arquivo do banco no Google Drive
        banco_id = st.session_state.get("GDRIVE_DATABASE_FOLDER_ID")
        if not banco_id:
            st.error("❌ ID do banco de dados não encontrado. Por favor, faça login novamente.")
            return None

        # Lista arquivos na pasta
        arquivos = gdrive.list_files_in_folder(banco_id)
        if not arquivos:
            st.error("❌ Nenhum arquivo encontrado na pasta do banco de dados")
            return None

        # Procura o arquivo do banco de dados
        banco_file = None
        for arquivo in arquivos:
            if arquivo['name'].endswith('.db'):
                banco_file = arquivo
                break

        if not banco_file:
            st.error("❌ Arquivo do banco de dados não encontrado na pasta")
            return None

        # Cria arquivo temporário
        temp_file = Path(gettempdir()) / "database.db"
        
        # Baixa o banco do Google Drive
        if gdrive.download_file(banco_file['id'], str(temp_file)):
            # Verifica se o arquivo foi baixado corretamente
            if temp_file.exists() and temp_file.stat().st_size > 0:
                return temp_file
            else:
                st.error("❌ Erro: Arquivo baixado está vazio ou não existe")
                return None
        else:
            st.error("❌ Erro ao baixar banco de dados do Google Drive")
            return None
            
    except Exception as e:
        st.error(f"❌ Erro ao obter banco de dados: {str(e)}")
        return None

def exportar_dados_json():
    """Exporta todos os dados do banco para um arquivo JSON"""
    try:
        # Obtém o banco de dados do Google Drive
        temp_file = obter_banco_temp()
        if not temp_file:
            return None

        # Verifica se o arquivo existe e tem conteúdo
        if not temp_file.exists():
            st.error("❌ Erro: Arquivo temporário não foi criado")
            return None
            
        if temp_file.stat().st_size == 0:
            st.error("❌ Erro: Arquivo temporário está vazio")
            return None

        # Conecta ao banco de dados temporário
        conn = sqlite3.connect(str(temp_file))
        cursor = conn.cursor()

        # Obtém dados de todas as tabelas
        dados = {}

        try:
            # Empresas
            cursor.execute("SELECT * FROM empresas")
            colunas = [description[0] for description in cursor.description]
            empresas = cursor.fetchall()
            dados["empresas"] = [dict(zip(colunas, empresa)) for empresa in empresas]

            # Contratos
            cursor.execute("SELECT * FROM contratos")
            colunas = [description[0] for description in cursor.description]
            contratos = cursor.fetchall()
            dados["contratos"] = [dict(zip(colunas, contrato)) for contrato in contratos]

            # Unidades
            cursor.execute("SELECT * FROM unidades")
            colunas = [description[0] for description in cursor.description]
            unidades = cursor.fetchall()
            dados["unidades"] = [dict(zip(colunas, unidade)) for unidade in unidades]

            # Serviços
            cursor.execute("SELECT * FROM servicos")
            colunas = [description[0] for description in cursor.description]
            servicos = cursor.fetchall()
            dados["servicos"] = [dict(zip(colunas, servico)) for servico in servicos]

            # Usuários (excluindo senhas)
            cursor.execute("SELECT usuario, nome, tipo FROM usuarios")
            colunas = [description[0] for description in cursor.description]
            usuarios = cursor.fetchall()
            dados["usuarios"] = [dict(zip(colunas, usuario)) for usuario in usuarios]

            # Funcionários
            cursor.execute("SELECT * FROM funcionarios")
            colunas = [description[0] for description in cursor.description]
            funcionarios = cursor.fetchall()
            dados["funcionarios"] = [dict(zip(colunas, funcionario)) for funcionario in funcionarios]

        except sqlite3.Error as e:
            st.error(f"❌ Erro ao ler dados do banco: {str(e)}")
            return None
        finally:
            # Fecha a conexão
            conn.close()

        # Remove o arquivo temporário
        try:
            temp_file.unlink()
        except Exception as e:
            logger.warning(f"Erro ao remover arquivo temporário: {e}")

        # Converte para JSON
        return json.dumps(dados, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"❌ Erro ao exportar dados: {str(e)}")
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except:
                pass
        return None

def criar_backup_banco():
    """Cria uma cópia do banco de dados baixando do Google Drive"""
    try:
        # Obtém o banco de dados do Google Drive
        temp_file = obter_banco_temp()
        if not temp_file:
            return None

        # Verifica se o arquivo existe e tem conteúdo
        if not temp_file.exists():
            st.error("❌ Erro: Arquivo temporário não foi criado")
            return None
            
        if temp_file.stat().st_size == 0:
            st.error("❌ Erro: Arquivo temporário está vazio")
            return None

        # Lê o conteúdo do banco
        with open(temp_file, 'rb') as f:
            db_content = f.read()
        
        # Remove o arquivo temporário
        try:
            temp_file.unlink()
        except Exception as e:
            logger.warning(f"Erro ao remover arquivo temporário: {e}")
        
        return db_content
            
    except Exception as e:
        st.error(f"❌ Erro ao criar backup: {str(e)}")
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except:
                pass
        return None

def exibir_tela_backup():
    """Exibe a tela de backup de dados"""
    if not verificar_permissao_admin():
        st.error("Acesso negado. Esta tela é restrita para administradores.")
        st.stop()
        
    st.title("💾 Backup de Dados")
    st.write("Esta tela permite realizar backup dos dados do sistema.")
    
    # Garante que as variáveis do Google Drive estejam configuradas
    if "GDRIVE_DATABASE_FOLDER_ID" not in st.session_state:
        st.error("❌ Configurações do Google Drive não encontradas. Por favor, faça login novamente.")
        st.stop()

    # Aplica tema
    aplicar_estilo_geral()

    # Data atual para nome dos arquivos
    data_atual = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Backup do banco de dados
    st.markdown("### 📦 Backup do Banco de Dados")
    st.markdown("Faça o download de uma cópia completa do banco de dados do Google Drive.")
    
    if st.button("📥 Baixar Backup do Banco", use_container_width=True):
        with st.spinner("Baixando banco de dados do Google Drive..."):
            db_content = criar_backup_banco()
            if db_content:
                st.download_button(
                    label="Download do Banco de Dados",
                    data=db_content,
                    file_name=f"backup_banco_{data_atual}.db",
                    mime="application/octet-stream",
                    use_container_width=True
                )

    # Exportação dos dados em JSON
    st.markdown("### 📄 Exportar Dados em JSON")
    st.markdown("Faça o download de todos os dados do sistema em formato JSON (exceto senhas de usuários).")
    
    if st.button("📥 Baixar Dados em JSON", use_container_width=True):
        with st.spinner("Exportando dados para JSON..."):
            json_data = exportar_dados_json()
            if json_data:
                st.download_button(
                    label="Download dos Dados em JSON",
                    data=json_data,
                    file_name=f"dados_sistema_{data_atual}.json",
                    mime="application/json",
                    use_container_width=True
                ) 