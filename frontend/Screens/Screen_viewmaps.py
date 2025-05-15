# frontend/Screens/Screen_ViewMaps.py
# -----------------------------------------------------------------------------
#  Visualização de Unidades no Mapa (Streamlit + PyDeck)
#  • Mapa centralizado entre pontos
#  • ScatterplotLayer para marcadores claros
#  • Placeholder para evitar mapas duplicados
#  • Tooltips interativos e botão de recentralização
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
    col3.metric("Latitude Média", round(df["lat"].mean(), 4))

    # ======= Download CSV =======
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Baixar CSV",
        data=csv,
        file_name=f"unidades_{numero_contrato}.csv",
        mime="text/csv"
    )

    # ======= Cálculo de bounding box e view_state =======
    lat_min, lat_max = df["lat"].min(), df["lat"].max()
    lon_min, lon_max = df["lon"].min(), df["lon"].max()
    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2

    if len(df) == 1:
        zoom = 12
    else:
        lat_diff = lat_max - lat_min
        lon_diff = lon_max - lon_min
        spread = max(lat_diff, lon_diff)
        zoom = min(12, max(3, int(8 - spread * 20)))

    initial_view = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom,
        pitch=0,
    )

    # Layer de pontos individuais (Scatterplot)
    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_radius=200,
        get_fill_color=[255, 140, 0, 200],
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

    # Placeholder para o mapa
    map_placeholder = st.empty()
    deck = pdk.Deck(
        layers=[scatter],
        initial_view_state=initial_view,
        tooltip=tooltip,
    )
    map_placeholder.pydeck_chart(deck)

    # ======= Botão Recentrar Mapa =======
    if st.button("🔄 Recentrar Mapa"):
        new_view = pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=zoom,
            pitch=0,
        )
        deck.initial_view_state = new_view
        map_placeholder.pydeck_chart(deck)

    # ======= Tabela interativa =======
    st.subheader("Detalhes das Unidades")
    st.dataframe(df, use_container_width=True)
