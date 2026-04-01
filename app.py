import streamlit as st
from itertools import combinations
import json
import os

FILE = "players.json"

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

    def to_dict(self):
        return {
            "name": self.name,
            "gender": self.gender,
            "skill": self.skill
        }

# -------------------------
# Load / Save
# -------------------------
def load_players():
    if os.path.exists(FILE):
        with open(FILE) as f:
            data = json.load(f)
            return [Player(d["name"], d["gender"], d["skill"]) for d in data]

    return [
        Player("Jos", "M", 4),
        Player("Open", "F", 2),
        Player("Novi", "F", 2),
        Player("Cancaw", "M", 4),
        Player("Michelle", "F", 2),
        Player("Panjul", "M", 3),
        Player("Sendy", "M", 2),
    ]

def save_players(players):
    with open(FILE, "w") as f:
        json.dump([p.to_dict() for p in players], f)

# -------------------------
# Init state
# -------------------------
if "players" not in st.session_state:
    st.session_state.players = load_players()
    st.session_state.current_tick = 1
    st.session_state.last_pairs = set()
    st.session_state.match_history = []
    st.session_state.courts = [[], []]

players = st.session_state.players

# -------------------------
# Helpers
# -------------------------
def team_skill(team):
    return sum(p.skill for p in team)

def pair_key(team):
    return tuple(sorted(p.name for p in team))

def get_player(name):
    return next((p for p in players if p.name == name), None)

# -------------------------
# Match Logic
# -------------------------
def find_best_match():
    available = [p for p in players if not p.force_skip]
    if len(available) < 4:
        return None

    best = None
    best_score = float("inf")

    min_match = min(p.matches_played for p in available)
    priority_players = [p for p in available if p.priority]

    for group in combinations(available, 4):
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

            for team in [teamA, teamB]:
                for p in team:
                    for q in team:
                        if q.name in p.preferred:
                            score -= 80
                        if q.name in p.avoid:
                            score += 10000

            if score < best_score:
                best_score = score
                best = (teamA, teamB, group)

    return best

# -------------------------
# Actions
# -------------------------
def generate_match(court_id):
    match = find_best_match()
    if not match:
        st.warning("Not enough players")
        return

    teamA, teamB, group = match

    st.session_state.courts[court_id].append(
        f"Match {st.session_state.current_tick}: "
        f"{[p.name for p in teamA]} vs {[p.name for p in teamB]}"
    )

    st.session_state.match_history.append({
        "court": court_id,
        "teamA": teamA,
        "teamB": teamB,
        "players": group,
        "result": None
    })

    for p in group:
        p.matches_played += 1
        p.last_played_tick = st.session_state.current_tick
        p.priority = False

    st.session_state.last_pairs = {pair_key(teamA), pair_key(teamB)}
    st.session_state.current_tick += 1

def submit_result(court_id):
    for match in reversed(st.session_state.match_history):
        if match["court"] == court_id and match["result"] is None:

            a = st.session_state[f"a{court_id}"]
            b = st.session_state[f"b{court_id}"]

            match["result"] = (a, b)

            winners = match["teamA"] if a > b else match["teamB"]

            for p in match["players"]:
                if p in winners:
                    p.wins += 1
                else:
                    p.losses += 1

            # CLEAR INPUT
            st.session_state[f"a{court_id}"] = 0
            st.session_state[f"b{court_id}"] = 0
            return

def undo_last():
    if not st.session_state.match_history:
        return

    match = st.session_state.match_history.pop()

    for p in match["players"]:
        p.matches_played -= 1
        p.last_played_tick = -1

    if match["result"]:
        winners = match["teamA"] if match["result"][0] > match["result"][1] else match["teamB"]
        for p in match["players"]:
            if p in winners:
                p.wins -= 1
            else:
                p.losses -= 1

    st.session_state.current_tick -= 1

# -------------------------
# UI
# -------------------------
st.title("🏸 Badminton Matcher PRO")

# PLAYER MANAGEMENT
st.subheader("Players")

for i, p in enumerate(players):
    col1, col2, col3, col4 = st.columns([3,1,1,1])

    col1.write(f"{p.name} ({p.gender}) - {p.skill}")

    if col2.button("Skip", key=f"s{i}"):
        p.force_skip = not p.force_skip
        if p.force_skip: p.priority = False

    if col3.button("Priority", key=f"p{i}"):
        p.priority = not p.priority
        if p.priority: p.force_skip = False

    if col4.button("Delete", key=f"d{i}"):
        players.pop(i)
        save_players(players)
        st.rerun()

# ADD PLAYER
st.subheader("Add Player")
name = st.text_input("Name")
gender = st.selectbox("Gender", ["M", "F"])
skill = st.slider("Skill", 1, 5, 3)

if st.button("Add"):
    if name:
        players.append(Player(name, gender, skill))
        save_players(players)
        st.rerun()

# PREFER / AVOID
st.subheader("Preferences")

p1 = st.selectbox("Player", [p.name for p in players])
p2 = st.selectbox("Target", [p.name for p in players])

colA, colB = st.columns(2)

if colA.button("Add Preferred"):
    a, b = get_player(p1), get_player(p2)
    a.preferred.add(b.name)
    b.preferred.add(a.name)

if colB.button("Add Avoid"):
    a, b = get_player(p1), get_player(p2)
    a.avoid.add(b.name)
    b.avoid.add(a.name)

# COURTS
st.subheader("Courts")

for i in range(2):
    st.markdown(f"### Court {i+1}")

    if st.button("Next Match", key=f"m{i}"):
        generate_match(i)

    for m in st.session_state.courts[i]:
        st.write(m)

    col1, col2 = st.columns(2)
    col1.number_input("A", key=f"a{i}")
    col2.number_input("B", key=f"b{i}")

    if st.button("Submit Result", key=f"r{i}"):
        submit_result(i)

# LEADERBOARD
st.subheader("Leaderboard")
for p in sorted(players, key=lambda x: x.wins, reverse=True):
    total = p.wins + p.losses
    rate = (p.wins / total * 100) if total else 0
    st.write(f"{p.name}: {p.wins}W {p.losses}L ({rate:.1f}%)")

# UNDO
if st.button("Undo"):
    undo_last()
