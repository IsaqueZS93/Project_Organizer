import streamlit as st
import pandas as pd
from Models import model_contrato, model_unidade

def exibir_tela_viewmaps():
    st.title("🗺️ Visualização de Unidades no Mapa")
    st.markdown("Selecione um contrato para visualizar as unidades cadastradas no mapa. O campo de localização deve estar preenchido no formato '-9.787930, -36.094997'.")

    # Buscar contratos disponíveis
    contratos = model_contrato.listar_contratos()
    if not contratos:
        st.warning("Nenhum contrato cadastrado.")
        return
    opcoes = {f"{c[0]} - {c[2]}": c[0] for c in contratos}  # Exibe número e empresa
    contrato_sel = st.selectbox("Contrato", list(opcoes.keys()))
    numero_contrato = opcoes[contrato_sel]

    # Buscar unidades do contrato
    unidades = model_unidade.listar_unidades(numero_contrato)
    if not unidades:
        st.info("Nenhuma unidade cadastrada para este contrato.")
        return

    # Montar DataFrame para o mapa
    dados = []
    for u in unidades:
        # u: (cod_unidade, numero_contrato, nome_unidade, estado, cidade, localizacao)
        if u[5]:
            try:
                lat, lon = map(float, u[5].split(","))
                dados.append({
                    "Unidade": u[2],
                    "Estado": u[3],
                    "Cidade": u[4],
                    "Latitude": lat,
                    "Longitude": lon,
                })
            except Exception:
                continue
    if not dados:
        st.warning("Nenhuma unidade deste contrato possui localização válida cadastrada.")
        return
    df = pd.DataFrame(dados)
    st.map(df.rename(columns={"Latitude": "lat", "Longitude": "lon"}))
    st.dataframe(df, use_container_width=True) 