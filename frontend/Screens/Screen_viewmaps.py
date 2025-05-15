# frontend/Screens/Screen_ViewMaps.py
# -----------------------------------------------------------------------------
#  Visualização de Unidades no Mapa (Streamlit + PyDeck)
#  • Mapa com rota otimizada (Nearest Neighbor)
#  • ScatterplotLayer para marcadores claros
#  • PathLayer para exibir a rota
#  • Placeholder para evitar mapas duplicados
#  • Tooltips interativos e botão de recentralização
#  • Resumo de métricas e download de CSV
# -----------------------------------------------------------------------------

from __future__ import annotations

import streamlit as st
import pandas as pd
import pydeck as pdk
import math

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
    col1, col2 = st.columns(2)
    col1.metric("Total de Unidades", len(df))
    col2.metric("Estados Distintos", df["Estado"].nunique())

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

    # Zoom dinamico
    if len(df) == 1:
        zoom = 12
    else:
        spread = max(lat_max - lat_min, lon_max - lon_min)
        zoom = min(12, max(3, int(8 - spread * 20)))

    initial_view = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom,
        pitch=0,
    )

    # ======= Route optimization: Nearest Neighbor =======
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    coords = df[["lat", "lon"]].values.tolist()
    visited = [0]
    route = [coords[0]]
    to_visit = set(range(1, len(coords)))
    while to_visit:
        last = visited[-1]
        nearest = min(
            to_visit,
            key=lambda i: haversine(coords[last][0], coords[last][1], coords[i][0], coords[i][1])
        )
        visited.append(nearest)
        route.append(coords[nearest])
        to_visit.remove(nearest)

    # Converter rota para formato [lon, lat]
    path = [(lon, lat) for lat, lon in route]
    path_data = [{"path": path}]

    # Scatter layer para pontos
    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_radius=200,
        get_fill_color=[255, 140, 0, 200],
        pickable=True,
    )

    # PathLayer para rota
    route_layer = pdk.Layer(
        "PathLayer",
        data=path_data,
        get_path="path",
        get_width=4,
        get_color=[0, 0, 255],
        width_min_pixels=2,
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
        layers=[scatter, route_layer],
        initial_view_state=initial_view,
        tooltip=tooltip,
    )
    map_placeholder.pydeck_chart(deck)

    # ======= Botão Recentrar Mapa =======
    if st.button("🔄 Recentrar Mapa"):
        map_placeholder.pydeck_chart(
            pdk.Deck(layers=[scatter, route_layer], initial_view_state=initial_view, tooltip=tooltip)
        )

    # ======= Tabela interativa =======
    st.subheader("Detalhes das Unidades")
    st.dataframe(df, use_container_width=True)
