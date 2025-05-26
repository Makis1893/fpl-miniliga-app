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
    r = requests.get(url); r.raise_for_status()
    data = r.json()
    return [(e['entry'], e['entry_name']) for e in data['standings']['results']]

@st.cache_data
def fetch_team_history(entry_id):
    url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/history/"
    r = requests.get(url); r.raise_for_status()
    return r.json().get('current', [])

entries = fetch_league_data(league_id)
max_rounds = 38

# 1) body za jednotlivá kola
points_df = pd.DataFrame(index=range(1, max_rounds+1))
for eid, name in entries:
    hist = fetch_team_history(eid)
    pts = [gw.get('event_points',0) for gw in hist]
    pts += [0]*(max_rounds - len(pts))
    points_df[name] = pts

# 2) kumulativní body pro pořadí
cum_df = points_df.cumsum()

tabs = st.tabs([
    "1️⃣ Vývoj bodů",
    "2️⃣ Vývoj pořadí",
    "3️⃣ Top 30 výkonů",
    "4️⃣ Aktuální pořadí",
    "5️⃣ Vývoj hodnoty",
    "6️⃣ Body v kolech"
])

# Tab 1
with tabs[0]:
    fig = go.Figure()
    for team in points_df.columns:
        fig.add_trace(go.Scatter(
            x=points_df.index, y=points_df[team], mode='lines+markers', name=team
        ))
    fig.update_layout(
        updatemenus=[dict(type="buttons",direction="left",buttons=[
            dict(label="Hide all",method="update",
                 args=[{"visible": ["legendonly"]*len(points_df.columns)},
                       {"title":"Všechny čáry skryty"}]),
            dict(label="Show all",method="update",
                 args=[{"visible": [True]*len(points_df.columns)},
                       {"title":"Vývoj bodů"}])
        ],pad={"r":10,"t":10},showactive=False,x=0,xanchor="left",y=1.25,yanchor="top")],
        legend=dict(orientation="h",yanchor="bottom",y=1.2,xanchor="right",x=1),
        margin=dict(l=40,r=40,t=120,b=40),autosize=False,height=600,
        title="Vývoj bodů v kolech", xaxis_title="Kolo", yaxis_title="Body",
        xaxis=dict(tickmode="linear",dtick=1,range=[1,max_rounds]),hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

# Tab 2
with tabs[1]:
    ranks = cum_df.rank(axis=1,method='min',ascending=False).astype(int)
    fig = go.Figure()
    for team in ranks.columns:
        fig.add_trace(go.Scatter(
            x=ranks.index, y=ranks[team], mode='lines+markers', name=team
        ))
    fig.update_layout(
        updatemenus=[dict(type="buttons",direction="left",buttons=[
            dict(label="Hide all",method="update",
                 args=[{"visible": ["legendonly"]*len(ranks.columns)},
                       {"title":"Všechny čáry skryty"}]),
            dict(label="Show all",method="update",
                 args=[{"visible": [True]*len(ranks.columns)},
                       {"title":"Vývoj pořadí"}])
        ],pad={"r":10,"t":10},showactive=False,x=0,xanchor="left",y=1.25,yanchor="top")],
        legend=dict(orientation="h",yanchor="bottom",y=1.2,xanchor="right",x=1),
        margin=dict(l=40,r=40,t=120,b=40),autosize=False,height=600,
        title="Vývoj kumulativního pořadí", xaxis_title="Kolo", yaxis_title="Pořadí",
        xaxis=dict(tickmode="linear",dtick=1,range=[1,max_rounds]),
        yaxis=dict(autorange="reversed",dtick=1,range=[1,len(ranks.columns)]),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

# Tab 3
with tabs[2]:
    perf=[]
    for eid,name in entries:
        hist=fetch_team_history(eid)
        for gw in hist:
            pts=gw.get('event_points') or gw.get('points') or 0
            perf.append({"Tým":name,"Kolo":gw.get('event'),"Body":pts})
    dfp=pd.DataFrame(perf).sort_values("Body",ascending=False).head(30).reset_index(drop=True)
    dfp.index+=1; dfp.index.name="Pořadí"
    st.table(dfp)

# Tab 4
with tabs[3]:
    final=[{"Tým":name,"Body celkem":fetch_team_history(eid)[-1].get('total_points',0)} for eid,name in entries]
    dff=pd.DataFrame(final).sort_values("Body celkem",ascending=False).reset_index(drop=True)
    dff.index+=1; dff.index.name="Pořadí"
    st.table(dff)

# Tab 5
with tabs[4]:
    val={}
    for eid,name in entries:
        hist=fetch_team_history(eid)
        v=[gw.get('value',0) for gw in hist]
        v+=[v[-1] if v else 0]*(max_rounds-len(v))
        val[name]=[x/10 for x in v]
    dfv=pd.DataFrame(val,index=range(1,max_rounds+1))
    fig=go.Figure()
    for team in dfv.columns:
        fig.add_trace(go.Scatter(
            x=dfv.index,y=dfv[team],mode='lines+markers',name=team
        ))
    fig.update_layout(
        updatemenus=[dict(type="buttons",direction="left",buttons=[
            dict(label="Hide all",method="update",
                 args=[{"visible": ["legendonly"]*len(dfv.columns)},
                       {"title":"Všechny čáry skryty"}]),
            dict(label="Show all",method="update",
                 args=[{"visible": [True]*len(dfv.columns)},
                       {"title":"Vývoj hodnoty"}])
        ],pad={"r":10,"t":10},showactive=False,x=0,xanchor="left",y=1.25,yanchor="top")],
        legend=dict(orientation="h",yanchor="bottom",y=1.2,xanchor="right",x=1),
        margin=dict(l=40,r=40,t=120,b=40),autosize=False,height=600,
        title="Vývoj hodnoty týmu (M£)", xaxis_title="Kolo", yaxis_title="Hodnota [M£]",
        xaxis=dict(tickmode="linear",dtick=1,range=[1,max_rounds]),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

# Tab 6: heatmapa bodů v kolech
with tabs[5]:
    fig = go.Figure(data=go.Heatmap(
        z=points_df.T.values,
        x=points_df.index,
        y=points_df.columns,
        colorscale="Viridis"
    ))
    fig.update_layout(
        title="Body týmů v jednotlivých kolech (heatmapa)",
        xaxis_title="Kolo",
        yaxis_title="Tým",
        margin=dict(l=120,r=40,t=80,b=40),
        autosize=False,
        height=800
    )
    st.plotly_chart(fig, use_container_width=True)
