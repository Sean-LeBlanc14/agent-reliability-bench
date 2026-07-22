"""Arm 1 (single-shot) over the full bench, k=1, tagged smoke."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from paths import REPO_ROOT
from agent.config import CONFIG_HASH
from agent.tool import Tool
from agent.executor import Executor, read_only_query
from agent.llm import LLM
from agent.extraction import EXTRACTION_SYSTEM, extract_prompt
from agent.trace import Tracer
from bench.grader import grade, parse_answer

BENCH = REPO_ROOT / "bench" / "bench.jsonl"
ARM = 1
RUN_IDX = 0 # smoke is k=1; this is run 0


def run_single_shot(tool, executor, llm, task):
    """One arm-1 episode: generate -> execute -> extract -> grade. No loop, no repair"""
    r = tool.generate_sql(task["task_id"], task["db_id"], task["question"], RUN_IDX, attempt_idx=0)
    res = executor.run(task["db_id"], r["sql"], r["tool_output_id"])

    attempt = {
        "attempt_idx": 0,
        "tool_prompt": r["prompt"],
        "sql": r["sql"],
        "tool_output_id": r["tool_output_id"],
        "exec_ok": res.ok,
        "exec_error": res.error,
        "truncated": res.truncated,
        "row_count": len(res.rows) if res.rows is not None else None,
        "rows": res.model_view() if res.ok else None,  # what the model actually saw (capped)
    }

    if res.ok:
        ext_prompt = extract_prompt(task["question"], res.model_view())
        answer_raw = llm.complete(EXTRACTION_SYSTEM, [{"role": "user", "content": ext_prompt}])
        terminal = "answered"
    else:
        # Arm 1 has no repair: a failed query is a failed task, full stop
        ext_prompt, answer_raw, terminal = None, "", "exec_failed"

    correct, grade_status = grade(answer_raw, task["gold_rows"], task["order_matters"])
    _, parse_status = parse_answer(answer_raw)

    return {
        "task_id": task["task_id"],
        "db_id": task["db_id"],
        "difficulty": task["difficulty"],
        "arm": ARM,
        "run_idx": RUN_IDX,
        "attempts": [attempt],
        "extraction_prompt": ext_prompt,
        "answer_raw": answer_raw,
        "correct": correct,
        "grade_status": grade_status,
        "parse_status": parse_status,
        "terminal_reason": terminal,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="cap tasks (PASS check on a slice)")
    args = ap.parse_args()

    tasks = [json.loads(l) for l in open(BENCH)]
    if args.limit:
        tasks = tasks[: args.limit]

    tool = Tool(read_only_query)
    executor = Executor(tool)
    llm = LLM()

    by_diff = defaultdict(lambda: [0, 0]) # difficulty -> [correct, total]
    t0 = time.perf_counter()

    with Tracer(REPO_ROOT / "runs", "smoke", CONFIG_HASH, llm.model) as tracer:
        for i, task in enumerate(tasks):
            ep = run_single_shot(tool, executor, llm, task)
            tracer.log_episode(**ep)
            by_diff[ep["difficulty"]][0] += int(ep["correct"])
            by_diff[ep["difficulty"]][1] += 1
            print("." if ep["correct"] else "x", end="", flush=True)
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{len(tasks)}")

    dt = time.perf_counter() - t0
    total = len(tasks)
    correct = sum(c for c, _ in by_diff.values())

    print("\n\nsmoke run (arm 1, k=1) - CALIBRATION ONLY, never reported")
    print(f"traces: {tracer.path}")
    print(f"episodes: {total}  wall: {dt:.1f}s  ({dt / total:.2f}s/episode)")
    print(f"extrapolated Day 7 (~1350 episodes): {dt / total * 1350 / 60:.1f} min at this rate")
    print(f"pass@1 overall: {correct}/{total} = {correct / total:.1%}")
    for d in ("easy", "medium", "hard", "extra"):
        c, n = by_diff[d]
        if n:
            print(f"  {d:6s}: {c}/{n} = {c / n:.1%}")
    if total and correct / total >= 0.80:
        print("headroom: arm 1 >=80% - consider reweighting toward hard/extra before agent data")


if __name__ == "__main__":
    main()
