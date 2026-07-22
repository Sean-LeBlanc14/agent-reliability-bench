"""
JSONL run logger. One file per run, one line per episode, each line
self-describing (run tag, config hash, model stamped on every line)
so a single excerpted line still identifies the run that produced it.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path


def _git_commit() -> str | None:
    # Best effort provenance; a checkout without git still logs, just without it.
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


class Tracer:
    def __init__(self, runs_dir, run_tag: str, arm: int, run_idx: int,
                 config_hash: str, orchestrator_model: str):
        # Tag guards the "smoke numbers are never reported" rule at the filename
        # level: smoke and main runs can never land in the same file
        assert run_tag in {"smoke", "main"}, f"unexpected run_tag: {run_tag}"
        runs_dir = Path(runs_dir)
        runs_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        self.path = runs_dir / f"{run_tag}_arm{arm}_k{run_idx}_{ts}_{config_hash}.jsonl"
        self._fh = self.path.open("a", buffering=1) # line-buffered: a crash keeps prior episodes
        self._base = {
            "run_tag": run_tag,
            "arm": arm,
            "run_idx": run_idx,
            "config_hash": config_hash,
            "orchestrator_model": orchestrator_model,
        }
        self._closed = False
        self._write({"event": "run_open", "started_at": time.time(), "git_commit": _git_commit()})


    def log_episode(self, **fields) -> None:
        self._write({"event": "episode", **fields})


    def _write(self, record: dict) -> None:
        # default=str so a stray non-JSON type (e.g. a Decimal out of SQLite) degrades
        # to a string instead of killing the run mid-write
        self._fh.write(json.dumps({"ts": time.time(), **self._base, **record}, default=str) + "\n")


    def close(self, **fields) -> None:
        if self._closed:
            return
        self._closed = True
        self._write({"event": "run_close", "ended_at": time.time(), **fields})

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

