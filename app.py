"""
Maplewind Hollow — an AI-driven cosy town (Streamlit demo)
==========================================================
Visual-novel presentation: character portraits react to the conversation
(mood comes from each NPC's hidden @@STATE@@ block), dialogue shows in a
VN-style box, and the player answers via generated choice buttons or
free-typed text.

Run:
    pip install -r requirements.txt
    # put your key in .streamlit/secrets.toml  (see README)
    streamlit run app.py
"""
import html
import re

import streamlit as st

import npc_engine as eng
import sprites

st.set_page_config(page_title="Maplewind Hollow — AI Town", page_icon="🌾",
                   layout="wide")

# ---- session state ----
if "world" not in st.session_state:
    st.session_state.world = eng.new_world()
if "npc" not in st.session_state:
    st.session_state.npc = "marla"
world = st.session_state.world
world.setdefault("pending_choices", {nid: [] for nid in eng.NPCS})
world.setdefault("mood", {nid: "neutral" for nid in eng.NPCS})

# ---- visual-novel styling ----
VN_CSS = """
<style>
.vn-scene{position:relative;height:470px;border-radius:16px;overflow:hidden;
  box-shadow:0 6px 24px rgba(0,0,0,.28);}
.vn-sprite{position:absolute;left:50%;bottom:118px;width:265px;
  transform:translateX(-50%);transform-origin:50% 100%;}
.vn-sprite svg{width:100%;height:auto;display:block;
  filter:drop-shadow(0 8px 14px rgba(0,0,0,.3));}
.vn-box{position:absolute;left:14px;right:14px;bottom:14px;min-height:104px;
  background:rgba(24,20,28,.84);border:1px solid rgba(255,255,255,.16);
  border-radius:12px;padding:16px 20px;color:#f4efe8;backdrop-filter:blur(3px);}
.vn-name{position:absolute;top:-16px;left:16px;padding:3px 16px;border-radius:8px;
  font-weight:700;color:#fff;font-size:.95rem;box-shadow:0 2px 6px rgba(0,0,0,.35);}
.vn-text{margin-top:8px;line-height:1.6;font-size:1.03rem;animation:vnfade .45s ease;}
.vn-text em{color:#c9b8e8;}
@keyframes vnfade{from{opacity:0;transform:translateY(5px)}to{opacity:1}}
@keyframes vn-idle{0%,100%{transform:translateX(-50%) scaleY(1)}
  50%{transform:translateX(-50%) scaleY(1.014)}}
@keyframes vn-bounce{0%,100%{transform:translateX(-50%) translateY(0)}
  30%{transform:translateX(-50%) translateY(-16px)}
  55%{transform:translateX(-50%) translateY(0)}
  75%{transform:translateX(-50%) translateY(-7px)}}
@keyframes vn-shake{0%,100%{transform:translateX(-50%)}
  20%{transform:translateX(calc(-50% - 9px))}40%{transform:translateX(calc(-50% + 9px))}
  60%{transform:translateX(calc(-50% - 6px))}80%{transform:translateX(calc(-50% + 6px))}}
@keyframes vn-pop{0%{transform:translateX(-50%) scale(.9)}
  55%{transform:translateX(-50%) scale(1.07)}100%{transform:translateX(-50%) scale(1)}}
@keyframes vn-droop{from{transform:translateX(-50%) translateY(0)}
  to{transform:translateX(-50%) translateY(9px)}}
@keyframes vn-sway{0%,100%{transform:translateX(-50%) rotate(0deg)}
  35%{transform:translateX(-50%) rotate(-2.5deg)}
  70%{transform:translateX(-50%) rotate(1.5deg)}}
.mood-neutral{animation:vn-idle 3.6s ease-in-out infinite;}
.mood-happy{animation:vn-bounce .9s ease;}
.mood-angry{animation:vn-shake .6s ease;}
.mood-surprised{animation:vn-pop .5s ease;}
.mood-sad{animation:vn-droop .9s ease forwards;}
.mood-shy{animation:vn-sway 1.7s ease;}
[class*="st-key-choice_"] button{width:100%;text-align:left;
  background:rgba(38,30,48,.92);color:#f0e8f8;border:1px solid rgba(255,255,255,.28);
  border-radius:10px;padding:.55rem 1.1rem;}
[class*="st-key-choice_"] button:hover{background:#5a4a7a;border-color:#c9b8e8;
  color:#fff;}
</style>
"""
st.markdown(VN_CSS, unsafe_allow_html=True)

BACKDROPS = {
    # general store: warm timber + lamplight
    "marla": ("radial-gradient(ellipse at 20% 15%, rgba(255,220,150,.55), "
              "transparent 45%), linear-gradient(180deg,#e8c48e 0%,#c99a63 55%,"
              "#8f6a42 100%)"),
    # forge: dark iron + ember glow
    "odell": ("radial-gradient(ellipse at 50% 100%, rgba(255,130,40,.55), "
              "transparent 55%), linear-gradient(180deg,#4a4038 0%,#2e2620 100%)"),
    # hillside: sky over meadow
    "wren": ("linear-gradient(180deg,#a5d8ec 0%,#cde8cf 58%,#82ac66 100%)"),
}
NAME_COLORS = {"marla": "#c06b46", "odell": "#5a6b7a", "wren": "#7c5cbf"}

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
# Main — choose a villager + visual-novel scene
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
            last_said = next((m["content"] for m in
                              reversed(world["history"]["marla"])
                              if m["role"] == "user"), None)
            q = eng.generate_quest(world, lang_sample=last_said)
        # let Marla introduce it in-character
        world["history"]["marla"].append(
            {"role": "assistant",
             "content": f"({q['description']})"})
        st.rerun()

npc_id = st.session_state.npc
npc = eng.NPCS[npc_id]


def _vn_html(text):
    """Markdown-ish NPC line -> safe HTML for the dialogue box."""
    t = html.escape(text)
    t = re.sub(r"\*([^*\n]+)\*", r"<em>\1</em>", t)
    return t.replace("\n\n", "<br>").replace("\n", "<br>")


hist = world["history"][npc_id]
last_line = next((m["content"] for m in reversed(hist) if m["role"] == "assistant"),
                 None) or f"*{npc['name']} looks up as you approach.*"
mood = world["mood"].get(npc_id, "neutral")

st.markdown(
    f'<div class="vn-scene" style="background:{BACKDROPS[npc_id]}">'
    f'  <div class="vn-sprite mood-{mood}">{sprites.sprite_svg(npc_id, mood)}</div>'
    f'  <div class="vn-box">'
    f'    <div class="vn-name" style="background:{NAME_COLORS[npc_id]}">'
    f'{npc["name"]} <span style="opacity:.75;font-weight:400">· {npc["role"]}</span>'
    f'</div>'
    f'    <div class="vn-text">{_vn_html(last_line)}</div>'
    f'  </div>'
    f'</div>',
    unsafe_allow_html=True)


def say(text):
    """Send one player line (typed or clicked) to the current NPC."""
    world["pending_choices"][npc_id] = []
    with st.spinner(f"{npc['name'].split()[0]} is thinking…"):
        try:
            reply, effects = eng.npc_reply(npc_id, text, world)
        except Exception as e:
            st.error(f"DeepSeek call failed: {e}")
            st.stop()
    # the player said they're off to see someone else -> change scene,
    # and the villager there opens the conversation
    target = effects.get("go_to")
    if target in eng.NPCS and target != npc_id:
        st.session_state.npc = target
        st.toast(f"🚶 → {eng.NPCS[target]['name']}")
        with st.spinner(f"{eng.NPCS[target]['name'].split()[0]}…"):
            try:
                eng.npc_greet(target, world, lang_sample=text)
            except Exception:
                pass  # arrival still happens even if the greeting call fails
    st.rerun()


# quick-reply choices proposed for this moment (click instead of typing)
choices = world["pending_choices"].get(npc_id, [])
if choices:
    for i, choice in enumerate(choices):
        if st.button(f"▸ {choice}", key=f"choice_{npc_id}_{i}",
                     use_container_width=True):
            say(choice)

# free-typed input stays available
prompt = st.chat_input(f"Say something to {npc['name'].split()[0]}…")
if prompt:
    say(prompt)

# VN-style backlog
with st.expander("📖 Backlog — full conversation"):
    for msg in hist:
        who = "**You:**" if msg["role"] == "user" else f"**{npc['name']}:**"
        st.markdown(f"{who} {msg['content']}")
