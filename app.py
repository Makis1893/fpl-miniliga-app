import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

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
            # Normalizuj jméno pro srovnání
            display_name = "Podoli-Pistin" if name.lower() == "podoli-pistin" else name
            points = fetch_team_history(entry_id)
            df[display_name] = points
        except Exception as e:
            st.warning(f"Chyba při načítání dat pro {name}: {e}")

    if not df.empty:
        df.index = range(1, len(df) + 1)  # Gameweeks
        df = df.reindex(range(1, 39))     # Extend to 38 GWs
        df_cum = df.fillna(method="ffill").fillna(0)

        # Vybrat top 5 týmů + "Podoli-Pistin"
        final_scores = df_cum.iloc[-1]
        top5 = final_scores.sort_values(ascending=False).head(5)
        team_set = set(top5.index.tolist())
        if "Podoli-Pistin" not in team_set and "Podoli-Pistin" in df_cum.columns:
            team_set.add("Podoli-Pistin")
        selected = df_cum[list(team_set)]

        # 🎨 Vykreslit graf
        st.subheader("📈 Vývoj celkových bodů (Top 5 + Podoli-Pistin)")

        fig, ax = plt.subplots(figsize=(12, 6))
        for col in selected.columns:
            ax.plot(selected.index, selected[col], label=col, linewidth=2)

        ax.set_xlim(1, 38)
        ax.set_xlabel("Kolo", fontsize=12)
        ax.set_ylabel("Celkové body", fontsize=12)
        ax.set_title("Vývoj bodů v minilize", fontsize=14)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5))
        st.pyplot(fig)
