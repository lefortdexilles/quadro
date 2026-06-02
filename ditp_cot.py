import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import openpyxl

st.set_page_config(page_title="Priorisation bilatérale", layout="wide")

st.title("Outil de cotation stratégique des pays")
st.caption("Comparaison entre effectifs engagés et charge d'activité")

uploaded_file = st.file_uploader("Charger le fichier Excel", type=["xlsx"])
if uploaded_file is None:
    st.info("Chargez un fichier contenant au minimum : pays, moyens, 17 criteres.")
    st.stop()

if uploaded_file.name.endswith(".xlsx"):
    df = pd.read_excel(uploaded_file, sheet_name="Sheet1", engine="openpyxl")
else:
    df = pd.read_csv(uploaded_file)

st.subheader("Aperçu des données")
st.dataframe(df.head())

baremes = {
    "c1": [(7, 1), (6, 0.8), (4, 0.5), (2, 0.4), (0, 0.2)],
    "c4": [(4, 1), (3, 0.8), (2, 0.5), (1, 0.4), (0, 0.2)],
    "c5": [(81, 1), (80, 0.8), (50, 0.5), (20, 0.4), (10, 0.2)],
    "c12": [(200, 1), (50, 0.8), (20, 0.5), (0, 0)],
    "c13": [(2, 1), (1, 0.5), (0, 0)],
    "c14": [(1000, 1), (500, 0.8), (100, 0.2), (0, 0.1)],
    "c17": [(50, 1), (10, 0.5), (0, 0.2)],
    "c18": [(5000, 1), (1000, 0.5), (0, 0.2)],
    "c19": [(50, 1), (20, 0.8), (10, 0.5), (5, 0.4), (0, 0.2)]
}

def appliquer_baremes(df, baremes, default=0):

    for col, bareme in baremes.items():
        conditions = [df[col] > seuil for seuil, note in bareme]
        notes = [note for seuil, note in bareme]

        df[col + "_note"] = np.select(
            conditions,
            notes,
            default=default
        )

    return df

dfr = appliquer_baremes(df, baremes)

df3 = pd.concat(
    [dfr[["pays", "moyens", "format", "iso_3", "c2", "c3", "c6", "c7", "c8", "c9", "c10", "c11", "c15", "c16"]], dfr[["c1_note", "c4_note", "c5_note", "c12_note", 
    "c13_note", "c14_note","c17_note","c18_note","c19_note",]]],
    axis=1
)

# --------------------------------------------------
# 2. Sélection dynamique des critères par groupe
# --------------------------------------------------

st.sidebar.header("Classement des critères")

criteres = [
    "c1_note", "c2", "c3", "c4_note", "c5_note", "c6", "c7",
    "c8", "c9", "c10", "c11", "c12_note", "c13_note",
    "c14_note", "c15", "c16", "c17_note", "c18_note", "c19_note"
]

# Initialisation du session_state
if "groupe_1" not in st.session_state:
    st.session_state.groupe_1 = [
        "c1_note", "c2", "c3", "c5_note", "c7", "c10",
        "c15", "c18_note", "c17_note"
    ]

if "groupe_2" not in st.session_state:
    st.session_state.groupe_2 = ["c8", "c9", "c11", "c14_note", "c16", "c12_note", "c19_note"]

if "groupe_3" not in st.session_state:
    st.session_state.groupe_3 = ["c4_note", "c6", "c13_note"]


def options_disponibles(groupe_courant):
    deja_selectionnes_autres_groupes = set()

    for nom_groupe in ["groupe_1", "groupe_2", "groupe_3"]:
        if nom_groupe != groupe_courant:
            deja_selectionnes_autres_groupes.update(st.session_state[nom_groupe])

    return [
        c for c in criteres
        if c not in deja_selectionnes_autres_groupes
        or c in st.session_state[groupe_courant]
    ]


st.session_state.groupe_1 = st.sidebar.multiselect(
    "Groupe niveau 1",
    options=options_disponibles("groupe_1"),
    default=st.session_state.groupe_1,
    key="ms_groupe_1"
)

st.session_state.groupe_2 = st.sidebar.multiselect(
    "Groupe niveau 2",
    options=options_disponibles("groupe_2"),
    default=st.session_state.groupe_2,
    key="ms_groupe_2"
)

st.session_state.groupe_3 = st.sidebar.multiselect(
    "Groupe niveau 3",
    options=options_disponibles("groupe_3"),
    default=st.session_state.groupe_3,
    key="ms_groupe_3"
)


groupes = {
    "Groupe niveau 1": st.session_state.groupe_1,
    "Groupe niveau 2": st.session_state.groupe_2,
    "Groupe niveau 3": st.session_state.groupe_3
}

# --------------------------------------------------
# 3. Sliders de poids
# --------------------------------------------------

st.sidebar.header("Poids des critères")

poids_groupes = {}

for groupe in groupes:
    poids_groupes[groupe] = st.sidebar.slider(
        label=f"Poids : {groupe}",  
        min_value=5,
        max_value=50,
        value=10,
        step=10
    )

# --------------------------------------------------
# 3. Attribution du poids à chaque critère
# --------------------------------------------------

poids_criteres = {}

for groupe, liste_criteres in groupes.items():

# poids brut issu du slider
    poids_brut = poids_groupes[groupe]

    # transformation non linéaire
    poids_effectif = 1 + (poids_brut - 1)**2

    for critere in liste_criteres:

        poids_criteres[critere] = poids_effectif

# --------------------------------------------------
# 4. Somme des poids
# --------------------------------------------------

somme_poids = sum(poids_criteres.values())

if somme_poids == 0:

    st.warning(
        "La somme des poids est égale à 0."
    )

else:

    # --------------------------------------------------
    # 5. Calcul du score final
    # --------------------------------------------------


    score_final = (
        sum(
            df3[c] * poids_criteres[c]
            for c in poids_criteres
        )
        / somme_poids
    )

    df3["score_final"] = score_final
 
# --------------------------------------------------
# 6. Définition des seuils des quadrants
# --------------------------------------------------

seuil_score = df3["score_final"].median()
seuil_moyens = df3["moyens"].median()

def attribuer_quadrant(row):
    if row["score_final"] >= seuil_score and row["moyens"] >= seuil_moyens:
        return "Charge + complexité élevées / moyens forts"
    elif row["score_final"] >= seuil_score and row["moyens"] < seuil_moyens:
        return "Charge + complexité élevées / moyens faibles"
    elif row["score_final"] < seuil_score and row["moyens"] >= seuil_moyens:
        return "Charge + complexité relative / moyens forts"
    else:
        return "Charge + complexité relative / moyens faibles"

df3["quadrant"] = df3.apply(attribuer_quadrant, axis=1)

couleurs_quadrants = {
    "Charge + complexité élevées / moyens forts": "#2ca02c",
    "Charge + complexité élevées / moyens faibles": "#ff7f0e",
    "Charge + complexité relative / moyens forts": "#d62728",
    "Charge + complexité relative / moyens faibles": "#1f77b4"
}

# --------------------------------------------------
# 7. Affichage en deux colonnes
# --------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    st.subheader("Quadrants : score stratégique vs moyens")

    fig_scatter = px.scatter(
        df3,
        x="score_final",
        y="moyens",
        color="format",
        #color_discrete_map=couleurs_quadrants,
        hover_name="pays",
        hover_data={
            "score_final": ":.2f",
            "moyens": True,
            "quadrant": True,
            "iso_3": False
        },
        text="pays"
    )

    fig_scatter.add_vline(
        x=seuil_score,
        line_dash="dash",
        line_color="gray"
    )

    fig_scatter.add_hline(
        y=seuil_moyens,
        line_dash="dash",
        line_color="gray"
    )

    fig_scatter.update_traces(
        textposition="top center",
        marker=dict(size=12)
    )

    fig_scatter.update_layout(
        height=650,
        xaxis_title="Score final",
        yaxis_title="Moyens",
        legend_title="Format de poste"
    )

    st.plotly_chart(fig_scatter, use_container_width=True)

with col2:
    st.subheader("Carte des quadrants par pays")

    fig_map = px.choropleth(
        df3,
        locations="iso_3",
        color="quadrant",
        hover_name="pays",
        hover_data={
            "score_final": ":.2f",
            "moyens": True,
            "quadrant": True,
            "iso_3": False
        },
        color_discrete_map=couleurs_quadrants,
        projection="natural earth"
    )

    fig_map.update_layout(
        height=650,
        margin=dict(l=0, r=0, t=20, b=0),
        legend_title="Quadrant"
    )

    st.plotly_chart(fig_map, use_container_width=True)

# --------------------------------------------------
# 8. Tableau final
# --------------------------------------------------

st.subheader("Tableau final")

st.dataframe(
    df3.sort_values("score_final", ascending=False),
    use_container_width=True
)