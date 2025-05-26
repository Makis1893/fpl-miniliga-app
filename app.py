import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

st.set_page_config(page_title="FPL Miniliga - Graf", layout="wide")
st.title("Fantasy Premier League – Vyvoj bodu v minilize")

league_id = st.number_input("Zadej ID miniligy (napr. 36264):", min_value=1, value=36264, step=1)

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

if st.button("Zobrazit graf"):
    entries = fetch_league_data(league_id)
    df = pd.DataFrame()

    for entry_id, name in entries:
        try:
            points = fetch_team_history(entry_id)
            df[name] = points
        except Exception as e:
            st.warning(f"Chyba pri nacitani dat pro {name}: {e}")

    if not df.empty:
        df_cum = df.cumsum()
        st.subheader("Vyvoj celkovych bodu")
        st.line_chart(df_cum)
