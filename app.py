import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="FPL Miniliga – Analýzy", layout="wide")
st.title("📊 Fantasy Premier League – Analýzy miniligy")

league_id = st.number_input("Zadej ID miniligy:", min_value=1, value=36264, step=1)
max_rounds = 38

@st.cache_data
def fetch_league_data(lid):
    url = f"https://fantasy.premierleague.com/api/leagues-classic/{lid}/standings/"
    r = requests.get(url); r.raise_for_status()
    return [(e["entry"], e["entry_name"]) for e in r.json()["standings"]["results"]]

@st.cache_data
def fetch_team_history(eid):
    url = f"https://fantasy.premierleague.com/api/entry/{eid}/history/"
    r = requests.get(url); r.raise_for_status()
    return r.json().get("current", [])

# Načti seznam týmů
entries = fetch_league_data(league_id)

# Připrav DataFrame bodů za každé kolo (event_points)
points_df = pd.DataFrame(index=range(1, max_rounds+1))
# Připrav DataFrame kumulativních bodů (total_points)
cum_df    = pd.DataFrame(index=range(1, max_rounds+1))
# Připrav DataFrame hodnoty týmu
value_df  = pd.DataFrame(index=range(1, max_rounds+1))

for eid, name in entries:
    hist = fetch_team_history(eid)
    # event_points
    ev = [gw.get("event_points", 0) for gw in hist]
    ev += [0] * (max_rounds - len(ev))
    points_df[name] = ev
    # total_points
    tot = [gw.get("total_points", 0) for gw in hist]
    tot += [tot[-1] if tot else 0] * (max_rounds - len(tot))
    cum_df[name] = tot
    # value v pencích → M£
    val = [gw.get("value", 0) for gw in hist]
    val += [val[-1] if val else 0] * (max_rounds - len(val))
    value_df[name] = [v/10 for v in val]

def add_hide_show(fig, n, title):
    fig.update_layout(
        updatemenus=[dict(
            type="buttons", direction="left", pad={"r":10,"t":10}, showactive=False,
            x=0, xanchor="left", y=1.25, yanchor="top",
            buttons=[
                dict(label="Hide all", method="update",
                     args=[{"visible": ["legendonly"]*n}, {"title":"Všechny čáry skryty"}]),
                dict(label="Show all", method="update",
                     args=[{"visible": [True]*n}, {"title": title}])
            ]
        )],
        legend=dict(orientation="h", yanchor="bottom", y=1.2, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=120, b=40),
        autosize=False,
        height=600
    )

tabs = st.tabs([
    "1️⃣ Kumulativní body",
    "2️⃣ Vývoj pořadí",
    "3️⃣ Top 30 výkonů",
    "4️⃣ Aktuální pořadí",
    "5️⃣ Vývoj hodnoty",
    "6️⃣ Scatter bodů"
])

# Tab 1: Kumulativní total_points
with tabs[0]:
    fig = go.Figure()
    for team in cum_df.columns:
        fig.add_trace(go.Scatter(
            x=cum_df.index, y=cum_df[team],
            mode="lines+markers", name=team
        ))
    add_hide_show(fig, len(cum_df.columns), "Kumulativní body")
    fig.update_layout(
        title="Kumulativní součet bodů v minilize",
        xaxis=dict(title="Kolo", tickmode="linear", dtick=1, range=[1, max_rounds]),
        yaxis_title="Body",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

# Tab 2: Vývoj pořadí
with tabs[1]:
    ranks = cum_df.rank(axis=1, method="min", ascending=False).astype(int)
    fig = go.Figure()
    for team in ranks.columns:
        fig.add_trace(go.Scatter(
            x=ranks.index, y=ranks[team],
            mode="lines+markers", name=team
        ))
    add_hide_show(fig, len(ranks.columns), "Vývoj pořadí")
    fig.update_layout(
        title="Vývoj pořadí v minilize (kumulativní body)",
        xaxis=dict(title="Kolo", tickmode="linear", dtick=1, range=[1, max_rounds]),
        yaxis=dict(title="Pořadí", autorange="reversed", dtick=1, range=[1, len(ranks.columns)]),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

# Tab 3: Top 30 výkonů (body v kole)
with tabs[2]:
    recs = []
    for event in points_df.index:
        for team in points_df.columns:
            recs.append({
                "Tým": team,
                "Kolo": event,
                "Body": points_df.at[event, team]
            })
    df_top = pd.DataFrame(recs) \
        .sort_values("Body", ascending=False) \
        .head(30) \
        .reset_index(drop=True)
    df_top.index += 1
    df_top.index.name = "Pořadí"
    st.table(df_top)

# Tab 4: Aktuální pořadí
with tabs[3]:
    recs = [
        {"Tým": team, "Body celkem": cum_df.at[max_rounds, team]}
        for team in cum_df.columns
    ]
    df_now = pd.DataFrame(recs) \
        .sort_values("Body celkem", ascending=False) \
        .reset_index(drop=True)
    df_now.index += 1
    df_now.index.name = "Pořadí"
    st.table(df_now)

# Tab 5: Vývoj hodnoty týmu
with tabs[4]:
    fig = go.Figure()
    for team in value_df.columns:
        fig.add_trace(go.Scatter(
            x=value_df.index, y=value_df[team],
            mode="lines+markers", name=team
        ))
    add_hide_show(fig, len(value_df.columns), "Vývoj hodnoty")
    fig.update_layout(
        title="Vývoj hodnoty týmu (M£)",
        xaxis=dict(title="Kolo", tickmode="linear", dtick=1, range=[1, max_rounds]),
        yaxis_title="Hodnota [M£]",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

# Tab 6: Scatter event_points
with tabs[5]:
    fig = go.Figure()
    for team in points_df.columns:
        fig.add_trace(go.Scatter(
            x=points_df.index, y=points_df[team],
            mode="markers", name=team, marker=dict(size=6),
            hovertemplate='Tým: %{name}<br>Kolo %{x}<br>Body %{y}<extra></extra>'
        ))
    add_hide_show(fig, len(points_df.columns), "Scatter bodů")
    fig.update_layout(
        title="Bodový scatter – body týmů v jednotlivých kolech",
        xaxis=dict(title="Kolo", tickmode="linear", dtick=1, range=[1, max_rounds]),
        yaxis_title="Body",
        hovermode="closest"
    )
    st.plotly_chart(fig, use_container_width=True)
