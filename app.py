import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="FPL Miniliga")

league_id = 36264  # Tvoje miniliga ID
max_rounds = 38

@st.cache_data(ttl=3600)
def fetch_league_data(league_id):
    url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/"
    entries = []
    page = 1
    while True:
        r = requests.get(url + f"?page_standings={page}")
        r.raise_for_status()
        data = r.json()
        standings = data['standings']['results']
        for entry in standings:
            entries.append((entry['entry'], entry['player_name']))
        if not data['standings']['has_next']:
            break
        page += 1
    return entries

@st.cache_data(ttl=3600)
def fetch_team_history(entry_id):
    url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/event-history/"
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    return data['current']

def create_hide_show_buttons(num_traces, prefix=""):
    buttons = []
    # Show all
    buttons.append(dict(
        label="Show all",
        method="update",
        args=[{"visible": [True] * num_traces}]
    ))
    # Hide all
    buttons.append(dict(
        label="Hide all",
        method="update",
        args=[{"visible": [False] * num_traces}]
    ))
    return [dict(
        type="buttons",
        direction="right",
        buttons=buttons,
        pad={"r": 10, "t": 10},
        showactive=False,
        x=0,
        y=1.1,
        xanchor="left",
        yanchor="top"
    )]

st.title("Fantasy Premier League Miniliga")

tabs = st.tabs(["Vývoj bodů týmů", "Top 30 bodových výkonů", "Vývoj pořadí v minilize"])

# --- Sekce 1: Vývoj bodů týmů ---
with tabs[0]:
    st.header("Vývoj bodů týmů v minilize")
    entries = fetch_league_data(league_id)

    points_per_round = {}
    for entry_id, name in entries:
        try:
            history = fetch_team_history(entry_id)
            points = [gw.get('event_points', 0) for gw in history]
            if len(points) < max_rounds:
                points += [0] * (max_rounds - len(points))
            points_per_round[name] = points
        except Exception as e:
            st.warning(f"Chyba při načítání dat pro {name}: {e}")

    df_points = pd.DataFrame(points_per_round)
    df_points.index = range(1, max_rounds + 1)

    fig1 = go.Figure()
    for team in df_points.columns:
        fig1.add_trace(go.Scatter(
            x=df_points.index,
            y=df_points[team],
            mode='lines+markers',
            name=team,
            line=dict(width=2),
            marker=dict(size=5),
            hovertemplate='Kolo %{x}<br>Body: %{y}<br>Tým: '+team+'<extra></extra>'
        ))

    fig1.update_layout(
        updatemenus=create_hide_show_buttons(len(df_points.columns), prefix="points"),
        title="Body v jednotlivých kolech",
        xaxis_title="Kolo",
        yaxis_title="Body",
        xaxis=dict(range=[1, max_rounds], dtick=1, tick0=1),
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
    st.plotly_chart(fig1, use_container_width=True)

# --- Sekce 2: Top 30 bodových výkonů ---
with tabs[1]:
    st.header("Top 30 bodových výkonů v rámci jednoho kola")
    # Vytvoříme dataframe se všemi výkony jednotlivých týmů a kol
    records = []
    for entry_id, name in entries:
        try:
            history = fetch_team_history(entry_id)
            for gw in history:
                event = gw.get('event')
                points = gw.get('event_points', 0)
                records.append({"Tým": name, "Kolo": event, "Body": points})
        except Exception as e:
            st.warning(f"Chyba při načítání dat pro {name}: {e}")

    df_performance = pd.DataFrame(records)
    df_performance = df_performance.dropna(subset=["Body", "Kolo"])

    # Seřadíme podle bodů sestupně, pak podle kola vzestupně
    df_top = df_performance.sort_values(by=["Body", "Kolo"], ascending=[False, True]).head(30)
    df_top.reset_index(drop=True, inplace=True)
    df_top.index += 1  # Pořadí od 1

    st.table(df_top.style.format({"Body": "{:.0f}"}))

# --- Sekce 3: Vývoj pořadí v minilize ---
with tabs[2]:
    st.header("Vývoj pořadí týmů v minilize podle kumulativních bodů")
    points_per_round = {}
    for entry_id, name in entries:
        try:
            history = fetch_team_history(entry_id)
            points = [gw.get('event_points', 0) for gw in history]
            if len(points) < max_rounds:
                points += [0] * (max_rounds - len(points))
            points_per_round[name] = points
        except Exception as e:
            st.warning(f"Chyba při načítání dat pro {name}: {e}")

    df_points = pd.DataFrame(points_per_round)
    df_points.index = range(1, max_rounds + 1)

    # kumulativní body
    df_cum = df_points.cumsum()

    # Pořadí v minilize: rankujeme po řádcích (kolech), descending body = rank 1 nejlepší
    df_rankings = df_cum.rank(axis=1, method='min', ascending=False).astype(int)

    max_position = len(df_rankings.columns)

    fig2 = go.Figure()
    for team in df_rankings.columns:
        fig2.add_trace(go.Scatter(
            x=df_rankings.index,
            y=df_rankings[team],
            mode='lines+markers',
            name=team,
            line=dict(width=2),
            marker=dict(size=5),
            hovertemplate='Kolo %{x}<br>Pořadí v minilize: %{y}<br>Tým: '+team+'<extra></extra>'
        ))

    fig2.update_layout(
        updatemenus=create_hide_show_buttons(len(df_rankings.columns), prefix="rank"),
        title="Vývoj průběžného pořadí v minilize podle kumulativních bodů",
        xaxis_title="Kolo",
        yaxis_title="Pořadí v minilize (1 = nejlepší)",
        xaxis=dict(range=[1, max_rounds], dtick=1, tick0=1),
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
    st.plotly_chart(fig2, use_container_width=True)
