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
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    return [(e['entry'], e['entry_name']) for e in data['standings']['results']]

@st.cache_data
def fetch_team_history(entry_id):
    url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/history/"
    r = requests.get(url)
    r.raise_for_status()
    return r.json().get('current', [])

tabs = st.tabs([
    "1️⃣ Vývoj bodů",
    "2️⃣ Vývoj pořadí",
    "3️⃣ Top 30 výkonů",
    "4️⃣ Aktuální pořadí",
    "5️⃣ Vývoj hodnoty"
])

# --- Tab 1: Vývoj bodů ---
with tabs[0]:
    entries = fetch_league_data(league_id)
    df = pd.DataFrame()
    max_rounds = 38
    for eid, name in entries:
        hist = fetch_team_history(eid)
        pts = [gw.get('total_points',0) for gw in hist]
        pts += [pts[-1] if pts else 0] * (max_rounds - len(pts))
        df[name] = pts
    df.index = range(1, max_rounds+1)
    fig = go.Figure()
    for team in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[team], mode='lines+markers', name=team))
    fig.update_layout(
        updatemenus=[dict(
            type="buttons",direction="left",
            buttons=[
                dict(label="Hide all", method="update",
                     args=[{"visible": ["legendonly"]*len(df.columns)},
                           {"title":"Všechny čáry skryty"}]),
                dict(label="Show all", method="update",
                     args=[{"visible": [True]*len(df.columns)},
                           {"title":"Vývoj bodů"}])
            ],pad={"r":10,"t":10},
            showactive=False,x=0,y=1.25,xanchor="left",yanchor="top"
        )],
        legend=dict(orientation="h",yanchor="bottom",y=1.2,xanchor="right",x=1),
        margin=dict(l=40,r=40,t=120,b=40),
        autosize=False,height=600,
        title="Vývoj bodů", xaxis_title="Kolo", yaxis_title="Body v kole",
        xaxis=dict(tickmode="linear",dtick=1,range=[1,max_rounds]),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Tab 2: Vývoj pořadí ---
with tabs[1]:
    entries = fetch_league_data(league_id)
    max_rounds = 38
    cum = {}
    for eid, name in entries:
        hist = fetch_team_history(eid)
        total=0; vals=[]
        for gw in hist:
            pts=gw.get('event_points') or gw.get('points') or 0
            total+=pts; vals.append(total)
        vals += [vals[-1] if vals else 0]*(max_rounds-len(vals))
        cum[name]=vals
    dfc = pd.DataFrame(cum, index=range(1,max_rounds+1))
    ranks = dfc.rank(axis=1,method='min',ascending=False).astype(int)
    fig = go.Figure()
    for team in ranks.columns:
        fig.add_trace(go.Scatter(x=ranks.index,y=ranks[team],mode='lines+markers',name=team))
    fig.update_layout(
        updatemenus=[dict(
            type="buttons",direction="left",
            buttons=[
                dict(label="Hide all", method="update",
                     args=[{"visible": ["legendonly"]*len(ranks.columns)},
                           {"title":"Všechny čáry skryty"}]),
                dict(label="Show all", method="update",
                     args=[{"visible": [True]*len(ranks.columns)},
                           {"title":"Vývoj pořadí"}])
            ],pad={"r":10,"t":10},
            showactive=False,x=0,y=1.25,xanchor="left",yanchor="top"
        )],
        legend=dict(orientation="h",yanchor="bottom",y=1.2,xanchor="right",x=1),
        margin=dict(l=40,r=40,t=120,b=40),
        autosize=False,height=600,
        title="Vývoj pořadí (kumulativně)", xaxis_title="Kolo", yaxis_title="Pořadí",
        xaxis=dict(tickmode="linear",dtick=1,range=[1,max_rounds]),
        yaxis=dict(autorange="reversed",dtick=1,range=[1,len(ranks.columns)]),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Tab 3: Top 30 výkonů ---
with tabs[2]:
    entries = fetch_league_data(league_id)
    perf=[]
    for eid,name in entries:
        hist=fetch_team_history(eid)
        for gw in hist:
            pts=gw.get('event_points') or gw.get('points') or 0
            perf.append({"Tým":name,"Kolo":gw.get('event'),"Body":pts})
    dfp=pd.DataFrame(perf).sort_values("Body",ascending=False).head(30).reset_index(drop=True)
    dfp.index+=1; dfp.index.name="Pořadí"
    st.table(dfp)

# --- Tab 4: Aktuální pořadí ---
with tabs[3]:
    entries = fetch_league_data(league_id)
    teams=[]
    for eid,name in entries:
        hist=fetch_team_history(eid)
        total=hist[-1].get('total_points',0) if hist else 0
        teams.append({"Tým":name,"Body celkem":total})
    dft=pd.DataFrame(teams).sort_values("Body celkem",ascending=False).reset_index(drop=True)
    dft.index+=1; dft.index.name="Pořadí"
    st.table(dft)

# --- Tab 5: Vývoj hodnoty týmu ---
with tabs[4]:
    entries = fetch_league_data(league_id)
    values = {}
    for eid,name in entries:
        hist = fetch_team_history(eid)
        val = [gw.get('value', 0) for gw in hist]
        val += [val[-1] if val else 0]*(38-len(val))
        # API vrací hodnotu v tisících: 1000 = 10.00
        values[name] = [v/10 for v in val]  # převedeme na miliony např. 1000→100.0
    dfv = pd.DataFrame(values, index=range(1,39))
    fig = go.Figure()
    for team in dfv.columns:
        fig.add_trace(go.Scatter(x=dfv.index,y=dfv[team],mode='lines+markers',name=team))
    fig.update_layout(
        updatemenus=[dict(
            type="buttons",direction="left",
            buttons=[
                dict(label="Hide all", method="update",
                     args=[{"visible": ["legendonly"]*len(dfv.columns)},
                           {"title":"Všechny čáry skryty"}]),
                dict(label="Show all", method="update",
                     args=[{"visible": [True]*len(dfv.columns)},
                           {"title":"Vývoj hodnoty"}])
            ],pad={"r":10,"t":10},
            showactive=False,x=0,y=1.25,xanchor="left",yanchor="top"
        )],
        legend=dict(orientation="h",yanchor="bottom",y=1.2,xanchor="right",x=1),
        margin=dict(l=40,r=40,t=120,b=40),
        autosize=False,height=600,
        title="Vývoj hodnoty týmu (miliony £)", xaxis_title="Kolo", yaxis_title="Hodnota [M£]",
        xaxis=dict(tickmode="linear",dtick=1,range=[1,38]),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
