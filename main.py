import pandas as pd
import pgeocode
import plotly.express as px
import streamlit as st

# 1) Toujours en premier
st.set_page_config(layout="wide")
st.title("Carte des cultures agricoles en France")

# --- Chargement du fichier ---
uploaded = st.file_uploader("Télécharger un fichier CSV", type=["csv"])

@st.cache_data
def load_df(file_like):
    # lit le csv (fichier déposé ou chemin local) et prépare les colonnes
    df = pd.read_csv(file_like, sep=";", dtype={"CODE_POSTAL": str}, on_bad_lines="skip", encoding="utf-8")
    req_cols = {"CODE_POSTAL", "TYPO_CULTURE"}
    if not req_cols.issubset(df.columns):
        missing = ", ".join(req_cols - set(df.columns))
        st.error(f"Colonnes manquantes : {missing}")
        st.stop()
    df["CODE_POSTAL"] = df["CODE_POSTAL"].astype(str).str.zfill(5)
    df = df.dropna(subset=["TYPO_CULTURE", "CODE_POSTAL"])
    # géocodage des codes postaux
    nomi = pgeocode.Nominatim("fr")
    geo = nomi.query_postal_code(df["CODE_POSTAL"].tolist())
    df["latitude"] = geo.latitude.values
    df["longitude"] = geo.longitude.values
    df = df.dropna(subset=["latitude", "longitude"])
    return df

if uploaded is not None:
    df = load_df(uploaded)  # <- fichier déposé

else:
    st.stop()

# --- Contrôles UI ---
alpha = st.slider("Opacité des points", 0.0, 1.0, 0.5)

# --- Carte ---
fig = px.scatter_mapbox(
    df, lat="latitude", lon="longitude", color="TYPO_CULTURE",
    hover_name="TYPO_CULTURE", zoom=5, height=600, mapbox_style="open-street-map"
)
fig.update_traces(marker=dict(opacity=alpha, size=8))
fig.update_layout(
    legend=dict(orientation="h", x=0, xanchor="left", y=-0.2, yanchor="top"),
    margin=dict(l=0, r=0, t=10, b=120)
)

st.plotly_chart(fig, use_container_width=True, config={"responsive": True})
st.write("Opacité des points :", alpha)
