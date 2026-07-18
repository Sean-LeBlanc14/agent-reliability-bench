"""
Grader: agent answer text vs gold rows.

Comparison core (compare_results and helpers) is adapted from text2sql-finetune
scorer.py, where it was validated by 18 unit tests and produced the execution
accuracy numbers for that project.

Policies inherited: order-from-gold, multiset (duplicate sensitive) comparison when
unordered, column permutation matching, numeric coercion to float rounded to 6 digits,
bytes decoded to str.

Changes from text2sql-finetine:
- order_matters is precomputed in bench.jsonl via top-level ORDER BY detection rather
  than a match-anywhere regex.
- New layer: parse_answer() converts the agent's free-text `ANSWER: ...` into rows
  before comparison.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Optional, Sequence

FLOAT_NDIGITS = 6
MAX_PERM_COLS = 6

_ANSWER_RE = re.compile(r"ANSWER\s*:\s*(.*)", re.DOTALL)


# --- comparison core (from text2sql-finetune) ---

def _norm_cell(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return round(float(v), FLOAT_NDIGITS)
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8", "replace")
        except Exception:
            return str(v)
    return v


def _norm_rows(rows: Sequence[Sequence[Any]]) -> list:
    return [tuple(_norm_cell(c) for c in row) for row in rows]


def _column_candidates(gold: list, pred: list, ncols: int):
    gold_cols = [Counter(r[i] for r in gold) for i in range(ncols)]
    pred_cols = [Counter(r[i] for r in pred) for i in range(ncols)]
    cands = []
    for gi in range(ncols):
        c = [pi for pi in range(ncols) if gold_cols[gi] == pred_cols[pi]]
        if not c:
            return None
        cands.append(c)
    return cands


def _iter_column_perms(cands, ncols):
    used = [False] * ncols
    assign = [0] * ncols

    def bt(gi):
        if gi == ncols:
            yield tuple(assign)
            return
        for pi in cands[gi]:
            if not used[pi]:
                used[pi] = True
                assign[gi] = pi
                yield from bt(gi + 1)
                used[pi] = False

    yield from bt(0)


def compare_results(gold_rows, pred_rows, order_matters: bool) -> bool:
    gold = _norm_rows(gold_rows or [])
    pred = _norm_rows(pred_rows or [])

    if len(gold) != len(pred):
        return False
    if len(gold) == 0:
        return True
    ncols = len(gold[0])
    if len(pred[0]) != ncols:
        return False

    if ncols == 1 or ncols > MAX_PERM_COLS:
        return gold == pred if order_matters else Counter(gold) == Counter(pred)

    cands = _column_candidates(gold, pred, ncols)
    if cands is None:
        return False

    gold_counter = None if order_matters else Counter(gold)
    for perm in _iter_column_perms(cands, ncols):
        pred_perm = [tuple(row[perm[i]] for i in range(ncols)) for row in pred]
        if order_matters:
            if gold == pred_perm:
                return True
        else:
            if gold_counter == Counter(pred_perm):
                return True
    return False


# --- answer parsing (exclusive to agent-reliability-bench) ---

def parse_answer(text: str):
    """
    Extract rows from agent output ending in `ANSWER: ...`.

    Returns (rows, parse_status)
    """

    if not text:
        return None, "no_answer"
    m = _ANSWER_RE.search(text)
    if not m:
        return None, "no_answer"
    raw = m.group(1).strip()
    if not raw:
        return None, "unparseable"

    try:
        val = json.loads(raw)
        if isinstance(val, list):
            if all(isinstance(r, list) for r in val):
                return val, "json"
            # flat list -> single row
            if all(not isinstance(r, (list, dict)) for r in val):
                return [val], "json"
        if isinstance(val, (int, float, str)):
            return [[val]],"json"
        return None, "unparseable"
    except (json.JSONDecodeError, ValueError):
        pass

    single_line = raw.splitlines()[0].strip()
    if "," not in single_line:
        return [[_coerce(single_line)]], "scalar_fallback"

    cells = [_coerce(c.strip()) for c in single_line.split(",")]
    return [cells], "row_fallback"


def _coerce(s: str):
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s.strip("\"'")


def grade(answer_text: str, gold_rows, order_matters: bool):
    """Returns (correct: bool, status: str)"""

    rows, parse_status = parse_answer(answer_text)
    if rows is None:
        return False, ("no_answer" if parse_status == "no_answer" else "unparseable_answer")
    ok = compare_results(gold_rows, rows, order_matters)
    return ok, ("correct" if ok else "wrong")

