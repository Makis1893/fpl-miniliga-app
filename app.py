import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="FPL Miniliga - Analýzy", layout="wide")
st.title("📊 Fantasy Premier League – Analýzy miniligy")

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

@st.cache_data
def fetch_team_history_full(entry_id):
    url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/history/"
    response = requests.get(url)
    return response.json().get('current', [])

tabs = st.tabs(["📈 Vývoj bodů", "🔥 Top 10 bodových výkonů", "🏆 Pořadí miniligy"])

with tabs[0]:
    if st.button("Zobrazit vývoj bodů", key="button_vyvoj"):
        entries = fetch_league_data(league_id)
        df = pd.DataFrame()

        for entry_id, name in entries:
            try:
                points = fetch_team_history(entry_id)
                df[name] = points
            except Exception as e:
                st.warning(f"Chyba při načítání dat pro {name}: {e}")

        if not df.empty:
            df.index = range(1, len(df) + 1)
            df = df.reindex(range(1, 39))
            df_cum = df.fillna(method="ffill").fillna(0)

            selected = df_cum

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
                title="Vývoj bodů v minilize (Všechny týmy)",
                xaxis_title="Kolo",
                yaxis_title="Celkové body",
                xaxis=dict(range=[1, 38], dtick=1, tick0=1),
                yaxis=dict(range=[0, selected.values.max()*1.1]),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    xref="paper",
                    yref="paper",
                    bgcolor="rgba(0,0,0,0)"
                ),
                margin=dict(l=40, r=40, t=60, b=40),
                hovermode="x unified"
            )

            st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    if st.button("Zobrazit top 10 bodových výkonů", key="button_top10"):
        entries = fetch_league_data(league_id)
        performances = []

        for entry_id, name in entries:
            try:
                history = fetch_team_history_full(entry_id)
                for gw in history:
                    performances.append({
                        "Tým": name,
                        "Kolo": gw['event'],
                        "Body": gw['total_points']
                    })
            except Exception as e:
                st.warning(f"Chyba při načítání dat pro {name}: {e}")

        if performances:
            df_perf = pd.DataFrame(performances)
            # Top 10 výkonů v rámci jednoho kola
            top10 = df_perf.sort_values(by="Body", ascending=False).head(10)
            st.subheader("🔥 Top 10 bodových výkonů v jednom kole")
            st.table(top10.reset_index(drop=True))

with tabs[2]:
    if st.button("Zobrazit aktuální pořadí", key="button_poradi"):
        entries = fetch_league_data(league_id)
        # Uspořádáme podle aktuálních celkových bodů (z posledního kola)
        teams_data = []

        for entry_id, name in entries:
            try:
                points = fetch_team_history(entry_id)
                total = points[-1] if points else 0
                teams_data.append({"Tým": name, "Body celkem": total})
            except Exception as e:
                st.warning(f"Chyba při načítání dat pro {name}: {e}")

        if teams_data:
            df_rank = pd.DataFrame(teams_data)
            df_rank = df_rank.sort_values(by="Body celkem", ascending=False).reset_index(drop=True)
            df_rank.index += 1
            st.subheader("🏆 Aktuální pořadí miniligy")
            st.table(df_rank)
