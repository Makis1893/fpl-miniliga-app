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
def fetch_team_history_safe(entry_id):
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
teams_without_data = []

with st.spinner(f"Načítám historii {len(entries)} týmů miniligy..."):
    for entry_id, name in entries:
        history = fetch_team_history_safe(entry_id)
        if history is not None:
            team_histories[name] = history
        else:
            teams_without_data.append(name)

if teams_without_data:
    st.warning(f"Týmy bez dostupné historie: {', '.join(teams_without_data)}")
st.info(f"Načteno dat pro {len(team_histories)} týmů ze {len(entries)} v minilize.")

if not team_histories:
    st.error("Žádný tým nemá dostupnou historii, nelze zobrazit data.")
    st.stop()

# --- Připravíme data pro všechny týmy ---
max_event = 38  # počet kol

# Body za jednotlivá kola (vždy 38 kol)
points_df = pd.DataFrame(index=range(1, max_event+1))
for name, history in team_histories.items():
    df = pd.DataFrame(history)
    df = df.set_index("event").reindex(range(1, max_event+1), fill_value=0)
    points_df[name] = df["points"]

# Pořadí v minilize kumulativně (počítá se podle součtu bodů po každém kole)
ranks_df = pd.DataFrame(index=range(1, max_event+1))

for event in range(1, max_event+1):
    cum_points = points_df.loc[:event].sum()
    rank = cum_points.rank(method="min", ascending=False)
    ranks_df[event] = rank

ranks_df = ranks_df.T

tabs = st.tabs(["Vývoj bodů", "Vývoj pořadí", "Top 30 výkonů v kole", "Konečné pořadí"])

with tabs[0]:
    st.header("Vývoj bodů v minilize")
    selected_teams = st.multiselect("Vyber týmy k zobrazení (výchozí: všechny)", list(points_df.columns), default=list(points_df.columns))
    if selected_teams:
        fig = go.Figure()
        for team in selected_teams:
            fig.add_trace(go.Scatter(
                x=points_df.index,
                y=points_df[team],
                mode="lines+markers",
                name=team,
            ))
        fig.update_layout(
            xaxis_title="Kolo",
            yaxis_title="Body v kole",
            xaxis=dict(tickmode="linear", dtick=1, range=[1, max_event]),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Vyber alespoň jeden tým pro zobrazení grafu.")

with tabs[1]:
    st.header("Vývoj pořadí v minilize (kumulativně)")
    selected_teams_ranks = st.multiselect("Vyber týmy k zobrazení (výchozí: všechny)", list(ranks_df.columns), default=list(ranks_df.columns))
    if selected_teams_ranks:
        fig = go.Figure()
        for team in selected_teams_ranks:
            fig.add_trace(go.Scatter(
                x=ranks_df.index,
                y=ranks_df[team],
                mode="lines+markers",
                name=team,
                yaxis="y"
            ))
        fig.update_layout(
            xaxis_title="Kolo",
            yaxis_title="Pořadí (1 = nejlepší)",
            yaxis=dict(autorange="reversed", dtick=1, range=[1, len(ranks_df.columns)]),
            xaxis=dict(tickmode="linear", dtick=1, range=[1, max_event]),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Vyber alespoň jeden tým pro zobrazení grafu.")

with tabs[2]:
    st.header("Top 30 bodových výkonů v rámci jednoho kola")
    performances = []
    for team in points_df.columns:
        for event in points_df.index:
            performances.append({"team": team, "event": event, "points": points_df.loc[event, team]})
    perf_df = pd.DataFrame(performances)
    perf_df = perf_df.sort_values(by="points", ascending=False).head(30).reset_index(drop=True)
    st.dataframe(perf_df.style.format({"points": "{:.0f}", "event": "{:.0f}"}), use_container_width=True)

with tabs[3]:
    st.header("Konečné pořadí v minilize")
    final_points = points_df.sum()
    final_ranks = final_points.rank(method="min", ascending=False)
    final_df = pd.DataFrame({
        "Tým": final_points.index,
        "Body celkem": final_points.values,
        "Pořadí": final_ranks.values.astype(int)
    })
    final_df = final_df.sort_values("Pořadí")
    st.dataframe(final_df.reset_index(drop=True), use_container_width=True)
