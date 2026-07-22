"""The gate between orchestrator-approved SQL and the database."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from agent.config import CONFIG
from paths import DB_DIR


@dataclass
class ExecResult:
    ok: bool
    rows: Optional[list]     # full result on success; the grading object
    error: Optional[str]    # structured message on failure; fed to the tool on repair
    truncated: bool = False  # True iff the model-facing view dropped rows


    def model_view(self) -> list:
        cap = CONFIG["executor"]["max_result_rows"]
        return self.rows[:cap] if self.rows else []


def _connect(db_id: str) -> sqlite3.Connection:
    """Every read of a benchmark DB goes through here."""
    db = DB_DIR / db_id / f"{db_id}.sqlite"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.text_factory = lambda b: b.decode(errors="replace")
    return con


def read_only_query(db_id: str, sql: str) -> tuple:
    """Schema introspection for the tool's prompt builder."""
    con = _connect(db_id)
    try:
        return con.execute(sql).fetchall(), None
    except Exception as e:
        return None, str(e)
    finally:
        con.close()


class Executor:
    def __init__(self, tool):
        # Holds the tool only to call verify(), not to generate.
        self._tool = tool


    def run(self, db_id: str, sql: str, tool_output_id: str) -> ExecResult:
        if not self._tool.verify(tool_output_id, sql):
            raise PermissionError(
                "SQL not vouched for by tool_output_id: refusing to execute "
                "(no-authorship invariant)"
            )
        return self._execute(db_id, sql)


    def _execute(self, db_id: str, sql: str) -> ExecResult:
        con = _connect(db_id)

        # Opcode-budget abort: SQLite has no wall-clock timeout.
        # The budget only has to be high enough that no legitimate
        # (<=20-row gold) query hits it, and low enough to stop a
        # runaway. Aborting raises OperationalError -> caught below
        # as a failure
        budget = CONFIG["executor"]["timeout_s"] * 5_000_000 # opcodes
        remaining = [budget]

        def _tick():
            remaining[0] -= 1
            return 1 if remaining[0] <= 0 else 0 # nonzero aborts the query

        con.set_progress_handler(_tick, 1000)
        try:
            rows = [list(r) for r in con.execute(sql).fetchall()]
            return ExecResult(ok=True, rows=rows, error=None,
                              truncated=len(rows) > CONFIG["executor"]["max_result_rows"])
        except Exception as e:
            return ExecResult(ok=False, rows=None, error=str(e))
        finally:
            con.set_progress_handler(None, 1000)
            con.close()
