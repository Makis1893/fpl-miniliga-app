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
    return response.json().get('current', [])

tabs = st.tabs(["📈 Vývoj bodů", "🔥 Top 30 bodových výkonů", "🏆 Pořadí miniligy", "📉 Vývoj pořadí"])

with tabs[0]:
    if st.button("Zobrazit vývoj bodů", key="button_vyvoj"):
        entries = fetch_league_data(league_id)
        df = pd.DataFrame()
        max_rounds = 38

        for entry_id, name in entries:
            try:
                history = fetch_team_history(entry_id)
                points = [gw['total_points'] for gw in history]
                if len(points) < max_rounds:
                    points += [points[-1]] * (max_rounds - len(points))
                df[name] = points
            except Exception as e:
                st.warning(f"Chyba při načítání dat pro {name}: {e}")

        if not df.empty:
            df.index = range(1, max_rounds + 1)

            fig = go.Figure()

            for team in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df[team],
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
                yaxis=dict(range=[0, df.values.max()*1.1]),
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
    if st.button("Zobrazit top 30 bodových výkonů", key="button_top30"):
        entries = fetch_league_data(league_id)
        performances = []

        for entry_id, name in entries:
            try:
                history = fetch_team_history(entry_id)
                for gw in history:
                    body = gw.get('event_points')
                    if not body:
                        body = gw.get('points', 0)
                    performances.append({
                        "Tým": name,
                        "Kolo": gw['event'],
                        "Body": body
                    })
            except Exception as e:
                st.warning(f"Chyba při načítání dat pro {name}: {e}")

        if performances:
            df_perf = pd.DataFrame(performances)
            top30 = df_perf.sort_values(by="Body", ascending=False).head(30).reset_index(drop=True)
            top30.index += 1
            top30.index.name = 'Pořadí'
            st.subheader("🔥 Top 30 bodových výkonů v rámci jednoho kola")
            st.table(top30)

with tabs[2]:
    if st.button("Zobrazit aktuální pořadí", key="button_poradi"):
        entries = fetch_league_data(league_id)
        teams_data = []

        for entry_id, name in entries:
            try:
                history = fetch_team_history(entry_id)
                total = history[-1]['total_points'] if history else 0
                teams_data.append({"Tým": name, "Body celkem": total})
            except Exception as e:
                st.warning(f"Chyba při načítání dat pro {name}: {e}")

        if teams_data:
            df_rank = pd.DataFrame(teams_data)
            df_rank = df_rank.sort_values(by="Body celkem", ascending=False).reset_index(drop=True)
            df_rank.index += 1
            st.subheader("🏆 Aktuální pořadí miniligy")
            st.table(df_rank)

with tabs[3]:
    if st.button("Zobrazit vývoj pořadí", key="button_vyvoj_poradi"):
        entries = fetch_league_data(league_id)
        df_rankings = pd.DataFrame()
        max_rounds = 38

        for entry_id, name in entries:
            try:
                history = fetch_team_history(entry_id)
                ranks = [gw['overall_rank'] for gw in history]
                # doplnit chybějící kola stejným posledním pořadím
                if len(ranks) < max_rounds:
                    ranks += [ranks[-1]] * (max_rounds - len(ranks))
                df_rankings[name] = ranks
            except Exception as e:
                st.warning(f"Chyba při načítání dat p
