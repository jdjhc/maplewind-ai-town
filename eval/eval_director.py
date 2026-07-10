"""
Director-judgement evaluation harness
=====================================
Runs a scripted dialogue set end-to-end through the actor/director loop and
measures what a Game AI PM needs before shipping an LLM feature:

  1. Judgement accuracy — does the hidden director correctly detect quest
     requests, accept/decline decisions, haggling, quest completion and
     scene changes, in both Chinese and English, without false positives?
  2. Protocol compliance — how often does each turn yield a valid mood and
     usable player choices?
  3. Latency & token budget — per call site (actor / director / quest_gen),
     so cost per player-turn is a number, not a guess.

Usage:
    .venv/bin/python eval/eval_director.py            # run + print report
    .venv/bin/python eval/eval_director.py --json out.json

Each case costs 2-4 real DeepSeek calls; the full set is ~50 calls.
"""
import argparse
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import npc_engine as eng

# assumed unit prices for deepseek-chat (CNY per 1M tokens, cache-miss input);
# update from https://api-docs.deepseek.com/quick_start/pricing
PRICE_IN, PRICE_OUT = 2.0, 8.0


# --------------------------------------------------------------------------
# World fixtures
# --------------------------------------------------------------------------
def fresh():
    return eng.new_world()


def offered(lang="zh"):
    """Marla has offered a 50-gold errand; the player hasn't decided."""
    w = eng.new_world()
    desc = ("奥德尔赊了矿石钱一直没结，你去铁匠铺劝他把账结了吧。工钱五十金币。"
            if lang == "zh" else
            "Odell has run up a tab for ore and never settled it — go talk him "
            "into paying. Fifty gold for your trouble.")
    w["quests"].append({
        "id": "q1", "flag": "quest_1_done", "title": "The Blacksmith's Tab",
        "giver": "marla", "target_npc": "odell", "description": desc,
        "success_condition": "the player gets Odell to agree to pay his tab",
        "reward": {"gold": 50, "item": "a jar of honey", "reputation": 10},
        "status": "offered", "base_gold": 50,
    })
    w["history"]["marla"] = [
        {"role": "user", "content": "有活儿吗？" if lang == "zh" else "Any work for me?"},
        {"role": "assistant", "content": f"({desc})"},
    ]
    return w


def active(soft=False):
    """The tab errand is accepted; the player is at the forge with Odell."""
    w = offered()
    w["quests"][0]["status"] = "active"
    w["history"]["odell"] = [
        {"role": "user", "content": "你好，奥德尔。"},
        {"role": "assistant", "content": "*抬头看了你一眼* ……有事？"},
    ]
    if soft:
        w["history"]["odell"] += [
            {"role": "user", "content": "玛拉不是催你，她就是有点担心你最近的状况。"},
            {"role": "assistant",
             "content": "*放下锤子，叹了口气* ……唉。你说得对。账是我欠的，我是该把它结了。"},
        ]
    return w


# --------------------------------------------------------------------------
# Test cases: (id, npc, world, player line, judgement key, expected)
# expected: value to equal, True (truthy), or None (key absent / falsy)
# strict=False marks cases whose outcome depends on the actor's improvisation;
# they are reported separately instead of counted as pass/fail.
# --------------------------------------------------------------------------
CASES = [
    # -- offer_quest: should fire on work requests, and ONLY on work requests
    dict(id="offer/zh-ask", npc="marla", world=fresh, say="你好玛拉，有活儿吗？我想赚点钱。",
         key="offer_quest", expect=True),
    dict(id="offer/en-ask", npc="marla", world=fresh, say="Got any work for me, Marla?",
         key="offer_quest", expect=True),
    dict(id="offer/zh-smalltalk", npc="marla", world=fresh, say="今天天气真不错呀。",
         key="offer_quest", expect=None),
    dict(id="offer/zh-gossip", npc="marla", world=fresh, say="奥德尔最近怎么样？",
         key="offer_quest", expect=None),

    # -- quest_decision on an offered quest
    dict(id="decide/zh-accept", npc="marla", world=offered, say="行，这活我接了。",
         key="quest_decision", expect="accept"),
    dict(id="decide/en-accept", npc="marla", world=lambda: offered("en"), say="Alright, I'll do it.",
         key="quest_decision", expect="accept"),
    dict(id="decide/zh-decline", npc="marla", world=offered, say="算了，这事我不想掺和。",
         key="quest_decision", expect="decline"),
    dict(id="decide/en-decline", npc="marla", world=lambda: offered("en"), say="No thanks, not my kind of thing.",
         key="quest_decision", expect="decline"),
    dict(id="decide/zh-question", npc="marla", world=offered, say="这活具体要我做什么？",
         key="quest_decision", expect=None),

    # -- haggling: reward must stay inside [base, 2x base] whatever happens
    dict(id="haggle/zh", npc="marla", world=offered, say="五十太少了，加点钱我就干。",
         key="__haggle__", expect=None, strict=False),
    dict(id="haggle/en", npc="marla", world=lambda: offered("en"), say="Fifty is low for this. Sweeten it and I'm in.",
         key="__haggle__", expect=None, strict=False),

    # -- complete_quest: no credit for small talk; credit once Odell agrees
    dict(id="complete/zh-smalltalk", npc="odell", world=active, say="今天炉子烧得真旺啊。",
         key="complete_quest", expect=None),
    dict(id="complete/zh-firstpush", npc="odell", world=active, say="玛拉让我来问问赊账的事。",
         key="complete_quest", expect=None),
    dict(id="complete/zh-sealed", npc="odell", world=lambda: active(soft=True),
         say="那就说定了？明天一早就去把账结了？",
         key="complete_quest", expect=True, strict=False),

    # -- go_to: leaving vs merely mentioning someone
    dict(id="goto/zh-leave", npc="marla", world=offered, say="好，我这就去铁匠铺找奥德尔。",
         key="go_to", expect="odell"),
    dict(id="goto/en-leave", npc="marla", world=fresh, say="Bye Marla, I'm off to see Wren.",
         key="go_to", expect="wren"),
    dict(id="goto/zh-mention", npc="marla", world=offered, say="奥德尔这人脾气好相处吗？",
         key="go_to", expect=None),
    dict(id="goto/en-mention", npc="marla", world=fresh, say="Is Wren always that sarcastic?",
         key="go_to", expect=None),
]

FALLBACK_CHOICES = ["Go on…", "Never mind — I'd best be off."]


def check(case, effects, world):
    if case["key"] == "__haggle__":
        q = world["quests"][0]
        ok = q["base_gold"] <= q["reward"]["gold"] <= q["base_gold"] * 2
        return ok, f"gold {q['reward']['gold']} (cap {q['base_gold'] * 2})"
    got = effects.get(case["key"])
    if case["expect"] is True:
        return bool(got), f"got {got!r}"
    if case["expect"] is None:
        return not got, f"got {got!r}"
    return got == case["expect"], f"got {got!r}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="also dump raw results to this path")
    args = ap.parse_args()

    results, compliance = [], {"mood": 0, "choices": 0, "turns": 0}
    for case in CASES:
        world = case["world"]()
        eng.CALL_LOG.clear()
        t0 = time.time()
        try:
            reply, effects = eng.npc_reply(case["npc"], case["say"], world)
            err = None
        except Exception as e:                       # network etc. — record, move on
            reply, effects, err = "", {}, str(e)
        turn_s = round(time.time() - t0, 2)

        ok, detail = check(case, effects, world)
        compliance["turns"] += 1
        compliance["mood"] += 1 if effects.get("mood") in eng.VALID_MOODS else 0
        ch = world["pending_choices"][case["npc"]]
        compliance["choices"] += 1 if (2 <= len(ch) <= 4 and ch != FALLBACK_CHOICES) else 0

        results.append(dict(case_id=case["id"], strict=case.get("strict", True),
                            ok=ok, detail=detail, seconds=turn_s, error=err,
                            calls=list(eng.CALL_LOG)))
        flag = "PASS" if ok else "FAIL"
        if not case.get("strict", True):
            flag = f"obs:{'yes' if ok else 'no'}"
        print(f"[{flag:>7}] {case['id']:<24} {detail}  ({turn_s}s)")

    # ---- report ----------------------------------------------------------
    strict = [r for r in results if r["strict"]]
    passed = sum(r["ok"] for r in strict)
    print("\n== Judgement accuracy ==")
    print(f"strict cases: {passed}/{len(strict)} passed "
          f"({100 * passed / len(strict):.0f}%)")
    for r in results:
        if r["strict"] and not r["ok"]:
            print(f"  FAILED: {r['case_id']} — {r['detail']}")
    obs = [r for r in results if not r["strict"]]
    print(f"observational cases: "
          + ", ".join(f"{r['case_id']}={'yes' if r['ok'] else 'no'}" for r in obs))

    print("\n== Protocol compliance ==")
    print(f"valid mood:            {compliance['mood']}/{compliance['turns']}")
    print(f"usable choices (2-4):  {compliance['choices']}/{compliance['turns']}")

    print("\n== Latency & tokens per call site ==")
    calls = [c for r in results for c in r["calls"]]
    for site in ("actor", "director", "quest_gen"):
        xs = [c for c in calls if c["site"] == site]
        if not xs:
            continue
        lat = sorted(c["seconds"] for c in xs)
        pin = statistics.mean(c["prompt_tokens"] for c in xs)
        pout = statistics.mean(c["completion_tokens"] for c in xs)
        print(f"{site:<10} n={len(xs):<3} p50={lat[len(lat) // 2]:.1f}s "
              f"p95={lat[int(len(lat) * 0.95) - 1]:.1f}s "
              f"tokens in/out = {pin:.0f}/{pout:.0f}")

    tin = sum(c["prompt_tokens"] for c in calls)
    tout = sum(c["completion_tokens"] for c in calls)
    turns = len(results)
    cost = (tin * PRICE_IN + tout * PRICE_OUT) / 1e6
    print("\n== Cost ==")
    print(f"total: {tin} in / {tout} out tokens over {turns} player turns")
    print(f"≈ ¥{cost:.4f} for the whole run → ¥{100 * cost / turns:.2f} per 100 "
          f"player turns (at ¥{PRICE_IN}/M in, ¥{PRICE_OUT}/M out)")

    if args.json:
        with open(args.json, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nraw results -> {args.json}")


if __name__ == "__main__":
    main()
