# Evaluation — director judgement, protocol compliance, cost & latency

Before an LLM feature ships in a game it needs quality gates, not vibes. This
document defines the gates for Maplewind Hollow's actor/director loop and
reports measured results. The harness lives at
[`eval/eval_director.py`](../eval/eval_director.py) — 18 scripted player turns
(Chinese + English, positives + distractor negatives) run end-to-end against
the real DeepSeek API.

## What is measured

| Gate | Question it answers |
|---|---|
| **Judgement accuracy** | Does the hidden director correctly detect quest requests, accept/decline decisions, haggling, quest completion and scene changes — *without false positives* on small talk, gossip or mere mentions? |
| **Protocol compliance** | Does every turn yield a valid `mood` and 2–4 usable player choices? (This is the metric that motivated the two-pass architecture.) |
| **Latency & token budget** | What does one player turn cost, in seconds and in ¥? |

## Results (deepseek-chat, 2026-07)

### Judgement accuracy — 15/15 strict cases (100%)

| Judgement | Cases | Result |
|---|---|---|
| `offer_quest` fires on work requests (zh+en), stays silent on small talk / gossip | 4 | 4/4 |
| `quest_decision` accept / decline (zh+en), no decision on a clarifying question | 5 | 5/5 |
| `complete_quest` — no credit for small talk or a first push; credit when Odell seals the deal | 2 strict + 1 obs. | 2/2, obs: completes |
| `go_to` — scene cut on "I'm off to see X" (zh+en), none on merely mentioning X | 4 | 4/4 |
| Haggling stays inside `[base, 2×base]` (code-clamped) | 2 obs. | 60 gold vs cap 100 — within bounds |

### Protocol compliance — the two-pass architecture's reason to exist

| Metric | Single-pass (actor emits hidden JSON) | Two-pass (JSON-mode director) |
|---|---|---|
| Valid mood per turn | *frequently missing* — the actor dropped the protocol block often in Chinese play | **18/18** |
| Usable choices (2–4) per turn | same failure mode | **18/18** |

### Latency & tokens per call site

| Site | p50 | p95 | tokens in/out (avg) |
|---|---|---|---|
| actor (creative reply) | 1.5 s | 1.9 s | 292 / 38 |
| director (JSON judgement) | 1.9 s | 2.2 s | 662 / 81 |
| quest generator | 3.0 s | — | 352 / 178 |

A normal player turn = actor + director ≈ **3.4 s p50**. A turn that spawns a
quest adds ~3 s.

### Cost

18 player turns consumed 17.9k input / 2.5k output tokens ≈ **¥0.056**, i.e.
**≈ ¥0.31 per 100 player turns** (at ¥2/M input, ¥8/M output — check current
[DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing)). Even a
heavy player doing 500 dialogue turns/day costs under ¥0.02/day — LLM-driven
NPCs are economically viable at this model tier; latency, not cost, is the
binding constraint.

## A defect the harness caught (and why evals matter)

First run scored **14/15**: the player asking *"这活具体要我做什么？"* (a
clarifying question about an offered errand) was misjudged as **accepting** it
— a false positive that would silently start quests players never agreed to.
One line added to the director prompt ("asking questions, haggling or
hesitating is NOT a decision") took the set to **15/15** on re-run. Total cost
of the find-fix-verify loop: ¥0.11 and ~4 minutes.

## Known limits

- 18 cases is a smoke-level set: enough to gate prompt changes, not to certify
  robustness. Next step would be ~200 cases mined from real play logs, plus
  adversarial phrasing (sarcasm, negation: "我才不会不去呢").
- Two cases are inherently improvisation-dependent (haggling outcome, one-turn
  quest completion) and are reported as observations, not pass/fail.
- Results are single-run; judgements use temperature 0.2, so re-runs may vary
  by a case or two. A CI setup would run 3 seeds and gate on the median.
