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

tabs = st.tabs([
    "1️⃣ Vývoj bodů",
    "2️⃣ Vývoj pořadí v minilize",
    "3️⃣ Top 30 bodových výkonů",
    "4️⃣ Aktuální pořadí miniligy"
])

with tabs[0]:
    if st.button("Zobrazit vývoj bodů", key="button_vyvoj_bodu"):
        entries = fetch_league_data(league_id)
        df = pd.DataFrame()
        max_rounds = 38

        for entry_id, name in entries:
            try:
                history = fetch_team_history(entry_id)
                points = [gw.get('total_points', 0) for gw in history]
                if len(points) < max_rounds:
                    points += [points[-1] if points else 0] * (max_rounds - len(points))
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
                    hovertemplate='Kolo %{x}<br>Body celkem: %{y}<br>Tým: '+team+'<extra></extra>'
                ))

            fig.update_layout(
                updatemenus=[
                    dict(
                        type="buttons",
                        direction="left",
                        buttons=[
                            dict(
                                label="Hide all",
                                method="update",
                                args=[{"visible": [False]*len(df.columns)},
                                      {"title": "Všechny čáry skryty"}]
                            ),
                            dict(
                                label="Show all",
                                method="update",
                                args=[{"visible": [True]*len(df.columns)},
                                      {"title": "Vývoj celkových bodů v minilize (Všechny týmy)"}]
                            )
                        ],
                        pad={"r": 10, "t": 10},
                        showactive=False,
                        x=0,
                        xanchor="left",
                        y=1.15,
                        yanchor="top"
                    )
                ]
            )

            fig.update_layout(
                title="Vývoj celkových bodů v minilize (Všechny týmy)",
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
    if st.button("Zobrazit vývoj pořadí v minilize", key="button_vyvoj_poradi"):
        entries = fetch_league_data(league_id)
        max_rounds = 38

        points_per_round = {}
        for entry_id, name in entries:
            try:
                history = fetch_team_history(entry_id)
                points = []
                for gw in history:
                    pts = gw.get('event_points')
                    if pts is None:
                        pts = gw.get('points')
                    if pts is None:
                        pts = 0
                    points.append(pts)
                if len(points) < max_rounds:
                    points += [0] * (max_rounds - len(points))
                points_per_round[name] = points
            except Exception as e:
                st.warning(f"Chyba při načítání dat pro {name}: {e}")

        df_points = pd.DataFrame(points_per_round)
        df_points.index = range(1, max_rounds + 1)

        # Kumulativní body
        df_cum_points = df_points.cumsum()

        # Pořadí podle kumulativních bodů (1 = nejlepší)
        df_rankings = df_cum_points.rank(axis=1, method='min', ascending=False).astype(int)
        max_position = len(df_rankings.columns)

        fig = go.Figure()
        for team in df_rankings.columns:
            fig.add_trace(go.Scatter(
                x=df_rankings.index,
                y=df_rankings[team],
                mode='lines+markers',
                name=team,
                line=dict(width=2),
                marker=dict(size=5),
                hovertemplate='Kolo %{x}<br>Pořadí v minilize: %{y}<br>Tým: '+team+'<extra></extra>'
            ))

        fig.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    direction="left",
                    buttons=[
                        dict(
                            label="Hide all",
                            method="update",
                            args=[{"visible": [False]*max_position},
                                  {"title": "Všechny čáry skryty"}]
                        ),
                        dict(
                            label="Show all",
                            method="update",
                            args=[{"visible": [True]*max_position},
                                  {"title": "Vývoj pořadí v minilize podle kumulativních bodů (Všechny týmy)"}]
                        )
                    ],
                    pad={"r": 10, "t": 10},
                    showactive=False,
                    x=0,
                    xanchor="left",
                    y=1.15,
                    yanchor="top"
                )
            ]
        )

        fig.update_layout(
            title="Vývoj pořadí v minilize podle kumulativních bodů (Všechny týmy)",
            xaxis_title="Kolo",
            yaxis_title="Pořadí v minilize (1 = nejlepší)",
            xaxis=dict(range=[1, 38], dtick=1, tick0=1),
            yaxis=dict(range=[1, max_position], autorange="reversed"),
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

with tabs[2]:
    if st.button("Zobrazit top 30 bodových výkonů", key="button_top30"):
        entries = fetch_league_data(league_id)
        performances = []

        for entry_id, name in entries:
            try:
                history = fetch_team_history(entry_id)
                for gw in history:
                    pts = gw.get('event_points')
                    if pts is None:
                        pts = gw.get('points')
                    if pts is None:
                        pts = 0
                    performances.append({
                        "Tým": name,
                        "Kolo": gw.get('event', 0),
                        "Body": pts
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

with tabs[3]:
    if st.button("Zobrazit aktuální pořadí", key="button_poradi"):
        entries = fetch_league_data(league_id)
        teams_data = []

        for entry_id, name in entries:
            try:
                history = fetch_team_history(entry_id)
                total = history[-1].get('total_points', 0) if history else 0
                teams_data.append({"Tým": name, "Body celkem": total})
            except Exception as e:
                st.warning(f"Chyba při načítání dat pro {name}: {e}")

        if teams_data:
            df_rank = pd.DataFrame(teams_data)
            df_rank = df_rank.sort_values(by="Body celkem", ascending=False).reset_index(drop=True)
            df_rank.index += 1
            st.subheader("🏆 Aktuální pořadí miniligy")
            st.table(df_rank)
