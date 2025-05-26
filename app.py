import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from requests.exceptions import HTTPError

st.set_page_config(layout="wide", page_title="FPL Miniliga")

league_id = 36264
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

def fetch_team_history_safe(entry_id):
    url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/event-history/"
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        return data['current']
    except HTTPError as http_err:
        if r.status_code == 404:
            st.warning(f"Tým s ID {entry_id} nemá dostupnou historii (404 Not Found). Přeskočeno.")
            return None
        else:
            st.error(f"HTTP chyba při načítání dat pro tým {entry_id}: {http_err}")
            return None
    except Exception as e:
        st.error(f"Chyba při načítání dat pro tým {entry_id}: {e}")
        return None

def create_hide_show_buttons(num_traces):
    buttons = []
    buttons.append(dict(
        label="Show all",
        method="update",
        args=[{"visible": [True] * num_traces}]
    ))
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

tabs = st.tabs(["Vývoj bodů týmů", "Top 30 bodových výkonů", "Vývoj pořadí v minilize", "Pořadí v minilize"])

entries = fetch_league_data(league_id)

# --- Zpracování dat pro všechny týmy ---
team_histories = {}
for entry_id, name in entries:
    history = fetch_team_history_safe(entry_id)
    if history is None:
        continue
    team_histories[name] = history

# --- 1. Vývoj bodů týmů ---
with tabs[0]:
    st.header("Vývoj bodů týmů v minilize")

    points_per_round = {}
    for name, history in team_histories.items():
        points = [gw.get('event_points', 0) for gw in history]
        if len(points) < max_rounds:
            points += [0] * (max_rounds - len(points))
        points_per_round[name] = points

    df_points = pd.DataFrame(points_per_round)
    df_points.index = range(1, max_rounds + 1)

    fig = go.Figure()
    for name in df_points.columns:
        fig.add_trace(go.Scatter(x=df_points.index, y=df_points[name], mode='lines+markers', name=name, visible=True))

    fig.update_layout(
        title="Body týmů po jednotlivých kolech",
        xaxis_title="Kolo",
        yaxis_title="Body v kole",
        xaxis=dict(tickmode="linear", dtick=1, range=[1, max_rounds]),
        updatemenus=create_hide_show_buttons(len(df_points.columns)),
        height=600,
    )
    st.plotly_chart(fig, use_container_width=True)

# --- 2. Top 30 bodových výkonů v rámci jednoho kola ---
with tabs[1]:
    st.header("Top 30 bodových výkonů v rámci jednoho kola")

    performance_list = []
    for name, history in team_histories.items():
        for round_num, gw in enumerate(history, 1):
            points = gw.get('event_points', 0)
            performance_list.append({"Tým": name, "Kolo": round_num, "Body": points})

    df_performance = pd.DataFrame(performance_list)
    df_performance = df_performance.sort_values(by="Body", ascending=False).head(30)
    df_performance.reset_index(drop=True, inplace=True)
    df_performance.index += 1
    st.table(df_performance)

# --- 3. Vývoj pořadí v rámci miniligy po kolech ---
with tabs[2]:
    st.header("Vývoj pořadí týmů v minilize po jednotlivých kolech")

    # Nejprve vytvoříme DataFrame s body po kolech
    df_points_cum = pd.DataFrame()
    for name, history in team_histories.items():
        points = [gw.get('event_points', 0) for gw in history]
        if len(points) < max_rounds:
            points += [0] * (max_rounds - len(points))
        df_points_cum[name] = points

    df_points_cum.index = range(1, max_rounds + 1)
    df_cum_sum = df_points_cum.cumsum()

    # Vypočítat pořadí v rámci miniligy (menší pořadí je lepší)
    order_data = {}
    for round_num in df_cum_sum.index:
        round_points = df_cum_sum.loc[round_num]
        round_order = round_points.rank(ascending=False, method='min')
        order_data[round_num] = round_order

    df_order = pd.DataFrame(order_data).T
    df_order.index.name = "Kolo"
    df_order.columns.name = "Tým"

    fig_order = go.Figure()
    for name in df_order.columns:
        fig_order.add_trace(go.Scatter(
            x=df_order.index,
            y=df_order[name],
            mode='lines+markers',
            name=name,
            visible=True,
            hovertemplate='Kolo %{x}<br>Pořadí: %{y}<extra></extra>'
        ))

    fig_order.update_layout(
        title="Vývoj pořadí týmů v minilize (kumulativní body)",
        xaxis_title="Kolo",
        yaxis_title="Pořadí (1 = nejlepší)",
        yaxis=dict(autorange="reversed", dtick=1),
        xaxis=dict(tickmode="linear", dtick=1, range=[1, max_rounds]),
        updatemenus=create_hide_show_buttons(len(df_order.columns)),
        height=600,
    )
    st.plotly_chart(fig_order, use_container_width=True)

# --- 4. Aktuální pořadí miniligy ---
with tabs[3]:
    st.header("Aktuální pořadí miniligy")

    # Získat aktuální pořadí z API
    url_standings = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/"
    response = requests.get(url_standings)
    response.raise_for_status()
    data = response.json()

    standings = data['standings']['results']
    df_standings = pd.DataFrame(standings)
    df_standings = df_standings[['rank', 'player_name', 'entry', 'total']]
    df_standings.rename(columns={
        'rank': 'Pořadí',
        'player_name': 'Tým',
        'entry': '
