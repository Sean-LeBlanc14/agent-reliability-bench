"""
Locks chat-block shape on the repair path. The original repair branch appended
assistant and user turns, rendering 5 blocks against an adapter trained on 3.
Nothing asserted the shape, so it survived until it was read by eye.
"""
import agent.tool
from agent.tool import _repair_question, _truncate_error
from agent.config import CONFIG
from prompt_utils import build_messages

DDL = "CREATE TABLE t (a INT)"


def _fake_run_query(db_id, sql):
    return ([(DDL,)], None)


def _messages(question, db_id):
    return build_messages(_fake_run_query, db_id, question, few_shots=[])


def test_repair_render_keeps_two_message_turns():
    q = _repair_question("How many?", "SELECT 1", "no such column: x")
    msgs = _messages(q, "db_repair")
    assert [m["role"] for m in msgs] == ["system", "user"]


def test_repair_matches_plain_block_shape():
    plain = _messages("How many?", "db_plain")
    repair = _messages(_repair_question("How many?", "SELECT 1", "boom"), "db_plain2")
    assert len(repair) == len(plain)


def test_single_generation_cue():
    q = _repair_question("How many?", "SELECT 1", "boom")
    assert not q.rstrip().endswith("SQL:")
    content = _messages(q, "db_cue")[-1]["content"]
    assert content.endswith("\nSQL:")
    assert content.count("\nSQL:") == 1


def test_previous_sql_is_not_preceded_by_a_generation_cue():
    # SQL:\n<query> is the training cue-then-answer pattern; a label ending in
    # SQL: would demonstrate emitting the previous query verbatim.
    assert "SQL:\nSELECT 1" not in _repair_question("How many?", "SELECT 1", "boom")


def test_question_leads_for_shared_prefix():
    assert _repair_question("How many?", "SELECT 1", "boom").startswith("How many?")


def test_error_truncation_respects_cap():
    cap = CONFIG["repair"]["max_error_chars"]
    text, flag = _truncate_error("x" * (cap + 50))
    assert flag and text.startswith("x" * cap) and "truncated" in text
    assert _truncate_error("short") == ("short", False)


def test_empty_result_constant_fits_the_error_slot():
    msg = CONFIG["repair"]["empty_result_message"]
    assert msg in _repair_question("How many?", "SELECT 1", msg)
