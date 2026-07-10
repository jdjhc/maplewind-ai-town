# 🌾 Maplewind Hollow — an AI-driven cosy town

A visual-novel-style prototype where **every villager is an LLM agent**. Chat
with them, take on quests, haggle over rewards, and watch the story — and
their portraits — react to your choices. Built to explore how generative AI
can power the *social* side of games.

Demonstrates the three pillars asked of AI in games:

| Pillar | How it shows up here |
|---|---|
| **NPC interactions** | 3 villagers, each with a distinct persona **and memory** — they remember your past conversations and the shared state of the town; their portraits change expression and animate with the conversation |
| **Procedural content generation** | Ask the shopkeeper for work — in chat or via a button — and a **new social quest is generated on the fly** (as structured JSON) from the current world state, in the player's language |
| **Dynamic narrative** | Quests are offered, haggled over, accepted or declined, and solved by **talking**, not fighting; villagers share one world state, so lying to one changes how the others treat you |

## The design idea (the part that matters for a games PM)

> **The LLM handles the creative layer** — dialogue, quest flavour, narration.
> **Deterministic code handles the rules layer** — quest lifecycle, rewards,
> reputation.

Every turn runs a **two-pass loop**:

1. **Actor pass** — the NPC replies fully in character (higher temperature,
   free prose).
2. **Director pass** — a hidden second call (JSON mode, low temperature) reads
   the exchange and rules on the game state: the NPC's `mood`, the player's
   next dialogue `choices`, `trust_delta`, whether a quest was requested /
   accepted / declined / completed, whether the pay was haggled up (clamped in
   code to 2× the base), and whether the player left to visit someone else.

*AI proposes, code disposes.* Splitting acting from judging keeps the fun,
open-ended feel of an LLM while making scoring, rewards and progress reliable —
the key to shipping LLM features in real games.

## Visual-novel presentation

- Each villager has an **original portrait drawn entirely in code** (SVG —
  no external assets, no copyright concerns) with **six moods**: neutral,
  happy, sad, angry, shy, surprised.
- The director picks the mood each turn, and the sprite reacts: a happy
  bounce, an angry shake, a shy sway, a surprised pop.
- Dialogue lands in a VN-style box with a name plate; the player answers by
  clicking **generated choice buttons** (accept / haggle / refuse / walk away…)
  or typing freely. A backlog panel keeps the full conversation.
- Say "I'll go find Odell" and the scene **cuts to the forge**, where Odell
  looks up from the anvil and opens the conversation himself.

## The cast (original characters, only *inspired by* farming-game archetypes)

- **Marla Thistle** — general-store keeper; warm, gossipy, hands out the errands.
- **Odell Grimshaw** — shy, gruff blacksmith with a secret soft spot.
- **Wren Ashfield** — restless, sharp-tongued adventurer who hears every rumour.

*(Characters and artwork are original to avoid any IP issues.)*

## Try it

A typical loop:
1. Ask **Marla** for work (just say so in chat, any language) → she offers a
   generated quest; **accept, haggle the pay up, or decline** via the choice
   buttons.
2. Say you're off to see the target villager → the scene switches and they
   greet you in character.
3. Talk the problem through — push too hard and Odell clams up; be patient and
   he opens up.
4. The director rules the moment the success condition is genuinely met → gold,
   item and reputation land in the sidebar.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Add your DeepSeek key (kept out of git):

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit the file and paste your key
```

```bash
.venv/bin/streamlit run app.py
```

Note: Streamlit hot-reloads `app.py` only — after editing `npc_engine.py` or
`sprites.py`, restart the server.

## Tech

Python · Streamlit · DeepSeek (`deepseek-chat`, OpenAI-compatible API) ·
a two-pass actor/director loop over a shared world state · code-drawn SVG
portraits.

## Security note

The API key lives only in `.streamlit/secrets.toml`, which is **gitignored** and
never committed. If a key is ever exposed, regenerate it.
