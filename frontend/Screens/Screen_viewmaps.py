# frontend/Screens/Screen_ViewMaps.py
# -----------------------------------------------------------------------------
#  Visualização de Unidades no Mapa com Rotas Válidas (PyDeck + OSRM)
#  • Calcula uma rota única entre todas as unidades na ordem otimizada
#  • Chama OSRM uma única vez para todos os waypoints
#  • Fallback para linha reta se OSRM falhar
#  • Exibe distância total da rota
#  • ScatterplotLayer e GeoJsonLayer para mapa
#  • Resumo de métricas e download de CSV
# -----------------------------------------------------------------------------

from __future__ import annotations

import streamlit as st
import pandas as pd
import pydeck as pdk
import requests
from requests.adapters import HTTPAdapter, Retry
import math

from Models import model_contrato, model_unidade

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

# -----------------------------------------------------------------------------
# Funções auxiliares
# -----------------------------------------------------------------------------

def get_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500,502,503,504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def fetch_full_route(coords: list[tuple[float,float]]) -> dict:
    """
    Chama OSRM para uma rota entre todos os waypoints (lon,lat semicolon separados).
    Fallback para linha reta aproximada se falhar.
    Retorna GeoJSON FeatureCollection com um único Feature contendo a rota.
    """
    # Monta string de coords: "lon,lat;lon,lat;..."
    coord_str = ";".join(f"{lon},{lat}" for lat, lon in coords)
    params = {"overview": "full", "geometries": "geojson"}
    session = get_session()
    try:
        resp = session.get(f"{OSRM_URL}/{coord_str}", params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        route = data["routes"][0]
        geometry = route.get("geometry", {"type":"LineString","coordinates":[(lon,lat) for lat,lon in coords]})
        distance_km = round(route.get("distance", 0)/1000, 2)
    except Exception:
        # Fallback: linha reta conectando todos pontos sequencialmente
        geometry = {"type":"LineString","coordinates":[(lon,lat) for lat,lon in coords]}
        distance_km = 0
        for i in range(len(coords)-1):
            distance_km += haversine(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
        distance_km = round(distance_km, 2)

    feature = {"type":"Feature","properties":{"distance_km":distance_km},"geometry":geometry}
    return {"type":"FeatureCollection","features":[feature]}

# -----------------------------------------------------------------------------
# Tela principal
# -----------------------------------------------------------------------------

def exibir_tela_viewmaps() -> None:
    st.title("🗺️ Visualização de Unidades no Mapa")
    st.markdown(
        "Selecione um contrato para visualizar as unidades no mapa. "
        "As coordenadas devem estar no formato '-9.787930, -36.094997'."
    )

    contratos = model_contrato.listar_contratos()
    if not contratos:
        st.warning("Nenhum contrato cadastrado.")
        return
    opcoes = {f"{c[0]} - {c[2]}": c[0] for c in contratos}
    sel = st.selectbox("Contrato", list(opcoes.keys()))
    numero = opcoes[sel]

    unidades = model_unidade.listar_unidades(numero)
    if not unidades:
        st.info("Nenhuma unidade para este contrato.")
        return

    # Prepara DataFrame
    dados = []
    for cod, num, nome, estado, cidade, loc in unidades:
        if loc:
            try:
                lat, lon = map(float, loc.split(","))
                dados.append({"Unidade":nome, "Contrato":num, "Estado":estado, "Cidade":cidade, "lat":lat, "lon":lon})
            except:
                continue
    if not dados:
        st.warning("Nenhuma localização válida.")
        return
    df = pd.DataFrame(dados)

    # Indicadores
    col1, col2 = st.columns(2)
    col1.metric("Total de Unidades", len(df))
    col2.metric("Estados Distintos", df["Estado"].nunique())

    # Download
    st.download_button("📥 Baixar CSV", df.to_csv(index=False).encode(), file_name=f"unidades_{numero}.csv")

    # Ordena rotas pela heurística Nearest Neighbor
    coords = list(zip(df["lat"], df["lon"]))
    unvisited = set(range(len(coords)))
    order = [unvisited.pop()]
    while unvisited:
        last = order[-1]
        next_idx = min(unvisited, key=lambda i: haversine(coords[last][0], coords[last][1], coords[i][0], coords[i][1]))
        order.append(next_idx)
        unvisited.remove(next_idx)
    ordered_coords = [coords[i] for i in order]

    # Busca rota completa
    geojson = fetch_full_route(ordered_coords)

    # Configura mapa
    lat_vals = df["lat"]
    lon_vals = df["lon"]
    center = [(lat_vals.min()+lat_vals.max())/2, (lon_vals.min()+lon_vals.max())/2]
    spread = max(lat_vals.max()-lat_vals.min(), lon_vals.max()-lon_vals.min())
    zoom = 12 if len(df)==1 else min(12, max(3, int(8-spread*20)))
    view = pdk.ViewState(latitude=center[0], longitude=center[1], zoom=zoom)

    scatter = pdk.Layer("ScatterplotLayer", df, get_position=["lon","lat"], get_radius=200, get_fill_color=[255,140,0,200])
    route_layer = pdk.Layer("GeoJsonLayer", geojson, stroked=True, filled=False, get_line_color=[0,0,255], get_line_width=4)

    tooltip = {"html":"<b>Distância total (km):</b> {feature.properties.distance_km}", "style":{"backgroundColor":"#FFF","color":"#000"}}

    placeholder = st.empty()
    deck = pdk.Deck(layers=[scatter,route_layer], initial_view_state=view, tooltip=tooltip)
    placeholder.pydeck_chart(deck)

    if st.button("🔄 Recentrar Mapa"):
        placeholder.pydeck_chart(deck)

    st.subheader("Detalhes das Unidades")
    st.dataframe(df, use_container_width=True)
