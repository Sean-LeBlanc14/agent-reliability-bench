"""
Arm-2 and arm-3 loop semantics, tested rather than asserted.

Two things here are load-bearing and invisible at runtime. First, the arm 2 /
arm 3 boundary must hold in both directions: arm 2 must never pass repair
context to the tool, and arm 3 must always pass it on re-query. That single
difference is what H1b measures, so a copy-paste in either direction would
silently erase the result. Second, the step cap must bind, since arms 2 and 3
share it and an off-by-one would confound feedback with attempt budget.

Stubs stand in for the tool and the orchestrator, but the Executor is real,
so the tool-output-id gate is exercised rather than mocked - the loop cannot
reach the database with SQL the tool didn't mint.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from agent.config import CONFIG
from agent.executor import Executor
from agent.loop import run_episode, ARM_RESAMPLE, ARM_REPAIR

DB_ID = "car_1"
OK = "SELECT 1;"
EMPTY = "SELECT 1 WHERE 0;"
BAD = "SELEC 1;"

TASK = {
    "task_id": "t000",
    "db_id": DB_ID,
    "question": "how many?",
    "difficulty": "easy",
    "gold_rows": [[1]],
    "order_matters": False,
}


class StubTool:
    """Serves scripted SQL and records every call for contract assertions."""

    def __init__(self, script):
        self._script = script          # SQL returned per attempt, last value repeats
        self._registry = {}
        self.calls = []

    def generate_sql(self, task_id, db_id, question, run_idx, attempt_idx,
                     previous_sql=None, executor_error=None):
        self.calls.append({
            "attempt_idx": attempt_idx,
            "question": question,
            "previous_sql": previous_sql,
            "executor_error": executor_error,
        })
        sql = self._script[min(attempt_idx, len(self._script) - 1)]
        tid = f"tid-{attempt_idx}"
        self._registry[tid] = sql
        return {"sql": sql, "tool_output_id": tid, "prompt": f"<prompt {attempt_idx}>", "error_truncated": False}

    def verify(self, tool_output_id, sql):
        return self._registry.get(tool_output_id) == sql


class StubLLM:
    """Stands in for the extraction call; records whether it ran."""

    model = "stub"

    def __init__(self):
        self.calls = []

    def complete(self, system, messages):
        self.calls.append(messages)
        return "ANSWER: 1"


def _run(script, arm=ARM_RESAMPLE):
    tool = StubTool(script)
    llm = StubLLM()
    ep = run_episode(tool, Executor(tool), llm, TASK, run_idx=0, arm=arm)
    return ep, tool, llm


def test_no_repair_context_ever_passed():
    """The arm 2 / arm 3 boundary: every re-query carries the question alone."""
    ep, tool, _ = _run([BAD])
    assert len(tool.calls) > 1, "loop did not resample; test proves nothing"
    for c in tool.calls:
        assert c["previous_sql"] is None
        assert c["executor_error"] is None
        assert c["question"] == TASK["question"]


def test_step_cap_binds():
    ep, tool, _ = _run([BAD])
    assert ep["n_attempts"] == CONFIG["agent"]["max_attempts"]
    assert len(tool.calls) == CONFIG["agent"]["max_attempts"]
    assert ep["terminal_reason"] == "exhausted_exec_failed"


def test_attempt_idx_increments_from_zero():
    """Seeds derive from attempt_idx, so a repeated index would resample identically."""
    _, tool, _ = _run([BAD])
    assert [c["attempt_idx"] for c in tool.calls] == list(range(len(tool.calls)))


def test_success_stops_the_loop():
    ep, tool, llm = _run([OK])
    assert ep["n_attempts"] == 1
    assert ep["terminal_reason"] == "answered"
    assert len(llm.calls) == 1


def test_resample_recovers_after_failure():
    ep, _, _ = _run([BAD, OK])
    assert ep["n_attempts"] == 2
    assert ep["terminal_reason"] == "answered"
    assert ep["attempts"][0]["trigger"] == "exec_error"
    assert ep["attempts"][1]["trigger"] is None


def test_empty_result_triggers_and_still_extracts():
    """An empty final result is graded, not suppressed: a confident ANSWER off
    zero rows is a hallucination the failure taxonomy needs to see."""
    ep, _, llm = _run([EMPTY])
    assert ep["n_attempts"] == CONFIG["agent"]["max_attempts"]
    assert ep["terminal_reason"] == "exhausted_empty"
    assert {a["trigger"] for a in ep["attempts"]} == {"empty_result"}
    assert len(llm.calls) == 1, "extraction must run on an empty final result"


def test_executed_sql_is_always_tool_minted():
    """Loop-level restatement of the no-authorship invariant: the real Executor
    raises on anything unminted, so reaching a terminal state proves the gate held."""
    ep, tool, _ = _run([BAD, EMPTY, OK])
    for a in ep["attempts"]:
        assert tool.verify(a["tool_output_id"], a["sql"])


def test_repair_arm_passes_previous_sql_and_error():
    """Arm 3's only difference: attempt 0 is bare, every re-query carries the
    previous SQL and the executor error. Question stays the original, since
    repair composition happens inside the tool, not here."""
    _, tool, _ = _run([BAD], arm=ARM_REPAIR)
    assert len(tool.calls) > 1, "loop did not resample; test proves nothing"
    assert tool.calls[0]["previous_sql"] is None
    assert tool.calls[0]["executor_error"] is None
    for c in tool.calls[1:]:
        assert c["previous_sql"] == BAD
        assert c["executor_error"]
        assert c["question"] == TASK["question"]


def test_repair_arm_substitutes_the_empty_result_constant():
    """The empty branch has no executor error, so the frozen constant stands in.
    This is the whole of _repair_context's logic and nothing else covers it."""
    _, tool, _ = _run([EMPTY], arm=ARM_REPAIR)
    assert tool.calls[1]["executor_error"] == CONFIG["repair"]["empty_result_message"]
