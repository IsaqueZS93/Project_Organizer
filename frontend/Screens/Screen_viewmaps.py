# frontend/Screens/Screen_ViewMaps.py
# -----------------------------------------------------------------------------
#  Visualização de Unidades no Mapa (Streamlit + PyDeck)
#  • Mapa customizado com cluster e pontos
#  • Tooltips interativos
#  • Resumo de métricas e download de CSV
# -----------------------------------------------------------------------------

from __future__ import annotations

import streamlit as st
import pandas as pd
import pydeck as pdk

from Models import model_contrato, model_unidade

# -----------------------------------------------------------------------------
# Tela principal
# -----------------------------------------------------------------------------

def exibir_tela_viewmaps() -> None:
    st.title("🗺️ Visualização de Unidades no Mapa")
    st.markdown(
        "Selecione um contrato para visualizar as unidades cadastradas no mapa. "
        "O campo de localização deve estar no formato '-9.787930, -36.094997'."
    )

    # Seleção de contrato
    contratos = model_contrato.listar_contratos()
    if not contratos:
        st.warning("Nenhum contrato cadastrado.")
        return
    opcoes = {f"{c[0]} - {c[2]}": c[0] for c in contratos}
    contrato_sel = st.selectbox("Contrato", list(opcoes.keys()))
    numero_contrato = opcoes[contrato_sel]

    # Listar unidades desse contrato
    unidades = model_unidade.listar_unidades(numero_contrato)
    if not unidades:
        st.info("Nenhuma unidade cadastrada para este contrato.")
        return

    # Montar DataFrame geolocalizado
    dados = []
    for cod, num, nome, estado, cidade, localizacao in unidades:
        if localizacao:
            try:
                lat, lon = map(float, localizacao.split(","))
                dados.append({
                    "Unidade": nome,
                    "Contrato": num,
                    "Estado": estado,
                    "Cidade": cidade,
                    "lat": lat,
                    "lon": lon,
                })
            except Exception:
                continue
    if not dados:
        st.warning("Unidades sem localização válida.")
        return

    df = pd.DataFrame(dados)

    # ======= Indicadores resumidos =======
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Unidades", len(df))
    col2.metric("Estados Distintos", df["Estado"].nunique())
    # Média de latitude (exemplo de indicador adicional)
    col3.metric("Latitude Média", round(df["lat"].mean(), 4))

    # ======= Download CSV =======
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Baixar CSV",
        data=csv,
        file_name=f"unidades_{numero_contrato}.csv",
        mime="text/csv"
    )

    # ======= PyDeck Map =======
    # Cálculo do centro e zoom inicial
    mid_lat = df["lat"].mean()
    mid_lon = df["lon"].mean()
    view_state = pdk.ViewState(
        latitude=mid_lat,
        longitude=mid_lon,
        zoom=7,
        pitch=40,
    )

    # Layer de cluster (HexagonLayer)
    hex_layer = pdk.Layer(
        "HexagonLayer",
        data=df,
        get_position=["lon", "lat"],
        radius=500,
        elevation_scale=50,
        elevation_range=[0, 3000],
        pickable=True,
        extruded=True,
    )

    # Layer de pontos individuais
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_fill_color=[255, 140, 0, 200],
        get_radius=200,
        pickable=True,
    )

    # Tooltip personalizado
    tooltip = {
        "html": (
            "<b>Unidade:</b> {Unidade}<br>"
            "<b>Contrato:</b> {Contrato}<br>"
            "<b>Cidade/Estado:</b> {Cidade}, {Estado}"
        ),
        "style": {"backgroundColor": "#F0F0F0", "color": "#000000"},
    }

    deck = pdk.Deck(
        layers=[hex_layer, scatter_layer],
        initial_view_state=view_state,
        tooltip=tooltip,
    )
    st.pydeck_chart(deck)

    # ======= Zoom to fit =======
    if st.button("🔄 Recentrar Mapa"):
        # Recalcula view_state baseado em bounding box
        lat_min, lat_max = df["lat"].min(), df["lat"].max()
        lon_min, lon_max = df["lon"].min(), df["lon"].max()
        # Centro
        new_center_lat = (lat_min + lat_max) / 2
        new_center_lon = (lon_min + lon_max) / 2
        # Aproximação de zoom com base no spread (muito simplificado)
        lat_diff = lat_max - lat_min
        zoom = max(2, min(12, int(8 - lat_diff * 10)))
        deck.initial_view_state.latitude = new_center_lat
        deck.initial_view_state.longitude = new_center_lon
        deck.initial_view_state.zoom = zoom
        st.pydeck_chart(deck)

    # ======= Tabela interativa =======
    st.subheader("Detalhes das Unidades")
    st.dataframe(df, use_container_width=True)
