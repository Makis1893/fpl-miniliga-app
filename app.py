import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="FPL Miniliga - Graf", layout="wide")
st.title("📊 Fantasy Premier League – Vývoj bodů v minilize")

league_id = st.number_input("Zadej ID miniligy (např. 36264):", min_value=1, value=36264, step=1)

@st.cache_data
def fetch_league_data(league_id):
    url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/"
    response = requests.get(url)
    data = response.json()
    entries = [(r['entry'], r['entry_name']) for r in data['standings']['results']]
    return entries

@st.cache_data
def fetch_team_history(entry_id):
    url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/history/"
    response = requests.get(url)
    return [gw['total_points'] for gw in response.json().get('current', [])]

if st.button("📈 Zobrazit graf"):
    entries = fetch_league_data(league_id)
    df = pd.DataFrame()

    for entry_id, name in entries:
        try:
            display_name = "Podoli-Pistin" if name.lower() == "podoli-pistin" else name
            points = fetch_team_history(entry_id)
            df[display_name] = points
        except Exception as e:
            st.warning(f"Chyba při načítání dat pro {name}: {e}")

    if not df.empty:
        df.index = range(1, len(df) + 1)
        df = df.reindex(range(1, 39))
        df_cum = df.fillna(method="ffill").fillna(0)

        final_scores = df_cum.iloc[-1]
        top5 = final_scores.sort_values(ascending=False).head(5)
        team_set = set(top5.index.tolist())
        if "Podoli-Pistin" not in team_set and "Podoli-Pistin" in df_cum.columns:
            team_set.add("Podoli-Pistin")
        selected = df_cum[list(team_set)]

        fig = go.Figure()

        for team in selected.columns:
            fig.add_trace(go.Scatter(
                x=selected.index,
                y=selected[team],
                mode='lines+markers',
                name=team,
                line=dict(width=2),
                marker=dict(size=5),
                hovertemplate='Kolo %{x}<br>Body: %{y}<br>Tým: '+team+'<extra></extra>'
            ))

        fig.update_layout(
            title="Vývoj bodů v minilize (Top 5 + Podoli-Pistin)",
            xaxis_title="Kolo",
            yaxis_title="Celkové body",
            xaxis=dict(range=[1, 38], dtick=1, tick0=1),
            yaxis=dict(range=[0, selected.values.max()*1.1]),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=40, r=40, t=60, b=40),
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)
