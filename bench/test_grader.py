"""Tests for the grader: comparison core (ported from Project 1 test_scorer.py)
plus the new ANSWER-parsing layer. No Spider data or model needed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from bench.grader import compare_results, parse_answer, grade


def check(name, got, want):
    status = "ok" if got == want else "FAIL"
    print(f"[{status}] {name}: got={got} want={want}")
    assert got == want, name


# ---------- comparison core (ported from Project 1) ----------

# ordered comparison cases
check("ordered exact", compare_results([(1,), (2,), (3,)], [(1,), (2,), (3,)], True), True)
check("ordered wrong order", compare_results([(1,), (2,), (3,)], [(3,), (2,), (1,)], True), False)

# unordered (multiset) comparison cases
check("unordered reorder ok", compare_results([(1,), (2,)], [(2,), (1,)], False), True)
check("multiset dup-sensitive", compare_results([(1,), (1,), (2,)], [(1,), (2,)], False), False)
check("multiset dup ok", compare_results([(1,), (1,), (2,)], [(2,), (1,), (1,)], False), True)

# column permutation
check("col perm ok", compare_results([("a", 1), ("b", 2)], [(1, "a"), (2, "b")], False), True)
check("col perm but data differs", compare_results([("a", 1), ("b", 2)], [(2, "a"), (1, "b")], False), False)

# numeric normalization
check("int vs float equal", compare_results([(5,)], [(5.0,)], False), True)
check("float noise rounded", compare_results([(1.0000001,)], [(1.0,)], False), True)
check("float genuine diff", compare_results([(1.5,)], [(2.5,)], False), False)

# shape mismatches
check("row count mismatch", compare_results([(1,)], [(1,), (2,)], False), False)
check("col count mismatch", compare_results([(1, 2)], [(1,)], False), False)
check("both empty", compare_results([], [], False), True)
check("both empty ordered", compare_results([], [], True), True)

# None handling
check("nulls compare", compare_results([(None,), (1,)], [(1,), (None,)], False), True)

# lists vs tuples (bench.jsonl stores lists after JSON round-trip)
check("list rows equal tuple rows", compare_results([[1], [2]], [(1,), (2,)], False), True)


# ---------- parse_answer ----------

check("parse json rows", parse_answer("ANSWER: [[3]]"), ([[3]], "json"))
check("parse json multi", parse_answer('ANSWER: [["a", 1], ["b", 2]]'), ([["a", 1], ["b", 2]], "json"))
check("parse flat list promoted", parse_answer("ANSWER: [3]"), ([[3]], "json"))
check("parse bare json scalar", parse_answer("ANSWER: 3"), ([[3]], "json"))
check("parse scalar string fallback", parse_answer("ANSWER: France"), ([["France"]], "scalar_fallback"))
check("parse row fallback", parse_answer("ANSWER: John, 42"), ([["John", 42]], "row_fallback"))
check("parse with preamble", parse_answer("The result is ready.\nANSWER: [[7]]"), ([[7]], "json"))
check("parse multiline json", parse_answer('ANSWER: [\n  [1],\n  [2]\n]'), ([[1], [2]], "json"))
check("parse no answer marker", parse_answer("I could not solve this."), (None, "no_answer"))
check("parse empty after marker", parse_answer("ANSWER: "), (None, "unparseable"))
check("parse empty text", parse_answer(""), (None, "no_answer"))
check("parse json dict rejected", parse_answer('ANSWER: {"a": 1}'), (None, "unparseable"))
check("parse quoted string stripped", parse_answer('ANSWER: "France"'), ([["France"]], "json"))
check("parse empty json array", parse_answer("ANSWER: []"), ([], "json"))
check("parse json null scalar", parse_answer("ANSWER: null"), ([[None]], "json"))


# ---------- grade (end to end, incl. precomputed order_matters flag) ----------

check("grade correct json", grade("ANSWER: [[3]]", [[3]], False), (True, "correct"))
check("grade correct with chatter", grade("Let me answer. ANSWER: [[3]]", [[3]], False), (True, "correct"))
check("grade scalar fallback", grade("ANSWER: 3", [[3]], False), (True, "correct"))
check("grade flat list", grade("ANSWER: [3]", [[3]], False), (True, "correct"))
check("grade row fallback", grade("ANSWER: John, 42", [["John", 42]], False), (True, "correct"))
check("grade string no quotes", grade("ANSWER: France", [["France"]], False), (True, "correct"))
check("grade wrong value", grade("ANSWER: [[3]]", [[4]], False), (False, "wrong"))
check("grade no answer", grade("I give up.", [[3]], False), (False, "no_answer"))
check("grade unparseable", grade("ANSWER: ", [[3]], False), (False, "unparseable_answer"))
check("grade order enforced", grade("ANSWER: [[2], [1]]", [[1], [2]], True), (False, "wrong"))
check("grade order not required", grade("ANSWER: [[2], [1]]", [[1], [2]], False), (True, "correct"))
check("grade empty gold correct", grade("ANSWER: []", [], False), (True, "correct"))
check("grade empty gold wrong", grade("ANSWER: [[1]]", [], False), (False, "wrong"))
check("grade int vs float", grade("ANSWER: [[5]]", [[5.0]], False), (True, "correct"))
check("grade null answer", grade("ANSWER: null", [[None]], False), (True, "correct"))

print("\nall grader tests passed.")
