import pandas as pd
import pgeocode
import plotly.express as px
import requests
import pgeocode




df = pd.read_csv("Base_brevo_juillet_2.csv", sep=';', dtype={'CODE_POSTAL': str})

df = df.dropna(subset=['TYPO_CULTURE', 'CODE_POSTAL'])

df = df.dropna(subset=['CODE_POSTAL'])

df["CODE_POSTAL"] = df["CODE_POSTAL"].apply(lambda x: x.zfill(5))
df.dropna(subset=['TYPO_CULTURE'], inplace=True)
len(df)

#Coordonées
nomi = pgeocode.Nominatim('fr')
coordonnees = nomi.query_postal_code(df['CODE_POSTAL'].astype(str).tolist())
df['latitude'] = coordonnees.latitude
df['longitude'] = coordonnees.longitude

#map





#affichage streamlit
import streamlit as st

titre = "Carte des cultures agricoles en France"
st.title(titre)
st.set_page_config(layout="wide")

#alpha_cursor 
alpha_cursor = st.slider("Opacité des points", 0.0, 1.0, 0.5)
fig = px.scatter_mapbox(
    df, lat='latitude', lon='longitude', color='TYPO_CULTURE',
    hover_name='TYPO_CULTURE', zoom=4, height=600,
    mapbox_style="open-street-map"   # pas besoin de token
)
st.plotly_chart(fig, use_container_width=True)
fig.update_traces(marker_opacity=alpha_cursor)
st.write("Opacité des points : ", alpha_cursor)


#%%
