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


def load_bench():
    path = REPO_ROOT / "bench" / "bench.jsonl"
    return {json.loads(l)["task_id"]: json.loads(l) for l in open(path)}


def load_episodes(trace_path):
    with open(trace_path) as f:
        recs = [json.loads(l) for l in f]
    header = next((r for r in recs if r.get("event") == "run_open"), {})
    return [r for r in recs if r.get("event") == "episode"], header


def decompose(episodes, bench):
    """
    Bucket every episode. Interpretation failure is the load-bearing one: the
    final executed rows match gold, so the SQL was right and the ANSWER was not.
    """
    b = defaultdict(int)
    for e in episodes:
        b["total"] += 1
        if e["correct"]:
            b["correct"] += 1
            continue
        if e["terminal_reason"] != "answered":
            b["exec_failed"] += 1
            continue
        task = bench[e["task_id"]]
        rows = e["attempts"][-1]["rows"]
        if compare_results(task["gold_rows"], rows, task["order_matters"]):
            b["interpretation_failure"] += 1
        else:
            b["tool_wrong"] += 1
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace", nargs="?", help="trace file (default: most recent in runs/)")
    args = ap.parse_args()

    trace = args.trace or sorted(glob.glob(str(REPO_ROOT / "runs" / "*.jsonl")))[-1]
    episodes, header = load_episodes(trace)
    bench = load_bench()

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
        print(f"  exec failed (repair-addressable) : {b['exec_failed']}")
        print(f"  wrong SQL                        : {b['tool_wrong']}")
        print(f"  interpretation failure           : {b['interpretation_failure']}"
              f"  ({b['interpretation_failure'] / n:.1%} of episodes)")
        print()


if __name__ == "__main__":
    main()
