# Product one-pager — AI-driven villagers

*A product framing of the Maplewind Hollow prototype, written the way a Game AI
PM would scope the feature.*

## Problem

Hand-authored NPC dialogue is expensive and static. Players exhaust it quickly,
side quests feel repetitive, and small studios can't hand-write enough content
to keep a living world feeling alive. Generative AI can help — but naive "let the
LLM say anything" approaches break game rules, leak tone, and can't be trusted to
score quests or grant rewards.

## Proposal

LLM-driven villagers with a **clean split of responsibility**:

- **Creative layer (LLM):** in-character dialogue, procedurally generated social
  quests, dynamic narration that branches on player choice.
- **Rules layer (deterministic code):** quest-completion checks, reward grants,
  reputation and inventory — driven by a shared, inspectable world state.

The LLM communicates with the rules layer through a constrained structured
signal (`@@STATE@@ {json}`), so designers keep control of anything that must be
reliable.

## Why it fits games (NPC interactions · PCG · dynamic narrative)

- **NPC interactions:** villagers hold persona + memory + awareness of the shared
  world — conversations feel personal and consistent.
- **Procedural content generation:** quests are generated from the live state, so
  content scales without hand-authoring every branch.
- **Dynamic narrative:** a shared world state means consequences propagate — lie
  to one villager and the others hear about it — creating emergent stories.

## What's in / out of scope for this prototype

**In:** 3 agents, shared world state, procedural social quests, conversational
completion + rewards, live state panel.
**Out (next steps):** voice, spatial/game-engine integration, safety/guardrail
filtering, latency/cost budgeting, evaluation harness for quest quality.

## Risks & mitigations (the honest part)

| Risk | Mitigation |
|---|---|
| LLM says something off-tone / breaks lore | Tight persona prompts + a lore/safety filter pass before display |
| LLM "cheats" completion or rewards | Rules layer owns all scoring; LLM only *proposes* via structured signal |
| Latency & API cost per line | Cache, smaller models for minor NPCs, batch background generation |
| Quest quality varies | Templated constraints + an automatic quality-eval before a quest goes live |

## Success metrics (if shipped)

Dialogue engagement (turns per NPC), quest completion rate, player-authored story
variety, and content-authoring cost saved vs. hand-written equivalent.

---

*Prototype by Mingqi Li. Built with DeepSeek + Streamlit. Characters original.*
