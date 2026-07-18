"""
Classify Spider dev examples by official hardness (taoyds/spider evaluation.py)
"""

import json
import sys
import sqlite3 
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "vendor" / "spider_eval"))
from process_sql import get_schema, Schema, get_sql
from evaluation import Evaluator

sys.path.insert(0, str(Path(__file__).parent.parent))
from paths import DB_DIR, DEV_FILE

OUT_FILE = Path(__file__).parent.parent / "analysis" / "dev_with_difficulty.jsonl"


def main():
    examples = [json.loads(l) for l in open(DEV_FILE)]
    evaluator = Evaluator()
    schemas = {}
    failures = []

    for i, ex in enumerate(examples):
        db_id = ex["db_id"]
        if db_id not in schemas:
            db_path = str(DB_DIR / db_id / f"{db_id}.sqlite")
            schemas[db_id] = Schema(get_schema(db_path))
        try:
            parsed = get_sql(schemas[db_id], ex["query"])
            ex["difficulty"] = evaluator.eval_hardness(parsed)
        except Exception as e:
            ex["difficulty"] = None
            failures.append((i, ex["query"], repr(e)))

        db_path = DB_DIR / db_id / f"{db_id}.sqlite"
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        con.text_factory = lambda b: b.decode(errors="replace")
        try:
            ex["gold_row_count"] = len(con.execute(ex["query"]).fetchall())
        except Exception as e:
            ex["gold_row_count"] = None
            failures.append((i, ex["query"], f"EXEC: {e!r}"))
        finally:
            con.close()

    OUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUT_FILE, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    dist = Counter(ex["difficulty"] for ex in examples)
    print("distribution:", dict(dist))
    print(f"parse failures: {len(failures)}")
    for i, q, err in failures[:5]:
        print(f"  [{i}] {q[:80]} -> {err}")
    over = sum(1 for ex in examples if (ex["gold_row_count"] or 0) > 20)
    exec_fail = sum(1 for ex in examples if ex["gold_row_count"] is None)
    print(f"gold exec failures: {exec_fail}")
    print(f"pool tasks with >20 gold rows: {over} / {len(examples)}")

if __name__ == "__main__":
    main()
