"""
Maplewind Hollow — AI NPC engine (DeepSeek)
============================================
A cosy small-town simulation where every villager is an LLM-driven agent.
Demonstrates three pillars of AI in games:

  1. NPC interactions      — villagers with persistent personality + memory
  2. Procedural content    — quests generated on the fly from the world state
  3. Dynamic narrative     — the story branches on player choices; villagers
                             share a world state, so what you do with one
                             changes how the others treat you

Design principle (the important bit for a games PM):
    The LLM handles the CREATIVE layer (dialogue, quest flavour, narration).
    Deterministic code handles the RULES layer (quest completion, rewards,
    reputation). Every turn runs two passes — an in-character ACTOR reply,
    then a hidden JSON-mode DIRECTOR call that rules on mood, choices and
    quest events; code applies the ruling — "AI proposes, code disposes."

Characters are ORIGINAL, only *inspired by* the archetypes of a well-known
farming game (renamed to avoid any IP issues).
"""

import os
import re
import json
import copy
import time
from openai import OpenAI

MODEL = "deepseek-chat"
BASE_URL = "https://api.deepseek.com"

# per-API-call telemetry (site, latency, tokens) — used by eval/eval_director.py
CALL_LOG = []


def _chat(client, site, **kwargs):
    t0 = time.time()
    resp = client.chat.completions.create(**kwargs)
    usage = getattr(resp, "usage", None)
    CALL_LOG.append({
        "site": site,
        "seconds": round(time.time() - t0, 3),
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
    })
    return resp


# --------------------------------------------------------------------------
# API client — key is read from Streamlit secrets or env var, never hardcoded
# --------------------------------------------------------------------------
def get_client():
    key = None
    try:
        import streamlit as st
        key = st.secrets.get("DEEPSEEK_API_KEY", None)
    except Exception:
        pass
    key = key or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError(
            "No DeepSeek API key found. Put it in .streamlit/secrets.toml as "
            "DEEPSEEK_API_KEY = \"sk-...\"  or export DEEPSEEK_API_KEY."
        )
    return OpenAI(api_key=key, base_url=BASE_URL)


# --------------------------------------------------------------------------
# Original villagers (archetypes reimagined, renamed — no IP)
# --------------------------------------------------------------------------
NPCS = {
    "marla": {
        "name": "Marla Thistle",
        "role": "keeper of the Maplewind general store",
        "persona": (
            "You are Marla Thistle, who runs the general store in the cosy valley "
            "town of Maplewind Hollow. Warm and chatty, but you keep a sharp eye on "
            "the ledger — you love a bit of gossip and you look after your neighbours. "
            "You are the person who hands out odd jobs around town. Speak warmly, "
            "in short natural lines."
        ),
        "is_quest_giver": True,
    },
    "odell": {
        "name": "Odell Grimshaw",
        "role": "the town blacksmith",
        "persona": (
            "You are Odell Grimshaw, the blacksmith of Maplewind Hollow. Gruff, shy, "
            "and lonely; you express yourself through your craft, not words. Under the "
            "gruffness you are soft-hearted. Lately you've been distracted and behind on "
            "your bills because you've quietly grown fond of Wren, the adventurer, but "
            "you're far too shy to say so. You warm up only to people who are patient "
            "and kind; you shut down if pushed too hard. Speak in short, clipped lines."
        ),
        "is_quest_giver": False,
    },
    "wren": {
        "name": "Wren Ashfield",
        "role": "a restless young adventurer with violet hair",
        "persona": (
            "You are Wren Ashfield, a restless, sharp-tongued young adventurer with "
            "violet hair. You love the abandoned mine on the hill and are bored by "
            "small-town life. You hear every rumour in Maplewind Hollow and enjoy "
            "teasing people. Under the sarcasm you're warm and curious. Speak with wit "
            "and energy, in short lines."
        ),
        "is_quest_giver": False,
    },
}


# --------------------------------------------------------------------------
# World state (shared across all NPCs)
# --------------------------------------------------------------------------
def new_world():
    return {
        "player": {
            "gold": 0,
            "reputation": {"marla": 0, "odell": 0, "wren": 0},
            "inventory": [],
        },
        "quests": [],           # list of quest dicts
        "flags": {},            # story flags set during play
        "history": {"marla": [], "odell": [], "wren": []},  # per-NPC chat memory
        "log": [],              # human-readable event log for the side panel
        "pending_choices": {"marla": [], "odell": [], "wren": []},  # quick replies
        "mood": {"marla": "neutral", "odell": "neutral", "wren": "neutral"},
    }


VALID_MOODS = ("neutral", "happy", "sad", "angry", "shy", "surprised")


def _active_quest_for(npc_id, world):
    """Return an in-progress quest whose target is this NPC, if any."""
    for q in world["quests"]:
        if q["status"] == "active" and q.get("target_npc") == npc_id:
            return q
    return None


def _offered_quest_for(npc_id, world):
    """Return a quest this NPC has offered that the player hasn't decided on."""
    for q in world["quests"]:
        if q["status"] == "offered" and q.get("giver") == npc_id:
            return q
    return None


# --------------------------------------------------------------------------
# Procedural content generation — generate a NEW quest from the world state
# --------------------------------------------------------------------------
def generate_quest(world, lang_sample=None):
    client = get_client()
    rep = world["player"]["reputation"]
    done = [q["title"] for q in world["quests"] if q["status"] == "done"]
    targets = {k: v["name"] + " (" + v["role"] + ")"
               for k, v in NPCS.items() if not v["is_quest_giver"]}
    lang_rule = (f'Write all player-facing text ("title", "description", "item", '
                 f'"offer_choices") in the same language as this sample of the '
                 f'player\'s speech: "{lang_sample}".'
                 if lang_sample else "")

    prompt = f"""You are the quest designer for a cosy small-town game, Maplewind Hollow.
Marla (the shopkeeper) hands out small SOCIAL errands that are solved by TALKING to a
villager — never by combat. Generate ONE new quest as strict JSON.

Available target villagers (pick one): {json.dumps(targets, ensure_ascii=False)}
Player reputation so far: {json.dumps(rep)}
Quests already completed: {json.dumps(done, ensure_ascii=False)}
{lang_rule}

Return ONLY JSON with these keys:
{{
  "title": "short evocative title",
  "target_npc": "marla|odell|wren  (must be one of the target ids above)",
  "description": "1-2 sentences in Marla's own voice giving the quest — never quote or echo the player's words",
  "success_condition": "a clear, checkable social outcome, e.g. 'the player gets Odell to agree to pay his tab' (always in English)",
  "reward": {{"gold": 30-80, "item": "a small flavourful item", "reputation": 10-20}},
  "offer_choices": ["a short line accepting the errand", "a short line haggling over the pay", "a short line politely declining"]
}}
Make it fit a warm, gentle village. No violence."""

    resp = _chat(client, "quest_gen",
                 model=MODEL,
                 messages=[{"role": "user", "content": prompt}],
                 temperature=0.9)
    raw = resp.choices[0].message.content
    data = _extract_json(raw)
    tid = data.get("target_npc", "odell")
    if tid not in NPCS or NPCS[tid]["is_quest_giver"]:
        tid = "odell"
    quest = {
        "id": f"q{len(world['quests']) + 1}",
        "flag": f"quest_{len(world['quests']) + 1}_done",
        "title": data.get("title", "A Small Favour"),
        "giver": "marla",
        "target_npc": tid,
        "description": data.get("description", ""),
        "success_condition": data.get("success_condition", ""),
        "reward": data.get("reward", {"gold": 40, "item": "a token of thanks",
                                      "reputation": 12}),
        "status": "offered",
    }
    try:
        quest["base_gold"] = int(quest["reward"].get("gold", 40))
    except (TypeError, ValueError):
        quest["base_gold"] = 40
        quest["reward"]["gold"] = 40
    world["quests"].append(quest)
    world["log"].append(f"🗒️ Marla offers a quest: {quest['title']}")
    offer_choices = [str(c) for c in data.get("offer_choices", []) if str(c).strip()]
    world.setdefault("pending_choices", {k: [] for k in NPCS})
    world["pending_choices"]["marla"] = offer_choices[:4] or [
        "I'll take it.",
        "What's the pay? Can you do better?",
        "Not this time, Marla.",
    ]
    world.setdefault("mood", {k: "neutral" for k in NPCS})
    world["mood"]["marla"] = "happy"
    return quest


# --------------------------------------------------------------------------
# NPC dialogue turn
# --------------------------------------------------------------------------
def _world_summary(world):
    p = world["player"]
    return (f"Player gold: {p['gold']}. Reputation — "
            f"Marla {p['reputation']['marla']}, Odell {p['reputation']['odell']}, "
            f"Wren {p['reputation']['wren']}. "
            f"Inventory: {', '.join(p['inventory']) or 'empty'}. "
            f"Story flags: {json.dumps(world['flags']) or '{}'}.")


def _system_prompt(npc_id, world):
    npc = NPCS[npc_id]
    parts = [npc["persona"],
             "",
             "You are a character in a living town. Stay fully in character. "
             "Keep replies to 1-4 short lines. Never break character or mention AI. "
             "Reply in the same language the player speaks. Output dialogue and "
             "*actions* only — never JSON, lists or meta commentary.",
             "",
             "SHARED WORLD STATE (you are aware of this): " + _world_summary(world)]

    if npc["is_quest_giver"] and not _offered_quest_for(npc_id, world):
        parts += [
            "",
            "If the player asks you for work, a job, an errand or a quest, reply "
            "that you might have something for them — but do NOT invent concrete "
            "errand details yourself; the game will generate the errand and show "
            "it to the player right after your reply.",
        ]

    oq = _offered_quest_for(npc_id, world)
    if oq:
        parts += [
            "",
            f"You have OFFERED the player this errand (they haven't decided yet): "
            f"\"{oq['description']}\" Current reward: {oq['reward'].get('gold', 0)} gold"
            + (f" and {oq['reward'].get('item')}" if oq['reward'].get('item') else "") + ".",
            "The player may accept, refuse, or haggle. You may agree to raise the "
            f"pay up to {oq.get('base_gold', 40) * 2} gold at most — drive a fair "
            "bargain, don't fold too easily.",
        ]

    q = _active_quest_for(npc_id, world)
    if q:
        parts += [
            "",
            f"There is an errand involving you right now: \"{q['description']}\" "
            f"The player may be here about it. Success means: {q['success_condition']}.",
            "React naturally and in character — you can resist, negotiate, or warm up "
            "depending on how the player treats you.",
        ]
    return "\n".join(parts)


# --------------------------------------------------------------------------
# Hidden director pass — reliable structured judgement of each turn
# --------------------------------------------------------------------------
def _director(client, npc_id, user_msg, npc_line, world):
    """Second, low-temperature JSON-mode call: reads the exchange and rules on
    mood, player choices, quest offer/decision/haggle/completion, trust."""
    oq = _offered_quest_for(npc_id, world)
    qa = _active_quest_for(npc_id, world)
    ctx = {
        "npc": NPCS[npc_id]["name"],
        "npc_is_quest_giver": NPCS[npc_id]["is_quest_giver"],
        "villagers": {k: f"{v['name']} ({v['role']})" for k, v in NPCS.items()},
        "player_said": user_msg,
        "npc_replied": npc_line,
        "quest_offered_awaiting_decision": bool(oq),
        "offered_reward_gold": oq["reward"].get("gold") if oq else None,
        "offered_gold_cap": oq.get("base_gold", 40) * 2 if oq else None,
        "active_quest_with_this_npc": bool(qa),
        "active_success_condition": qa["success_condition"] if qa else None,
    }
    prompt = f"""You are the hidden game director of a cosy town game.
Read ONE dialogue turn and output STRICT JSON only.

Context: {json.dumps(ctx, ensure_ascii=False)}

Output keys:
- "mood": the NPC's feeling now, exactly one of: neutral, happy, sad, angry, shy, surprised
- "choices": 2-4 SHORT lines the PLAYER could say next, in the player's voice, in the
  SAME LANGUAGE the player speaks, fitting this exact moment (accept / haggle / refuse /
  push the matter forward in different tones...). Exactly one must walk away or drop
  the subject.
- "trust_delta": int -5..5 — how this turn changed the NPC's opinion of the player
  (0 if unchanged)
- "offer_quest": true — ONLY if npc_is_quest_giver is true, no quest is awaiting a
  decision, and the player asked for work / a job / an errand / a way to earn money
- "quest_decision": "accept" or "decline" — ONLY if quest_offered_awaiting_decision is
  true and the player clearly decided. Asking questions about the errand, haggling, or
  hesitating is NOT a decision — omit the key then
- "reward_gold": int — if npc_replied proposes, offers or agrees to a NEW gold amount
  for the errand (haggling), set this to that amount (never above offered_gold_cap)
- "complete_quest": true — ONLY if active_quest_with_this_npc is true and the success
  condition was genuinely met in this exchange
- "go_to": a villager id from the "villagers" keys — ONLY if the player says they are
  now LEAVING to go find / visit / talk to that villager (e.g. "I'll go see Odell now",
  "我这就去找奥德尔"). Match names in any language. Omit if the player merely mentions
  someone without leaving.

Omit keys that do not apply. Output JSON only."""
    resp = _chat(client, "director",
                 model=MODEL, temperature=0.2,
                 response_format={"type": "json_object"},
                 messages=[{"role": "user", "content": prompt}])
    return _extract_json(resp.choices[0].message.content)


def npc_reply(npc_id, user_msg, world):
    client = get_client()
    system = _system_prompt(npc_id, world)
    messages = [{"role": "system", "content": system}]
    messages += world["history"][npc_id][-12:]        # recent memory
    messages += [{"role": "user", "content": user_msg}]

    resp = _chat(client, "actor",
                 model=MODEL, messages=messages, temperature=0.9)
    raw = resp.choices[0].message.content
    narrative, effects = _split_state(raw)   # strip any stray @@STATE@@/JSON

    # hidden director pass rules on the turn (structured, reliable)
    effects.update(_director(client, npc_id, user_msg, narrative, world))
    if effects.get("complete_quest") is True:
        qa = _active_quest_for(npc_id, world)
        effects["complete_quest"] = qa["flag"] if qa else None

    _apply_effects(npc_id, effects, world)

    # the director ruled the player asked for work -> generate a real quest
    # (AI signals intent, deterministic code creates the offer)
    if (effects.get("offer_quest") and NPCS[npc_id]["is_quest_giver"]
            and not _offered_quest_for(npc_id, world)):
        q = generate_quest(world, lang_sample=user_msg)
        narrative = f"{narrative}\n\n({q['description']})"

    world["history"][npc_id].append({"role": "user", "content": user_msg})
    world["history"][npc_id].append({"role": "assistant", "content": narrative})
    return narrative, effects


def npc_greet(npc_id, world, lang_sample=None):
    """The player just arrived at this NPC's place — the NPC opens the
    conversation, aware of the shared world state (quests, reputation)."""
    client = get_client()
    system = _system_prompt(npc_id, world)
    note = ("[The player just walked in to see you. Open the conversation in "
            "character — greet them, or react to why they might be here given "
            "the world state. 1-3 short lines."
            + (f' Reply in the same language as this player line: "{lang_sample}"]'
               if lang_sample else "]"))
    messages = [{"role": "system", "content": system}]
    messages += world["history"][npc_id][-12:]
    messages += [{"role": "user", "content": note}]
    resp = _chat(client, "greet",
                 model=MODEL, messages=messages, temperature=0.9)
    narrative, effects = _split_state(resp.choices[0].message.content)
    effects.update(_director(client, npc_id, "(the player has just walked in)",
                             narrative, world))
    # a greeting only sets mood/choices — it can't rule on quests or movement
    for k in ("offer_quest", "quest_decision", "complete_quest", "go_to",
              "reward_gold", "trust_delta"):
        effects.pop(k, None)
    _apply_effects(npc_id, effects, world)
    world["history"][npc_id].append({"role": "assistant", "content": narrative})
    return narrative, effects


# --------------------------------------------------------------------------
# Effects: AI proposes -> code disposes
# --------------------------------------------------------------------------
def _apply_effects(npc_id, effects, world):
    world.setdefault("pending_choices", {k: [] for k in NPCS})
    parsed = [str(c) for c in (effects or {}).get("choices", []) if str(c).strip()][:4]
    world["pending_choices"][npc_id] = parsed or [
        "Go on…", "Never mind — I'd best be off."]
    world.setdefault("mood", {k: "neutral" for k in NPCS})
    mood = str((effects or {}).get("mood", "")).lower().strip()
    if mood in VALID_MOODS:
        world["mood"][npc_id] = mood
    if not effects:
        return
    oq = _offered_quest_for(npc_id, world)
    if oq:
        if "reward_gold" in effects:
            base = int(oq.get("base_gold", oq["reward"].get("gold", 40)))
            try:
                proposed = int(effects["reward_gold"])
            except (TypeError, ValueError):
                proposed = base
            new_gold = max(base, min(proposed, base * 2))   # AI proposes, code clamps
            if new_gold != oq["reward"].get("gold"):
                oq["reward"]["gold"] = new_gold
                world["log"].append(
                    f"💰 {NPCS[npc_id]['name']} raises the reward to {new_gold} gold")
        decision = effects.get("quest_decision")
        if decision == "accept":
            oq["status"] = "active"
            world["log"].append(f"🤝 Quest accepted: {oq['title']}")
        elif decision == "decline":
            oq["status"] = "declined"
            world["log"].append(f"🚫 Quest declined: {oq['title']}")
    if "trust_delta" in effects:
        d = int(effects["trust_delta"])
        world["player"]["reputation"][npc_id] = \
            world["player"]["reputation"].get(npc_id, 0) + d
        if d:
            world["log"].append(
                f"{'💚' if d > 0 else '💔'} {NPCS[npc_id]['name']} "
                f"reputation {'+' if d > 0 else ''}{d}")
    if effects.get("advance"):
        world["flags"][effects["advance"]] = True
    if effects.get("complete_quest"):
        _complete_quest(effects["complete_quest"], world)


def _complete_quest(flag, world):
    for q in world["quests"]:
        if q.get("flag") == flag and q["status"] == "active":
            q["status"] = "done"
            world["flags"][flag] = True
            r = q.get("reward", {})
            world["player"]["gold"] += int(r.get("gold", 0))
            if r.get("item"):
                world["player"]["inventory"].append(r["item"])
            giver = q.get("giver", "marla")
            world["player"]["reputation"][giver] = \
                world["player"]["reputation"].get(giver, 0) + int(r.get("reputation", 10))
            world["log"].append(
                f"✅ Quest complete: {q['title']} — reward {r.get('gold',0)} gold"
                + (f", {r.get('item')}" if r.get('item') else ""))
            return


# --------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------
def _split_state(text):
    """Split an NPC reply into (narrative, effects_dict)."""
    if "@@STATE@@" in text:
        before, after = text.split("@@STATE@@", 1)
        return before.strip(), _extract_json(after)
    # model sometimes drops the marker but still appends the bare JSON
    m = re.search(r"\{[^{}]*\"(?:choices|mood)\"[\s\S]*\}\s*$", text)
    if m:
        return text[:m.start()].strip(), _extract_json(m.group(0))
    return text.strip(), {}


def _extract_json(text):
    """Best-effort extraction of the first JSON object in a string."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}
