"""
Execute gold SQL -> bench.jsonl with gold rows and order_matters flags.
"""

import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
from paths import DB_DIR

IN_FILE = REPO_ROOT / "bench" / "benchmark_questions.jsonl"
OUT_FILE = REPO_ROOT / "bench" / "bench.jsonl"


def order_matters(sql: str) -> bool:
    """True if top-level ORDER BY exists (outside any parentheses)."""

    s = sql.lower()
    depth = 0
    i = 0
    while i < len(s):
        c = s[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif depth == 0 and s[i:i+8] == "order by":
            return True
        i += 1
    return False


def main():
    tasks = [json.loads(l) for l in open(IN_FILE)]
    max_rows = 0
    max_rows_task = None

    with open(OUT_FILE, "w") as f:
        for t in tasks:
            db_path = DB_DIR / t["db_id"] / f"{t['db_id']}.sqlite"
            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            con.text_factory = lambda b: b.decode(errors="replace")
            try:
                rows = con.execute(t["gold_sql"]).fetchall()
            except Exception as e:
                sys.exit(f"GOLD SQL FAILED on {t['task_id']} ({t['db_id']}): {e}\n{t['gold_sql']}")
            finally:
                con.close()

            t["gold_rows"] = [list(r) for r in rows]
            assert len(t["gold_rows"]) <= 20, \
                f"{t['task_id']}: {len(t['gold_rows'])} gold rows - sampler let an ineligible task through"
            t["order_matters"] = order_matters(t["gold_sql"])
            if len(rows) > max_rows:
                max_rows, max_rows_task = len(rows), t["task_id"]
            f.write(json.dumps(t) + "\n")

    om = sum(1 for _ in open(OUT_FILE) if json.loads(_)["order_matters"])
    empty = sum(1 for _ in open(OUT_FILE) if json.loads(_)["gold_rows"] == [])
    print(f"wrote {len(tasks)} tasks -> {OUT_FILE}")
    print(f"order_matters: {om}, empty gold results: {empty}")
    print(f"max gold rows: {max_rows} ({max_rows_task})")

if __name__ == "__main__":
    main()
