import streamlit as st
import ee
import folium
import logging
from streamlit_folium import st_folium

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(layout="wide")
logging.basicConfig(level=logging.INFO)

# ---------------------------
# INIT GEE (FIXED)
# ---------------------------
@st.cache_resource
def init_gee():
    creds = st.secrets["ee"]

    private_key = creds["private_key"].replace("\\n", "\n")

    credentials = ee.ServiceAccountCredentials(
        creds["client_email"],
        key_data=private_key
    )

    ee.Initialize(credentials, project=creds["project_id"])

init_gee()

# ---------------------------
# TILE FUNCTION (CACHE)
# ---------------------------
@st.cache_data
def get_tile_url(asset_id, palette, is_point=False):
    try:
        fc = ee.FeatureCollection(asset_id)

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
# BASEMAPS
# ---------------------------
BASEMAPS = {
    "OpenStreetMap": "OpenStreetMap",
    "Satélite (Esri)": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "CartoDB Positron": "CartoDB positron",
    "CartoDB Dark": "CartoDB dark_matter",
}

# ---------------------------
# LAYERS
# ---------------------------
project = "projects/ee-pigee/assets"

layers = {
    "Limite": {"url": get_tile_url("projects/ee-rogergodoytest/assets/limite_municipal", "000000"), "color": "#000000"},
    "APA": {"url": get_tile_url(f"{project}/UnidadesConservacaoCampinas", "3AF40B"), "color": "#3AF40B"},
    "APP": {"url": get_tile_url(f"{project}/areaPreservacaoPermanente", "f1fc07"), "color": "#f1fc07"},
    "Amortecimento": {"url": get_tile_url(f"{project}/zonasAmortecimento", "f50618"), "color": "#f50618"},
    "Nascentes": {"url": get_tile_url(f"{project}/nascentes_campinas", "13f2f9", is_point=True), "color": "#13f2f9"},
    "Hidrografia": {"url": get_tile_url(f"{project}/hidrografia_campinas", "031fbb"), "color": "#031fbb"},
    "HIDS": {"url": get_tile_url(f"{project}/hids", "fa9e09"), "color": "#fa9e09"},
    "PIDS": {"url": get_tile_url(f"{project}/hids_pids", "d488de"), "color": "#d488de"},
}

# ---------------------------
# UI
# ---------------------------
st.title("🌎 Mapa Ambiental - Campinas")

# Sidebar
st.sidebar.header("🗺️ Configurações")

basemap_choice = st.sidebar.selectbox("Mapa base", list(BASEMAPS.keys()))

selected_layers = [
    name for name in layers
    if st.sidebar.checkbox(name, value=True)
]

# ---------------------------
# MAPA
# ---------------------------
m = folium.Map(
    location=[-22.9, -47.06],
    zoom_start=11,
    tiles=None
)

# Basemap
basemap = BASEMAPS[basemap_choice]

if basemap.startswith("http"):
    folium.TileLayer(
        tiles=basemap,
        attr=basemap_choice,
        name="Base",
        overlay=False
    ).add_to(m)
else:
    folium.TileLayer(basemap, name="Base").add_to(m)

# Camadas
for name in selected_layers:
    url = layers[name]["url"]
    if url:
        folium.TileLayer(
            tiles=url,
            attr=name,
            name=name,
            overlay=True
        ).add_to(m)

# LEGENDA
from branca.element import Template, MacroElement

def add_legend(map_obj, selected_layers, layers_dict):
    legend_items = ""

    for layer in selected_layers:
        color = layers_dict[layer]["color"]
        legend_items += f"""
        <li><span style='background:{color}'></span>{layer}</li>
        """

    template = f"""
    {{% macro html(this, kwargs) %}}

    <div style="
        position: fixed; 
        bottom: 40px; left: 40px; width: 220px;
        background-color: black;
        border:2px solid grey;
        z-index:9999;
        font-size:14px;
        padding: 10px;
        border-radius: 8px;
        ">
        
        <b>Legenda</b>
        <ul style="list-style: none; padding: 0;">
            {legend_items}
        </ul>
    </div>

    <style>
        li {{
            margin-bottom: 5px;
        }}
        span {{
            display:inline-block;
            width: 12px;
            height: 12px;
            margin-right: 8px;
        }}
    </style>

    {{% endmacro %}}
    """

    macro = MacroElement()
    macro._template = Template(template)
    map_obj.get_root().add_child(macro)

folium.LayerControl().add_to(m)
add_legend(m, selected_layers, layers)

# Render (FIXED)
st_folium(m, width=1200, height=600)

# ---------------------------
# EXPORT GEO TIFF
# ---------------------------
st.sidebar.header("⬇️ Exportar")

if st.sidebar.button("Exportar Hidrografia GeoTIFF"):
    try:
        fc = ee.FeatureCollection(f"{project}/hidrografia_campinas")
        image = ee.Image().paint(fc, 1)

        url = image.getDownloadURL({
            'scale': 30,
            'crs': 'EPSG:4326',
            'format': 'GeoTIFF'
        })

        st.sidebar.success("Link gerado!")
        st.sidebar.markdown(f"[Download GeoTIFF]({url})")

    except Exception as e:
        st.sidebar.error(f"Erro: {e}")
