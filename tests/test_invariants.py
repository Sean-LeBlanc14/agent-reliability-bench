"""
The no-authorship invariant, tested rather than asserted.

The executor is the enforcement point: nothing reaches the database unless the
tool vouches for the exact SQL string. These cover the three ways that goes
wrong - forged id, edited SQL under a real id, stale id from an earlier attempt -
plus the happy path, so "enforced structurally" cites evidence, not a design story.

Tool.__init__ loads a 1.5B model; verify() needs only the registry, so these build
the object without __init__ to stay fast and GPU-free.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from agent.executor import Executor
from agent.tool import Tool

DB_ID = "car_1"    # any bench db: SELECT 1 touches no schema
SQL = "SELECT 1;"


def _tool_with(registry):
    tool = object.__new__(Tool)
    tool._registry = registry
    return tool


def test_valid_id_executes():
    tool = _tool_with({"tid": SQL})
    res = Executor(tool).run(DB_ID, SQL, "tid")
    assert res.ok
    assert res.rows == [[1]]


def test_forged_id_rejected():
    tool = _tool_with({})
    with pytest.raises(PermissionError):
        Executor(tool).run(DB_ID, SQL, "not-a-real-id")


def test_edited_sql_under_valid_id_rejected():
    """The id vouches for a string, not for the fact that a tool call happened."""
    tool = _tool_with({"tid": SQL})
    with pytest.raises(PermissionError):
        Executor(tool).run(DB_ID, SQL + " LIMIT 1", "tid")


def test_stale_id_rejected():
    """An id minted for an earlier attempt cannot vouch for a later query."""
    tool = _tool_with({"old": SQL})
    with pytest.raises(PermissionError):
        Executor(tool).run(DB_ID, "SELECT 2;", "old")

