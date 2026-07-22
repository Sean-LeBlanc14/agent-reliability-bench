"""
Arm 2 (resample-on-failure): the loop, with no error feedback.

Every resample re-queries the tool with the original question only. The
tool's repair parameters are deliberately never passed here; that omission
is the entire difference between this arm and arm 3, and holding the step
cap equal is what keeps H1b a comparison of information rather than of
attempt budget.

Loop control is deterministic. The orchestrator is not consulted about
whether to retry, so the arms differ in what the tool is told and in
nothing else.
"""

from __future__ import annotations

from agent.config import CONFIG
from agent.extraction import EXTRACTION_SYSTEM, extract_prompt
from bench.grader import grade, parse_answer

ARM = 2


def _trigger(res) -> str | None:
    """The two locked repair predicates, in one place. No third condition."""
    if not res.ok:
        return "exec_error"
    if not res.rows:
        return "empty_result"
    return None


def run_episode(tool, executor, llm, task, run_idx: int) -> dict:
    max_attempts = CONFIG["agent"]["max_attempts"]
    attempts = []
    res = None
    trig = None

    for attempt_idx in range(max_attempts):
        r = tool.generate_sql(
            task["task_id"], task["db_id"], task["question"], run_idx, attempt_idx
        )
        res = executor.run(task["db_id"], r["sql"], r["tool_output_id"])
        trig = _trigger(res)

        attempts.append({
            "attempt_idx": attempt_idx,
            "tool_prompt": r["prompt"],
            "sql": r["sql"],
            "tool_output_id": r["tool_output_id"],
            "exec_ok": res.ok,
            "exec_error": res.error,
            "truncated": res.truncated,
            "row_count": len(res.rows) if res.rows is not None else None,
            "rows": res.model_view() if res.ok else None,
            "trigger": trig,
        })

        if trig is None:
            break

    # Extraction runs whenever the final attempt executed, empty rows included
    if res.ok:
        ext_prompt = extract_prompt(task["question"], res.model_view())
        answer_raw = llm.complete(
            EXTRACTION_SYSTEM, [{"role": "user", "content": ext_prompt}]
        )
        terminal = "answered" if trig is None else "exhausted_empty"
    else:
        ext_prompt, answer_raw, terminal = None, "", "exhausted_exec_failed"

    correct, grade_status = grade(answer_raw, task["gold_rows"], task["order_matters"])
    _, parse_status = parse_answer(answer_raw)

    return {
        "task_id": task["task_id"],
        "db_id": task["db_id"],
        "difficulty": task["difficulty"],
        "arm": ARM,
        "run_idx": run_idx,
        "attempts": attempts,
        "n_attempts": len(attempts),
        "extraction_prompt": ext_prompt,
        "answer_raw": answer_raw,
        "correct": correct,
        "grade_status": grade_status,
        "parse_status": parse_status,
        "terminal_reason": terminal,
    }

