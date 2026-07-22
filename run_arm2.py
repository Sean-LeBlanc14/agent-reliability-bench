"""Arm 2 (resample-on-failure) over a bench slice. Pipeline check, not a measurement"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from paths import REPO_ROOT
from agent.config import CONFIG, CONFIG_HASH
from agent.tool import Tool
from agent.executor import Executor, read_only_query
from agent.llm import LLM
from agent.loop import run_episode
from agent.trace import Tracer

BENCH = REPO_ROOT / "bench" / "bench.jsonl"
RUN_IDX = 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--task-ids", default=None, help="comma-separated; overrides --limit")
    args = ap.parse_args()

    tasks = [json.loads(l) for l in open(BENCH)]
    if args.task_ids:
        want = set(args.task_ids.split(","))
        tasks = [t for t in tasks if str(t["task_id"]) in want]
    elif args.limit:
        tasks = tasks[: args.limit]

    tool = Tool(read_only_query)
    executor = Executor(tool)
    llm = LLM()

    episodes = []
    t0 = time.perf_counter()

    with Tracer(REPO_ROOT / "runs", "smoke", CONFIG_HASH, llm.model) as tracer:
        for task in tasks:
            ep = run_episode(tool, executor, llm, task, RUN_IDX)
            tracer.log_episode(**ep)
            episodes.append(ep)
            print("." if ep["correct"] else "x", end="", flush=True)

    dt = time.perf_counter() - t0
    n = len(episodes)
    correct = sum(int(e["correct"]) for e in episodes)

    print(f"\n\narm 2 pipeline check - not a reported number")
    print(f"traces: {tracer.path}")
    print(f"episodes: {n}  wall: {dt:.1f}s  ({dt / n:.2f}s/episode)")
    print(f"pass@1: {correct}/{n}")
    print(f"attempts used: {dict(sorted(Counter(e['n_attempts'] for e in episodes).items()))}")
    print(f"terminal:      {dict(Counter(e['terminal_reason'] for e in episodes))}")
    print(f"triggers:      {dict(Counter(a['trigger'] for e in episodes for a in e['attempts'] if a['trigger']))}")
    print(f"cap: {CONFIG['agent']['max_attempts']}")


if __name__ == "__main__":
    main()
