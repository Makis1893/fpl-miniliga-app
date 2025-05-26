import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("Fantasy Premier League - Miniliga")

MINILIGA_ID = st.text_input("Zadej ID miniligy", value="36264")

@st.cache_data(show_spinner=False)
def fetch_miniliga_entries(miniliga_id):
    url = f"https://fantasy.premierleague.com/api/leagues-classic/{miniliga_id}/standings/"
    entries = []
    page = 1
    while True:
        r = requests.get(url, params={"page_standings": page})
        if r.status_code != 200:
            st.error(f"Chyba při načítání miniligy: {r.status_code}")
            return []
        data = r.json()
        page_entries = data.get("standings", {}).get("results", [])
        if not page_entries:
            break
        for e in page_entries:
            entries.append((e["entry"], e["player_name"]))
        if data.get("standings", {}).get("has_next", False):
            page += 1
        else:
            break
    return entries

@st.cache_data(show_spinner=False)
def fetch_team_history(entry_id):
    url = f"https://fantasy.premierleague.com/api/entry/{entry_id}/event-history/"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

if not MINILIGA_ID.strip():
    st.warning("Zadej ID miniligy pro načtení dat.")
    st.stop()

entries = fetch_miniliga_entries(MINILIGA_ID)
if not entries:
    st.error("Miniliga nenalezena nebo prázdná.")
    st.stop()

team_histories = {}
teams_no_history = []

with st.spinner(f"Načítám historii {len(entries)} týmů..."):
    for entry_id, name in entries:
        hist = fetch_team_history(entry_id)
        if hist is None:
            teams_no_history.append(name)
        else:
            team_histories[name] = hist

if teams_no_history:
    st.warning(f"Týmy bez dostupné historie: {', '.join(teams_no_history)}")
st.info(f"Načteno dat pro {len(team_histories)} týmů ze {len(entries)} v minilize.")

if not team_histories:
    st.error("Žádný tým nemá dostupnou historii, nelze zobrazit data.")
    st.stop()

MAX_EVENTS = 38

points_df = pd.DataFrame(index=range(1, MAX_EVENTS+1))
for team, hist in team_histories.items():
    df = pd.DataFrame(hist)
    df = df.set_index("event").reindex(range(1, MAX_EVENTS+1), fill_value=0)
    points_df[team] = df["points"]

cumulative_points = points_df.cumsum()

rank_df = pd.DataFrame(index=range(1, MAX_EVENTS+1))
for event in range(1, MAX_EVENTS+1):
    rank_df[event] = cumulative_points.loc[event].rank(ascending=False, method="min")
rank_df = rank_df.T
rank_df.columns = points_df.columns

tabs = st.tabs(["Vývoj bodů", "Vývoj pořadí", "Top 30 výkonů v kole", "Konečné pořadí"])

with tabs[0]:
    st.header("Vývoj bodů v jednotlivých kolech")
    vybrane_tymy = st.multiselect("Vyber týmy k zobrazení", points_df.columns.tolist(), default=points_df.columns.tolist())
    if vybrane_tymy:
        fig = go.Figure()
        for team in vybrane_tymy:
            fig.add_trace(go.Scatter(
                x=points_df.index,
                y=points_df[team],
                mode="lines+markers",
                name=team
            ))
        fig.update_layout(
            xaxis_title="Kolo",
            yaxis_title="Body v kole",
            xaxis=dict(tickmode="linear", dtick=1, range=[1, MAX_EVENTS]),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Vyber alespoň jeden tým.")

with tabs[1]:
    st.header("Vývoj pořadí v minilize (kumulativně)")
    vybrane_tymy_r = st.multiselect("Vyber týmy k zobrazení", rank_df.columns.tolist(), default=rank_df.columns.tolist())
    if vybrane_tymy_r:
        fig = go.Figure()
        for team in vybrane_tymy_r:
            fig.add_trace(go.Scatter(
                x=rank_df.index,
                y=rank_df[team],
                mode="lines+markers",
                name=team
            ))
        fig.update_layout(
            xaxis_title="Kolo",
            yaxis_title="Pořadí (1 = nejlepší)",
            yaxis=dict(autorange="reversed", dtick=1, range=[1, len(rank_df.columns)]),
            xaxis=dict(tickmode="linear", dtick=1, range=[1, MAX_EVENTS]),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Vyber alespoň jeden tým.")

with tabs[2]:
    st.header("Top 30 bodových výkonů v rámci jednoho kola")
    performances = []
    for team in points_df.columns:
        for event in points_df.index:
            performances.append({"Tým": team, "Kolo": event, "Body": points_df.loc[event, team]})
    perf_df = pd.DataFrame(performances)
    perf_df = perf_df.sort_values(by="Body", ascending=False).head(30).reset_index(drop=True)
    st.dataframe(perf_df.style.format({"Body": "{:.0f}", "Kolo": "{:.0f}"}), use_container_width=True)

with tabs[3]:
    st.header("Konečné pořadí v minilize")
    total_points = points_df.sum()
    final_rank = total_points.rank(method="min", ascending=False)
    final_df = pd.DataFrame({
        "Tým": total_points.index,
        "Body celkem": total_points.values,
        "Pořadí": final_rank.values.astype(int)
    }).sort_values("Pořadí")
    st.dataframe(final_df.reset_index(drop=True), use_container_width=True)
