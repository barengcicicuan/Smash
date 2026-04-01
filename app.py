import streamlit as st
from itertools import combinations

# -------------------------
# Player
# -------------------------
class Player:
    def __init__(self, name, gender, skill):
        self.name = name
        self.gender = gender
        self.skill = int(skill)

        self.matches_played = 0
        self.last_played_tick = -1
        self.force_skip = False
        self.priority = False
        self.wins = 0
        self.losses = 0
        self.preferred = set()
        self.avoid = set()

# -------------------------
# Session State (IMPORTANT)
# -------------------------
if "players" not in st.session_state:
    st.session_state.players = []
    st.session_state.current_tick = 1
    st.session_state.last_pairs = set()
    st.session_state.match_history = []

players = st.session_state.players

# -------------------------
# Helpers
# -------------------------
def team_skill(team):
    return sum(p.skill for p in team)

def pair_key(team):
    return tuple(sorted(p.name for p in team))

# -------------------------
# Matching Logic (same as yours)
# -------------------------
def find_best_match():
    available_players = [p for p in players if not p.force_skip]

    if len(available_players) < 4:
        return None

    best = None
    best_score = float("inf")

    min_match = min(p.matches_played for p in available_players)
    priority_players = [p for p in available_players if p.priority]

    for group in combinations(available_players, 4):
        for teamA in combinations(group, 2):
            teamB = tuple(p for p in group if p not in teamA)

            score = 0

            for p in group:
                score += (p.matches_played - min_match) * 100

            score += abs(team_skill(teamA) - team_skill(teamB)) * 5

            for p in group:
                if p.last_played_tick == st.session_state.current_tick - 1:
                    score += 50

            if pair_key(teamA) in st.session_state.last_pairs:
                score += 40
            if pair_key(teamB) in st.session_state.last_pairs:
                score += 40

            for p in priority_players:
                if p not in group:
                    score += 1000

            if score < best_score:
                best_score = score
                best = (teamA, teamB, group)

    return best

# -------------------------
# UI
# -------------------------
st.title("🏸 Badminton Matcher")

# Add player
st.subheader("Add Player")
name = st.text_input("Name")
gender = st.selectbox("Gender", ["M", "F"])
skill = st.slider("Skill", 1, 5, 3)

if st.button("Add Player"):
    players.append(Player(name, gender, skill))

# Show players
st.subheader("Players")
for p in players:
    st.write(f"{p.name} ({p.gender}) - Skill {p.skill}")

# Generate match
if st.button("Generate Match"):
    match = find_best_match()
    if match:
        teamA, teamB, _ = match
        st.success(f"{[p.name for p in teamA]} vs {[p.name for p in teamB]}")
    else:
        st.warning("Not enough players")