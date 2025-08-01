import pandas as pd
import pgeocode
import plotly.express as px
import streamlit as st

# 1) Toujours en premier
st.set_page_config(layout="wide")
st.title("Visualisateur Brevo")

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
    hover_data=["TYPO_CULTURE", "EMAIL", "SOCIETE_OU_ORGANISME"], zoom=5, height=1000, mapbox_style="carto-positron")

fig.update_traces(marker=dict(opacity=alpha, size=8))

fig.update_layout(
    legend=dict(orientation="h", x=0, xanchor="left", y=-0.2, yanchor="top"),
    margin=dict(l=0, r=0, t=10, b=120)
)

st.plotly_chart(fig, use_container_width=True, config={"responsive": True})


# --- Graphiques en camembert ---

st.subheader("Graphiques en camembert")
def plotly_pie_chart(df, variable, title, max_value_slider=20):
    """Affiche un graphique en camembert pour une variable donnée."""
    st.subheader(title)
    max_value_slider = st.slider(f"Nombre maximum de {variable} à afficher", 1, max_value_slider, 10)
    pie = df[variable].value_counts().reset_index()[:max_value_slider]
    pie.columns = [variable, "Nombre"]
    fig_pie = px.pie(pie, values="Nombre", names=variable, title=title)
    fig_pie.update_traces(textposition='outside', textinfo='percent+label')
    st.plotly_chart(fig_pie, use_container_width=True, config={"responsive": True})
    return fig_pie

# plotly_pie_chart(df, "TYPO_CULTURE", "Répartition des cultures agricoles", max_value_slider=20)
# plotly_pie_chart(df, "DEPARTEMENT", "Répartition des départements", max_value_slider=100)

def pie_chart_to_display(df):
    variables = df.columns.tolist()
    variables_choices = st.multiselect("Sélectionner les variables pour les graphiques en camembert", variables)
    for variable in variables_choices:
        plotly_pie_chart(df, variable, f"Répartition de {variable}", max_value_slider=50)

pie_chart_to_display(df)

# --- Graphiques en barres ---
st.subheader("Graphiques en barres")
def plotly_bar_chart(df, variable, title):
    """Affiche un graphique en barres pour une variable donnée."""
    st.subheader(title)
    max_value_slider = st.slider(f"Nombre maximum de {variable} à afficher", 1, len(df[variable].unique()), 10)
    bar = df[variable].value_counts().reset_index()[:max_value_slider]
    bar.columns = [variable, "Nombre"]
    fig_bar = px.bar(bar, x=variable, y="Nombre", title=title)
    fig_bar.update_layout(xaxis_title=variable, yaxis_title="Nombre")
    st.plotly_chart(fig_bar, use_container_width=True, config={"responsive": True})
    return fig_bar
def bar_chart_to_display(df):
    variables = df.columns.tolist()
    variables_choices = st.multiselect("Sélectionner les variables pour les graphiques en barres", variables)
    for variable in variables_choices:
        plotly_bar_chart(df, variable, f"Répartition de {variable}")
bar_chart_to_display(df)

#%%
# --- Choroplèthe départements ---
import json, requests

@st.cache_data
def load_departements_geojson():
    # GeoJSON des départements (IGN/INSEE, mirroir github)
    url = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"
    gj = requests.get(url, timeout=30).json()
    # dictionnaire nom -> code et code -> nom (pour le survol)
    props = [f["properties"] for f in gj["features"]]
    name2code = {p["nom"].upper(): p["code"] for p in props}
    code2name = {p["code"]: p["nom"] for p in props}
    return gj, name2code, code2name




def make_dept_choropleth(df, geojson, name2code, code2name,
                         culture_choice="(Toutes)", metric="Nb. d'enregistrements"):
    # filtre éventuel sur une culture
    data = df if culture_choice == "(Toutes)" else df[df["TYPO_CULTURE"] == culture_choice]

    # agrégation par département
    if metric == "Nb. d'enregistrements":
        agg = data.groupby("DEPARTEMENT", as_index=False).size().rename(columns={"size": "Valeur"})
    else:  # "Nb. de cultures distinctes"
        agg = data.groupby("DEPARTEMENT")["TYPO_CULTURE"].nunique().reset_index(name="Valeur")

    # tenter d’obtenir un code département valable (ex: '75', '13', '2A', '971')
    s = agg["DEPARTEMENT"].astype(str).str.strip()
    is_code = s.str.fullmatch(r"\d{2,3}|2A|2B")
    agg["code"] = s.where(is_code, s.str.upper().map(name2code))
    agg = agg.dropna(subset=["code"]).copy()
    agg["nom"] = agg["code"].map(code2name)

    # carte
    fig_dep = px.choropleth_mapbox(
        agg,
        geojson=geojson,
        locations="code",
        featureidkey="properties.code",
        color="Valeur",
        hover_name="nom",
        hover_data={"code": True, "Valeur": True},
        mapbox_style="carto-positron",
        center={"lat": 46.6, "lon": 2.2},
        zoom=5, opacity=0.75, height=1000
    )
    fig_dep.update_layout(margin=dict(l=0, r=0, t=10, b=10))
    return fig_dep

# ---- UI ----
st.subheader("Carte choroplèthe par département")
geojson, name2code, code2name = load_departements_geojson()

culture_options = ["(Toutes)"] + sorted(df["TYPO_CULTURE"].dropna().unique().tolist())
culture_choice = st.selectbox("Filtrer sur une culture", culture_options, index=0)

fig_dep = make_dept_choropleth(df, geojson, name2code, code2name, culture_choice)
st.plotly_chart(fig_dep, use_container_width=True, config={"responsive": True})
