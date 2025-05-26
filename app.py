import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="FPL Miniliga – Analýzy", layout="wide")
st.title("📊 Fantasy Premier League – Analýzy miniligy")

league_id = st.number_input("Zadej ID miniligy (např. 36264):", min_value=1, value=36264, step=1)
max_rounds = 38

@st.cache_data
def fetch_league_data(lid):
    url = f"https://fantasy.premierleague.com/api/leagues-classic/{lid}/standings/"
    r = requests.get(url); r.raise_for_status()
    data = r.json()
    return [(e["entry"], e["entry_name"]) for e in data["standings"]["results"]]

@st.cache_data
def fetch_team_history(eid):
    url = f"https://fantasy.premierleague.com/api/entry/{eid}/history/"
    r = requests.get(url); r.raise_for_status()
    return r.json().get("current", [])

# 1) Načti seznam týmů
entries = fetch_league_data(league_id)

# 2) Sestav DataFrame bodů (za každé kolo použijeme key "points")
points_df = pd.DataFrame(index=range(1, max_rounds+1))
value_df  = pd.DataFrame(index=range(1, max_rounds+1))
for eid, name in entries:
    hist = fetch_team_history(eid)
    pts  = [gw.get("points", 0) for gw in hist]
    vals = [gw.get("value",  0) for gw in hist]
    # doplnění na 38 kol
    pts  += [0] * (max_rounds - len(pts))
    vals += [vals[-1] if vals else 0] * (max_rounds - len(vals))
    points_df[name] = pts
    # převod value z pencí na M£
    value_df[name]  = [v/10 for v in vals]

# 3) Kumulativní součty pro pořadí
cum_df = points_df.cumsum()

# Utility pro přidání tlačítek nad grafem
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
    "1️⃣ Vývoj bodů",
    "2️⃣ Vývoj pořadí",
    "3️⃣ Top 30 výkonů",
    "4️⃣ Aktuální pořadí",
    "5️⃣ Vývoj hodnoty",
    "6️⃣ Body v kolech (scatter)"
])

# Tab 1: Vývoj bodů
with tabs[0]:
    fig = go.Figure()
    for team in points_df.columns:
        fig.add_trace(go.Scatter(
            x=points_df.index, y=points_df[team],
            mode="lines+markers", name=team
        ))
    add_hide_show(fig, len(points_df.columns), "Vývoj bodů")
    fig.update_layout(
        title="Vývoj bodů v jednotlivých kolech",
        xaxis_title="Kolo", yaxis_title="Body",
        xaxis=dict(tickmode="linear", dtick=1, range=[1, max_rounds]),
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
        title="Vývoj kumulativního pořadí",
        xaxis_title="Kolo", yaxis_title="Pořadí",
        xaxis=dict(tickmode="linear", dtick=1, range=[1, max_rounds]),
        yaxis=dict(autorange="reversed", dtick=1, range=[1, len(ranks.columns)]),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

# Tab 3: Top 30 výkonů v kole
with tabs[2]:
    perf = []
    for eid, name in entries:
        hist = fetch_team_history(eid)
        for gw in hist:
            pts = gw.get("points", 0)
            perf.append({"Tým": name, "Kolo": gw.get("event"), "Body": pts})
    dfp = pd.DataFrame(perf).sort_values("Body", ascending=False).head(30).reset_index(drop=True)
    dfp.index += 1; dfp.index.name = "Pořadí"
    st.table(dfp)

# Tab 4: Aktuální pořadí
with tabs[3]:
    final = []
    for eid, name in entries:
        hist = fetch_team_history(eid)
        total = hist[-1].get("total_points", 0) if hist else 0
        final.append({"Tým": name, "Body celkem": total})
    dff = pd.DataFrame(final).sort_values("Body celkem", ascending=False).reset_index(drop=True)
    dff.index += 1; dff.index.name = "Pořadí"
    st.table(dff)

# Tab 5: Vývoj hodnoty
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
        xaxis_title="Kolo", yaxis_title="Hodnota [M£]",
        xaxis=dict(tickmode="linear", dtick=1, range=[1, max_rounds]),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

# Tab 6: Scatter bodů v kolech
with tabs[5]:
    fig = go.Figure()
    for team in points_df.columns:
        fig.add_trace(go.Scatter(
            x=points_df.index, y=points_df[team],
            mode="markers", name=team,
            marker=dict(size=6),
            hovertemplate='Tým: %{legendgroup}<br>Kolo %{x}<br>Body %{y}<extra></extra>',
            legendgroup=team
        ))
    add_hide_show(fig, len(points_df.columns), "Scatter bodů v kolech")
    fig.update_layout(
        title="Bodový scatter – body týmů v jednotlivých kolech",
        xaxis_title="Kolo", yaxis_title="Body",
        xaxis=dict(tickmode="linear", dtick=1, range=[1, max_rounds]),
        hovermode="closest"
    )
    st.plotly_chart(fig, use_container_width=True)
