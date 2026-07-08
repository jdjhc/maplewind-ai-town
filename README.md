# 🌾 Maplewind Hollow — an AI-driven cosy town

A small prototype where **every villager is an LLM agent**. Chat with them,
take on quests, and watch the story and their opinions of you shift with your
choices. Built to explore how generative AI can power the *social* side of games.

Demonstrates the three pillars asked of AI in games:

| Pillar | How it shows up here |
|---|---|
| **NPC interactions** | 3 villagers, each with a distinct persona **and memory** — they remember your past conversations and the shared state of the town |
| **Procedural content generation** | Ask the shopkeeper for work and a **new social quest is generated on the fly** (as structured JSON) from the current world state |
| **Dynamic narrative** | Quests are solved by **talking**, not fighting; villagers share one world state, so lying to one changes how the others treat you; rewards resolve inside the story |

## The design idea (the part that matters for a games PM)

> **The LLM handles the creative layer** — dialogue, quest flavour, narration.
> **Deterministic code handles the rules layer** — quest completion, rewards,
> reputation.

Each NPC reply may append a hidden `@@STATE@@ {json}` block that the engine
parses and applies. *AI proposes, code disposes.* This keeps the fun,
open-ended feel of an LLM while guaranteeing that scoring, rewards and progress
stay reliable — the key to shipping LLM features in real games.

## The cast (original characters, only *inspired by* farming-game archetypes)

- **Marla Thistle** — general-store keeper; warm, gossipy, hands out the errands.
- **Odell Grimshaw** — shy, gruff blacksmith with a secret soft spot.
- **Wren Ashfield** — restless, sharp-tongued adventurer who hears every rumour.

*(Characters are original and renamed to avoid any IP issues.)*

## Try it

A typical loop:
1. Talk to **Marla**, click **"Ask for work"** → she generates a quest, e.g.
   *"Odell hasn't paid his tab — go find out what's wrong."*
2. Talk to **Odell**. Push too hard and he clams up; be patient and he opens up.
3. Follow the thread to **Wren**; what you do ripples back.
4. Resolve it in conversation → the reward lands in the story, and the side
   panel updates gold / reputation / inventory.

## Run locally

```bash
pip install -r requirements.txt
```

Add your DeepSeek key (kept out of git):

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit the file and paste your key
```

```bash
streamlit run app.py
```

## Tech

Python · Streamlit · DeepSeek (`deepseek-chat`, OpenAI-compatible API) ·
a lightweight multi-agent world-state loop.

## Security note

The API key lives only in `.streamlit/secrets.toml`, which is **gitignored** and
never committed. If a key is ever exposed, regenerate it.
