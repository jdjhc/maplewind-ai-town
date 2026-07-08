"""
Maplewind Hollow — an AI-driven cosy town (Streamlit demo)
==========================================================
Chat with LLM-powered villagers. Ask the shopkeeper for work and she'll
procedurally generate a social quest; solve it by TALKING to the right
villager; the story and everyone's opinion of you shift as you go.

Run:
    pip install -r requirements.txt
    # put your key in .streamlit/secrets.toml  (see README)
    streamlit run app.py
"""
import streamlit as st
import npc_engine as eng

st.set_page_config(page_title="Maplewind Hollow — AI Town", page_icon="🌾",
                   layout="wide")

# ---- session state ----
if "world" not in st.session_state:
    st.session_state.world = eng.new_world()
if "npc" not in st.session_state:
    st.session_state.npc = "marla"
world = st.session_state.world
world.setdefault("pending_choices", {nid: [] for nid in eng.NPCS})

# ---- header ----
st.title("🌾 Maplewind Hollow")
st.caption("A cosy town where every villager is an AI agent. "
           "Talk to them, take on quests, watch the story bend around your choices.")

# ==========================================================================
# Sidebar — live world state (the 'rules layer' made visible)
# ==========================================================================
with st.sidebar:
    st.header("🧭 World State")
    p = world["player"]
    st.metric("Gold", p["gold"])

    st.subheader("Reputation")
    for nid, npc in eng.NPCS.items():
        rep = p["reputation"].get(nid, 0)
        st.write(f"**{npc['name'].split()[0]}**")
        st.progress(max(0.0, min(1.0, (rep + 30) / 60)),
                    text=f"{rep:+d}")

    st.subheader("Inventory")
    st.write("• " + "\n• ".join(p["inventory"]) if p["inventory"] else "_empty_")

    st.subheader("Quests")
    if not world["quests"]:
        st.write("_none yet — ask Marla for work_")
    for q in world["quests"]:
        icon = {"done": "✅", "active": "🟡",
                "offered": "📜", "declined": "🚫"}.get(q["status"], "🟡")
        tgt = eng.NPCS[q["target_npc"]]["name"].split()[0]
        st.write(f"{icon} **{q['title']}** → talk to {tgt}")
        if q["status"] == "active":
            st.caption(q["success_condition"])
        elif q["status"] == "offered":
            st.caption(f"offered — {q['reward'].get('gold', 0)} gold; "
                       "answer Marla to accept or decline")

    st.divider()
    if world["log"]:
        st.subheader("Event log")
        for line in world["log"][-8:][::-1]:
            st.caption(line)

    st.divider()
    if st.button("🔄 Reset town"):
        st.session_state.world = eng.new_world()
        st.rerun()

# ==========================================================================
# Main — choose a villager + chat
# ==========================================================================
cols = st.columns(len(eng.NPCS) + 1)
for i, (nid, npc) in enumerate(eng.NPCS.items()):
    label = ("🧺 " if nid == "marla" else "🔨 " if nid == "odell" else "⛏️ ") \
        + npc["name"].split()[0]
    if cols[i].button(label, use_container_width=True,
                      type="primary" if st.session_state.npc == nid else "secondary"):
        st.session_state.npc = nid
        st.rerun()

# "Ask for a quest" — visible procedural generation, only at Marla
if st.session_state.npc == "marla":
    offer_pending = any(q["status"] == "offered" for q in world["quests"])
    if cols[-1].button("🗒️ Ask for work", use_container_width=True,
                       disabled=offer_pending,
                       help="Answer Marla's current offer first"
                       if offer_pending else None):
        with st.spinner("Marla thinks of an errand…"):
            q = eng.generate_quest(world)
        # let Marla introduce it in-character
        world["history"]["marla"].append(
            {"role": "assistant",
             "content": f"({q['description']})"})
        st.rerun()

npc_id = st.session_state.npc
npc = eng.NPCS[npc_id]
st.subheader(f"{npc['name']} — {npc['role']}")

# render conversation
for msg in world["history"][npc_id]:
    with st.chat_message("user" if msg["role"] == "user" else "assistant"):
        st.write(msg["content"])


def say(text):
    """Send one player line (typed or clicked) to the current NPC."""
    world["pending_choices"][npc_id] = []
    with st.chat_message("user"):
        st.write(text)
    with st.chat_message("assistant"):
        with st.spinner("…"):
            try:
                reply, effects = eng.npc_reply(npc_id, text, world)
            except Exception as e:
                st.error(f"DeepSeek call failed: {e}")
                st.stop()
        st.write(reply)
    st.rerun()


# quick-reply choices proposed for this moment (click instead of typing)
choices = world["pending_choices"].get(npc_id, [])
if choices:
    st.caption("Quick replies — or type your own below")
    for i, choice in enumerate(choices):
        if st.button(f"💬 {choice}", key=f"choice_{npc_id}_{i}",
                     use_container_width=True):
            say(choice)

# input
prompt = st.chat_input(f"Say something to {npc['name'].split()[0]}…")
if prompt:
    say(prompt)
