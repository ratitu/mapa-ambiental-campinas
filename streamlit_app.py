import streamlit as st
import ee
import folium
import logging
import json
from streamlit.components.v1 import html

# ---------------------------
# Configuração
# ---------------------------
st.set_page_config(layout="wide")
logging.basicConfig(level=logging.INFO)

# ---------------------------
# Inicializar GEE
# ---------------------------
@st.cache_resource
def init_gee():
    creds_dict = st.secrets["ee"]

    credentials = ee.ServiceAccountCredentials(
        creds_dict["client_email"],
        key_data=creds_dict("private_key")
    )

    ee.Initialize(credentials, project="ee-passeionamatamapas")

init_gee()
# ---------------------------
# Função (igual à sua)
# ---------------------------
def get_tile_url(asset_id, palette, is_point=False):
    try:
        fc = ee.FeatureCollection(asset_id)
        count = fc.size().getInfo()
        logging.info(f"{asset_id} -> {count} elementos")

        if is_point:
            image = ee.Image().paint(fc.map(lambda f: f.buffer(15)), 0)
        else:
            image = ee.Image().paint(fc, 0, 2)

        map_id = image.getMapId({'palette': palette})
        return map_id['tile_fetcher'].url_format

    except Exception as e:
        logging.error(f"Erro no asset {asset_id}: {e}")
        return None

# ---------------------------
# Camadas
# ---------------------------
project = "projects/ee-pigee/assets"

layers = {
    "Limite": get_tile_url("projects/ee-rogergodoytest/assets/limite_municipal", "000000"),
    "APA": get_tile_url(f"{project}/UnidadesConservacaoCampinas", "3AF40B"),
    "APP": get_tile_url(f"{project}/areaPreservacaoPermanente", "f1fc07"),
    "Amortecimento": get_tile_url(f"{project}/zonasAmortecimento", "f50618"),
    "Nascentes": get_tile_url(f"{project}/nascentes_campinas", "13f2f9", is_point=True),
    "Hidrografia": get_tile_url(f"{project}/hidrografia_campinas", "031fbb"),
    "HIDS": get_tile_url(f"{project}/hids", "fa9e09"),
    "PIDS": get_tile_url(f"{project}/hids_pids", "d488de")
}

# ---------------------------
# Interface
# ---------------------------
st.title("🌎 Mapa Ambiental - Campinas")

# Sidebar para controle de camadas
st.sidebar.header("Camadas")
selected_layers = []
for name in layers:
    if st.sidebar.checkbox(name, value=True):
        selected_layers.append(name)

# ---------------------------
# Mapa Folium
# ---------------------------
m = folium.Map(location=[-22.9, -47.06], zoom_start=11)

for name in selected_layers:
    url = layers[name]
    if url:
        folium.TileLayer(
            tiles=url,
            attr=name,
            name=name,
            overlay=True
        ).add_to(m)

folium.LayerControl().add_to(m)

# ---------------------------
# Renderizar no Streamlit
# ---------------------------
html(m._repr_html_(), height=600)
