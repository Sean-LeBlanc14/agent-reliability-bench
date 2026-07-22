"""
Grader tests: comparison core (ported from Project 1 test_scorer.py) plus the
ANSWER-parsing layer added here. No Spider data or model needed.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from bench.grader import compare_results, grade, parse_answer


# ---------- comparison core (ported from Project 1) ----------

@pytest.mark.parametrize("name,gold,pred,order,want", [
    ("ordered exact",            [(1,), (2,), (3,)], [(1,), (2,), (3,)], True,  True),
    ("ordered wrong order",      [(1,), (2,), (3,)], [(3,), (2,), (1,)], True,  False),
    ("unordered reorder ok",     [(1,), (2,)],       [(2,), (1,)],       False, True),
    ("multiset dup-sensitive",   [(1,), (1,), (2,)], [(1,), (2,)],       False, False),
    ("multiset dup ok",          [(1,), (1,), (2,)], [(2,), (1,), (1,)], False, True),
    ("col perm ok",              [("a", 1), ("b", 2)], [(1, "a"), (2, "b")], False, True),
    ("col perm data differs",    [("a", 1), ("b", 2)], [(2, "a"), (1, "b")], False, False),
    ("int vs float equal",       [(5,)],             [(5.0,)],           False, True),
    ("float noise rounded",      [(1.0000001,)],     [(1.0,)],           False, True),
    ("float genuine diff",       [(1.5,)],           [(2.5,)],           False, False),
    ("row count mismatch",       [(1,)],             [(1,), (2,)],       False, False),
    ("col count mismatch",       [(1, 2)],           [(1,)],             False, False),
    ("both empty",               [],                 [],                 False, True),
    ("both empty ordered",       [],                 [],                 True,  True),
    ("nulls compare",            [(None,), (1,)],    [(1,), (None,)],    False, True),
    # bench.jsonl stores lists after the JSON round-trip
    ("list rows equal tuples",   [[1], [2]],         [(1,), (2,)],       False, True),
])
def test_compare_results(name, gold, pred, order, want):
    assert compare_results(gold, pred, order) is want


# ---------- answer parsing ----------

@pytest.mark.parametrize("name,text,want", [
    ("json rows",            "ANSWER: [[3]]",                    ([[3]], "json")),
    ("json multi",           'ANSWER: [["a", 1], ["b", 2]]',     ([["a", 1], ["b", 2]], "json")),
    ("flat list promoted",   "ANSWER: [3]",                      ([[3]], "json")),
    ("bare json scalar",     "ANSWER: 3",                        ([[3]], "json")),
    ("json null scalar",     "ANSWER: null",                     ([[None]], "json")),
    ("quoted string",        'ANSWER: "France"',                 ([["France"]], "json")),
    ("empty json array",     "ANSWER: []",                       ([], "json")),
    ("multiline json",       "ANSWER: [\n  [1],\n  [2]\n]",      ([[1], [2]], "json")),
    ("with preamble",        "The result is ready.\nANSWER: [[7]]", ([[7]], "json")),
    ("scalar fallback",      "ANSWER: France",                   ([["France"]], "scalar_fallback")),
    ("row fallback",         "ANSWER: John, 42",                 ([["John", 42]], "row_fallback")),
    ("no answer marker",     "I could not solve this.",          (None, "no_answer")),
    ("empty after marker",   "ANSWER: ",                         (None, "unparseable")),
    ("empty text",           "",                                 (None, "no_answer")),
    ("json dict rejected",   'ANSWER: {"a": 1}',                 (None, "unparseable")),
])
def test_parse_answer(name, text, want):
    assert parse_answer(text) == want


# ---------- end to end ----------

@pytest.mark.parametrize("name,text,gold,order,want", [
    ("correct json",        "ANSWER: [[3]]",                [[3]],           False, (True, "correct")),
    ("correct with chatter","Let me answer. ANSWER: [[3]]", [[3]],           False, (True, "correct")),
    ("scalar fallback",     "ANSWER: 3",                    [[3]],           False, (True, "correct")),
    ("flat list",           "ANSWER: [3]",                  [[3]],           False, (True, "correct")),
    ("row fallback",        "ANSWER: John, 42",             [["John", 42]],  False, (True, "correct")),
    ("string no quotes",    "ANSWER: France",               [["France"]],    False, (True, "correct")),
    ("null answer",         "ANSWER: null",                 [[None]],        False, (True, "correct")),
    ("int vs float",        "ANSWER: [[5]]",                [[5.0]],         False, (True, "correct")),
    ("empty gold correct",  "ANSWER: []",                   [],              False, (True, "correct")),
    ("wrong value",         "ANSWER: [[3]]",                [[4]],           False, (False, "wrong")),
    ("empty gold wrong",    "ANSWER: [[1]]",                [],              False, (False, "wrong")),
    ("no answer",           "I give up.",                   [[3]],           False, (False, "no_answer")),
    ("unparseable",         "ANSWER: ",                     [[3]],           False, (False, "unparseable_answer")),
    ("order enforced",      "ANSWER: [[2], [1]]",           [[1], [2]],      True,  (False, "wrong")),
    ("order not required",  "ANSWER: [[2], [1]]",           [[1], [2]],      False, (True, "correct")),
])
def test_grade(name, text, gold, order, want):
    assert grade(text, gold, order) == want
