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
# INIT
# -------------------------
def init_players():
    return [
        Player("Jos", "M", 4),
        Player("Open", "F", 2),
        Player("Novi", "F", 2),
        Player("Cancaw", "M", 4),
        Player("Michelle", "F", 2),
        Player("Panjul", "M", 3),
        Player("Sendy", "M", 2),
    ]

if "players" not in st.session_state:
    st.session_state.players = init_players()
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

def format_team(team):
    return " & ".join([p.name for p in team])

# -------------------------
# MATCH LOGIC (FIXED)
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

            # fairness
            for p in group:
                score += (p.matches_played - min_match) * 100

            # balance
            score += abs(team_skill(teamA) - team_skill(teamB)) * 5

            # avoid back-to-back
            for p in group:
                if p.last_played_tick == st.session_state.current_tick - 1:
                    score += 50

            # avoid repeating pairs
            if pair_key(teamA) in st.session_state.last_pairs:
                score += 100
            if pair_key(teamB) in st.session_state.last_pairs:
                score += 100

            # priority enforcement
            for p in priority_players:
                if p not in group:
                    score += 1000

            # preferred / avoid
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
# ACTIONS
# -------------------------
def generate_match(court_id):
    match = find_best_match()
    if not match:
        st.warning("Not enough players")
        return

    teamA, teamB, group = match

    text = f"Match {st.session_state.current_tick}: {format_team(teamA)} vs {format_team(teamB)}"

    st.session_state.courts[court_id].append(text)

    st.session_state.match_history.append({
        "court": court_id,
        "teamA": teamA,
        "teamB": teamB,
        "players": group,
        "result": None,
        "text": text
    })

    for p in group:
        p.matches_played += 1
        p.last_played_tick = st.session_state.current_tick
        p.priority = False  # one-time use

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

            # clear scores
            st.session_state[f"a{court_id}"] = 0
            st.session_state[f"b{court_id}"] = 0
            return

def undo_last():
    if not st.session_state.match_history:
        return

    match = st.session_state.match_history.pop()

    # remove from court UI
    if match["text"] in st.session_state.courts[match["court"]]:
        st.session_state.courts[match["court"]].remove(match["text"])

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

# PLAYERS
st.subheader("Players")

for i, p in enumerate(players):
    cols = st.columns([3,1,1,1])

    label = f"{p.name} ({p.gender}) | Skill {p.skill} | Played {p.matches_played}"

    if p.force_skip:
        label = "🔴 " + label
    elif p.priority:
        label = "🟡 " + label

    cols[0].write(label)

    if cols[1].button("Skip", key=f"s{i}"):
        p.force_skip = not p.force_skip
        if p.force_skip:
            p.priority = False

    if cols[2].button("Priority", key=f"p{i}"):
        p.priority = True
        p.force_skip = False

    if cols[3].button("Delete", key=f"d{i}"):
        players.pop(i)
        st.rerun()

# EDIT PLAYER
st.subheader("Edit Player")

names = [p.name for p in players]
selected = st.selectbox("Select Player", names)

p = next(x for x in players if x.name == selected)

new_name = st.text_input("Name", value=p.name)
new_gender = st.selectbox("Gender", ["M","F"], index=0 if p.gender=="M" else 1)
new_skill = st.slider("Skill", 1, 5, p.skill)

if st.button("Update Player"):
    p.name = new_name
    p.gender = new_gender
    p.skill = new_skill
    st.rerun()

# ADD PLAYER
st.subheader("Add Player")

name = st.text_input("New Name")
gender = st.selectbox("New Gender", ["M","F"])
skill = st.slider("New Skill", 1, 5, 3)

if st.button("Add Player"):
    if name:
        players.append(Player(name, gender, skill))
        st.rerun()

# COURTS
st.subheader("Courts")

for i in range(2):
    st.markdown(f"### Court {i+1}")

    if st.button("Next Match", key=f"m{i}"):
        generate_match(i)

    for m in st.session_state.courts[i]:
        st.write(m)

    col1, col2 = st.columns(2)
    col1.number_input("A", step=1, format="%d", key=f"a{i}")
    col2.number_input("B", step=1, format="%d", key=f"b{i}")

    if st.button("Submit Result", key=f"r{i}"):
        submit_result(i)

# LEADERBOARD
st.subheader("Leaderboard")

for p in sorted(players, key=lambda x: x.wins, reverse=True):
    total = p.wins + p.losses
    rate = (p.wins / total * 100) if total else 0
    st.write(f"{p.name}: {p.wins}W {p.losses}L ({rate:.1f}%)")

# UNDO
if st.button("Undo Last Match"):
    undo_last()
