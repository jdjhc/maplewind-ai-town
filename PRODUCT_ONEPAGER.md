# Product one-pager — AI-driven villagers

*A product framing of the Maplewind Hollow prototype, written the way a Game AI
PM would scope the feature. Live demo:
[maplewind-hollow.streamlit.app](https://maplewind-hollow.streamlit.app)*

## Problem

Hand-authored NPC dialogue is expensive and static. Players exhaust it quickly,
side quests feel repetitive, and small studios can't hand-write enough content
to keep a living world feeling alive. Generative AI can help — but naive "let
the LLM say anything" approaches break game rules, leak tone, and can't be
trusted to score quests or grant rewards.

## Proposal: an actor/director loop

Every player turn runs **two passes with a clean split of responsibility**:

- **Actor pass (creative layer):** the NPC replies fully in character — high
  temperature, free prose, persona + memory + shared world state. It is never
  asked to output data.
- **Director pass (rules layer):** a hidden JSON-mode, low-temperature call
  reads the exchange and rules on game state: the NPC's mood (drives the
  portrait), the player's next dialogue choices, trust change, and whether a
  quest was requested / accepted / declined / haggled / completed, or the
  player left for another scene. Deterministic code then applies the ruling —
  rewards are granted by code, haggling is clamped by code to 2× base pay.

*AI proposes, code disposes* — but split across two calls, because one call
can't be trusted to do both jobs (see field notes).

## Field notes: what we learned about model capability

These came from actually building it, and shaped the architecture:

1. **In-prose protocol compliance is unreliable.** Asking the actor to append
   a hidden JSON block to its reply worked in English demos, then collapsed in
   Chinese play — the block was silently dropped, so no choices, no mood, no
   quest detection. Reminders helped but never fixed it.
2. **JSON mode fixes it completely.** Moving all structured judgement to a
   dedicated `response_format=json_object` call at temperature 0.2 measured
   **18/18 valid outputs** ([full evaluation](docs/EVALUATION.md)).
3. **Ungrounded quest-givers hallucinate content.** Before the director
   existed, the shopkeeper invented fake villagers and fake errands
   ("carpenter Winnie needs flour moved") that no game system knew about.
   Now the actor is told *not* to invent errand details; the director detects
   the intent and deterministic code generates a real, registered quest.
4. **Narrative/state divergence destroys trust.** An NPC "handing you a coin"
   in prose while the gold counter stays put reads as a bug to players. Every
   number a player sees must come from the rules layer.

## Why it fits games (NPC interactions · PCG · dynamic narrative)

- **NPC interactions:** villagers hold persona + memory + shared world
  awareness; portraits (six moods, code-drawn SVG) react to every exchange.
- **Procedural content generation:** quests are generated as structured JSON
  from live world state — asked for in chat in any language, offered, haggled
  over, accepted or declined.
- **Dynamic narrative:** one shared world state means consequences propagate;
  saying "I'll go find Odell" cuts the scene to the forge, where Odell opens
  the conversation himself.

## Measured quality gates ([details & harness](docs/EVALUATION.md))

| Gate | Result |
|---|---|
| Director judgement accuracy (18-case zh/en set, positives + distractors) | **15/15 strict** after one prompt fix the harness itself caught |
| Protocol compliance (valid mood + usable choices per turn) | **18/18** |
| Latency per player turn | ≈ 3.4 s p50 (actor 1.5 s + director 1.9 s) |
| Cost | **≈ ¥0.31 per 100 player turns** — cost is a non-issue; latency is the binding constraint |

## What's in / out of scope for this prototype

**In:** 3 agents, shared world state, chat-triggered procedural quests with an
offer/haggle/accept/decline lifecycle, conversational completion + rewards,
mood-reactive portraits, scene transitions, an evaluation harness, cost/latency
telemetry.
**Out (next steps):** voice, game-engine integration, streaming responses to
hide director latency, a 200+ case eval set mined from play logs, safety
filtering for adversarial player input.

## Risks & mitigations

| Risk | Mitigation | Status |
|---|---|---|
| LLM "cheats" completion or rewards | Rules layer owns all scoring; director only proposes; code clamps | ✅ shipped, tested |
| Structured output silently dropped | Dedicated JSON-mode director pass | ✅ shipped, 18/18 |
| Quest-giver hallucinates content | Actor forbidden to invent details; code generates real quests | ✅ shipped |
| Latency (2 calls/turn) | Acceptable in a VN format; streaming + smaller judge model next | ⚠️ open |
| Adversarial phrasing fools the director | Grow eval set with negation/sarcasm cases; gate releases on it | ⚠️ open |

## Success metrics (if shipped)

Dialogue engagement (turns per NPC per session), quest acceptance and
completion rates, choice-button usage vs free typing (UX signal), director
false-positive rate on live logs, and content-authoring cost saved vs
hand-written equivalent.

---

*Prototype by Mingqi Li. Built with DeepSeek + Streamlit. Characters and
artwork original.*
