"""
Failure decomposition for a run's traces: pass@1 plus the ANSWER-vs-rows split.

This is where the secondary diagnostic lives. A wrong answer is either wrong SQL
(tool failure) or right SQL misread (interpretation failure), and only the trace
can tell them apart - it holds both the executed rows and the emitted ANSWER.
Grouped by arm so the same script serves the smoke run and the 3-arm main run.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from bench.grader import compare_results
from paths import REPO_ROOT

DIFFICULTIES = ("easy", "medium", "hard", "extra")

KEYS = ("total", "correct", "no_runnable_sql", "exhausted_empty", "final_empty",
        "tool_wrong", "degraded", "interpretation_failure", "attempt_pairs", "verbatim_repeats")


def load_bench():
    path = REPO_ROOT / "bench" / "bench.jsonl"
    return {json.loads(l)["task_id"]: json.loads(l) for l in open(path)}


def load_episodes(trace_path):
    with open(trace_path) as f:
        recs = [json.loads(l) for l in f]
    header = next((r for r in recs if r.get("event") == "run_open"), {})
    return [r for r in recs if r.get("event") == "episode"], header


def classify(e, bench) -> str:
    """Bucket one episode. One source of truth for the counts and the worklist."""
    if e["correct"]:
        return "correct"
    # run_arm1 and loop emit different strings for the same terminal state
    if e["terminal_reason"] in ("exhausted_exec_failed", "exec_failed"):
        return "no_runnable_sql"
    if e["terminal_reason"] == "exhausted_empty":
        return "exhausted_empty"
    task = bench[e["task_id"]]
    rows = e["attempts"][-1]["rows"]
    if compare_results(task["gold_rows"], rows, task["order_matters"]):
        return "interpretation_failure"
    return "tool_wrong"


def flatten(x):
    if isinstance(x, (list, tuple)):
        return [v for i in x for v in flatten(i)]
    return [x]


def unsupported(e):
    """Scalars in the ANSWER that appear nowhere in the rows the tool returned.

    Null is instructed behavior for a missing value, so it is not a fabrication.
    Truncated display makes this uncheckable by eye, hence the full-row check.
    """
    raw = e["answer_raw"].split("ANSWER:", 1)[-1].strip()
    try:
        vals = flatten(json.loads(raw))
    except json.JSONDecodeError:
        return None
    have = {str(v) for v in flatten(e["attempts"][-1].get("rows") or [])}
    return [v for v in vals if v is not None and str(v) not in have]


def degraded(e) -> bool:
    """Empty result at attempt i followed by an exec error at attempt i+1.

    Mechanical stand-in for the dropped repair-induced-regression label, which
    was unreachable: a successful non-empty execution ends the episode, so
    repair only ever fires on already-failed states.
    """
    a = e["attempts"]
    return any(
        a[i]["trigger"] == "empty_result" and not a[i + 1]["exec_ok"]
        for i in range(len(a) - 1)
    )


def repeats(e):
    """Consecutive attempt pairs whose SQL is byte-identical.

    Pre-registered because the render check caught the tool re-emitting the
    previous query. Exact match, no normalization: a whitespace difference
    means a different token sequence, which is what "did feedback change the
    output" is asking.
    """
    a = e["attempts"]
    pairs = [(a[i]["sql"], a[i + 1]["sql"]) for i in range(len(a) - 1)]
    return len(pairs), sum(p == q for p, q in pairs)


def decompose(episodes, bench):
    b = defaultdict(int)
    for e in episodes:
        b["total"] += 1
        p, r = repeats(e)
        b["attempt_pairs"] += p
        b["verbatim_repeats"] += r
        if e["attempts"][-1].get("rows") == []:
            b["final_empty"] += 1
        if degraded(e):
            b["degraded"] += 1
        b[classify(e, bench)] += 1
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace", help="trace file")
    ap.add_argument("--out", help="append per-cell counts as JSONL to this path")
    ap.add_argument("--worklist", help="write bucketed episode identities to this path")
    ap.add_argument("--run-idx", type=int, help="restrict worklist to one run index")
    args = ap.parse_args()

    trace = args.trace
    episodes, header = load_episodes(trace)
    bench = load_bench()

    if args.out and header.get("git_commit") != "9ca1c7e":
        raise SystemExit(f"{Path(trace).name} is not from the frozen commit")

    print(f"trace : {Path(trace).name}")
    print(f"tag   : {header.get('run_tag')}  config: {header.get('config_hash')}  "
          f"commit: {header.get('git_commit')}")
    print(f"model : {header.get('orchestrator_model')}\n")

    by_arm = defaultdict(list)
    for e in episodes:
        by_arm[e["arm"]].append(e)

    for arm in sorted(by_arm):
        eps = by_arm[arm]
        b = decompose(eps, bench)
        n = b["total"]
        print(f"--- arm {arm}  ({n} episodes) ---")
        print(f"pass@1: {b['correct']}/{n} = {b['correct'] / n:.1%}")
        for d in DIFFICULTIES:
            sub = [e for e in eps if e["difficulty"] == d]
            if sub:
                c = sum(e["correct"] for e in sub)
                print(f"  {d:6s}: {c}/{len(sub)} = {c / len(sub):.1%}")
        print(f"failures: {n - b['correct']}")
        print(f"  no runnable SQL                  : {b['no_runnable_sql']}")
        print(f"  exhausted empty                  : {b['exhausted_empty']}")
        print(f"  final result empty (any terminal)  : {b['final_empty']}")
        print(f"  wrong SQL                        : {b['tool_wrong']}")
        print(f"  repair-induced degradation         : {b['degraded']}")
        if b["attempt_pairs"]:
            print(f"  verbatim repetition                : {b['verbatim_repeats']}/{b['attempt_pairs']}"
                  f" = {b['verbatim_repeats'] / b['attempt_pairs']:.1%} of consecutive pairs")
        print(f"  interpretation failure           : {b['interpretation_failure']}"
              f"  ({b['interpretation_failure'] / n:.1%} of episodes)")
        print()

        if args.out:
            with open(args.out, "a") as f:
                f.write(json.dumps({
                    "arm": arm,
                    "run_idx": eps[0]["run_idx"],
                    "trace": Path(trace).name,
                    "git_commit": header.get("git_commit"),
                    "config_hash": header.get("config_hash"),
                    **{k: b[k] for k in KEYS},
                }) + "\n")

    if args.worklist:
        # Join key for failure_labels.jsonl: every label traceable to a frozen episode
        with open(args.worklist, "w") as f:
            for i, e in enumerate(episodes):
                if args.run_idx is not None and e["run_idx"] != args.run_idx:
                    continue
                bucket = classify(e, bench)
                if bucket == "correct":
                    continue
                f.write(json.dumps({
                    "task_id": e["task_id"],
                    "arm": e["arm"],
                    "run_idx": e["run_idx"],
                    "bucket": bucket,
                    "trace": Path(trace).name,
                    "episode_idx": i,
                }) + "\n")
        print(f"worklist: {args.worklist}")


if __name__ == "__main__":
    main()
