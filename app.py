import streamlit as st
import pandas as pd
import requests

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
            points = fetch_team_history(entry_id)
            df[name] = points
        except Exception as e:
            st.warning(f"Chyba při načítání dat pro {name}: {e}")

    if not df.empty:
        df.index = range(1, len(df) + 1)  # kolo 1..n
        df = df.reindex(range(1, 39))     # doplnit až do 38 kol NaN, pokud chybí
        df_cum = df.fillna(method="ffill").fillna(0)  # vyplnit chybějící NaN dopředu nulami

        # Vybrat top 5 týmů + "podoli-pistin"
        final_scores = df_cum.iloc[-1]
        top5 = final_scores.sort_values(ascending=False).head(5)
        team_set = set(top5.index.tolist())
        if "podoli-pistin" not in team_set and "podoli-pistin" in df_cum.columns:
            team_set.add("podoli-pistin")
        selected_teams = df_cum[list(team_set)]

        st.subheader("📈 Vývoj celkových bodů (Top 5 + Podoli-Pistin)")
        st.line_chart(selected_teams)
