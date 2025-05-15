# frontend/Screens/Screen_ViewMaps.py
# -----------------------------------------------------------------------------
#  Visualização de Unidades no Mapa com Rotas Válidas
#  • Usa API de roteamento OSRM para caminhos reais entre pontos
#  • Exibe distância de cada segmento ao passar o mouse
#  • ScatterplotLayer e PathLayer via GeoJSON
#  • Placeholder para evitar mapas duplicados
#  • Resumo de métricas e download de CSV
# -----------------------------------------------------------------------------

from __future__ import annotations

import streamlit as st
import pandas as pd
import pydeck as pdk
import requests
import math

from Models import model_contrato, model_unidade

OSRM_URL = "http://router.project-osrm.org/route/v1/driving"

# -----------------------------------------------------------------------------
# Funções auxiliares
# -----------------------------------------------------------------------------

def fetch_route(lat1: float, lon1: float, lat2: float, lon2: float) -> dict:
    """
    Consulta OSRM e retorna GeoJSON LineString com propriedade 'distance_km'.
    """
    coords = f"{lon1},{lat1};{lon2},{lat2}"
    params = {"overview": "full", "geometries": "geojson", "annotations": "false"}
    resp = requests.get(f"{OSRM_URL}/{coords}", params=params, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    route = data["routes"][0]
    distance_km = round(route["distance"] / 1000, 2)
    geometry = route["geometry"]  # GeoJSON LineString: {'coordinates': [...], 'type': 'LineString'}
    # Adiciona property
    feature = {"type": "Feature", "properties": {"distance_km": distance_km}, "geometry": geometry}
    return feature

# -----------------------------------------------------------------------------
# Tela principal
# -----------------------------------------------------------------------------

def exibir_tela_viewmaps() -> None:
    st.title("🗺️ Visualização de Unidades no Mapa")
    st.markdown(
        "Selecione um contrato para ver rotas reais entre as unidades. "
        "A localização deve estar no formato '-9.787930, -36.094997'."
    )

    # Seleção de contrato
    contratos = model_contrato.listar_contratos()
    if not contratos:
        st.warning("Nenhum contrato cadastrado.")
        return
    opcoes = {f"{c[0]} - {c[2]}": c[0] for c in contratos}
    contrato_sel = st.selectbox("Contrato", list(opcoes.keys()))
    numero_contrato = opcoes[contrato_sel]

    unidades = model_unidade.listar_unidades(numero_contrato)
    if not unidades:
        st.info("Nenhuma unidade cadastrada para este contrato.")
        return

    # Preparar DataFrame
    registros = []
    for cod, num, nome, estado, cidade, loc in unidades:
        if loc:
            try:
                lat, lon = map(float, loc.split(","))
                registros.append({"Unidade": nome, "Contrato": num, "Estado": estado,
                                  "Cidade": cidade, "lat": lat, "lon": lon})
            except:
                continue
    if not registros:
        st.warning("Nenhuma localização válida encontrada.")
        return
    df = pd.DataFrame(registros)

    # Indicadores
    col1, col2 = st.columns(2)
    col1.metric("Total de Unidades", len(df))
    col2.metric("Estados Distintos", df["Estado"].nunique())

    # Download CSV
    st.download_button(
        "📥 Baixar CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"unidades_{numero_contrato}.csv",
        mime="text/csv"
    )

    # Calcular centro e zoom
    lat_min, lat_max = df["lat"].min(), df["lat"].max()
    lon_min, lon_max = df["lon"].min(), df["lon"].max()
    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2
    if len(df) == 1:
        zoom = 12
    else:
        spread = max(lat_max - lat_min, lon_max - lon_min)
        zoom = min(12, max(3, int(8 - spread * 20)))

    view = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom)

    # Construir rota via OSRM
    features = []
    coords = df[["lat","lon"]].values.tolist()
    # Ordena por Nearest Neighbor
    unvisited = set(range(len(coords)))
    order = [unvisited.pop()]
    while unvisited:
        last = order[-1]
        next_idx = min(unvisited, key=lambda i: math.hypot(coords[i][0]-coords[last][0], coords[i][1]-coords[last][1]))
        order.append(next_idx)
        unvisited.remove(next_idx)
    # Buscar segmentos
    for i in range(len(order)-1):
        i1, i2 = order[i], order[i+1]
        f = fetch_route(coords[i1][0], coords[i1][1], coords[i2][0], coords[i2][1])
        features.append(f)
    geojson = {"type":"FeatureCollection","features":features}

    # Scatter layer
    scatter = pdk.Layer(
        "ScatterplotLayer", df,
        get_position=["lon","lat"], get_radius=200, get_fill_color=[255,140,0,200], pickable=True
    )
    # GeoJSON layer para rotas
    route_layer = pdk.Layer(
        "GeoJsonLayer", geojson,
        pickable=True, stroked=True, filled=False,
        get_line_color=[0,0,255], get_line_width=4,
        get_line_dash=[10, 5],
        auto_highlight=True,
        highlight_color=[255,0,0,100],
    )
    # Tooltip customizado para distâncias
    tooltip = {"html": "<b>Distância (km):</b> {feature.properties.distance_km}",
               "style": {"backgroundColor":"#FFF","color":"#000"}}

    placeholder = st.empty()
    deck = pdk.Deck(layers=[scatter, route_layer], initial_view_state=view, tooltip=tooltip)
    placeholder.pydeck_chart(deck)

    # Botão recenter
    if st.button("🔄 Recentrar Mapa"):
        placeholder.pydeck_chart(deck)

    # Tabela
    st.subheader("Detalhes das Unidades")
    st.dataframe(df, use_container_width=True)
