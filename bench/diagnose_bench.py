"""
Per-task gold execution timing + row-count distribution for bench.jsonl.
"""

import json
import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
from paths import DB_DIR

BENCH = REPO_ROOT / "bench" / "bench.jsonl"


def main():
    tasks = [json.loads(l) for l in open(BENCH)]
    stats = []
    for t in tasks:
        db_path = DB_DIR / t["db_id"] / f"{t['db_id']}.sqlite"
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        con.text_factory = lambda b: b.decode(errors="replace")
        t0 = time.perf_counter()
        rows = con.execute(t["gold_sql"]).fetchall()
        dt = time.perf_counter() - t0
        con.close()
        stats.append((dt, len(rows), t["task_id"], t["db_id"], t["difficulty"]))

    stats.sort(reverse=True)
    print("slowest 10:")
    for dt, n, tid, db, diff in stats[:10]:
        print(f"  {tid} {db:24s} {diff:6s} {dt:8.2f}s  {n} rows")

    counts = sorted(n for _, n, *_ in stats)
    print(f"\nrow counts: max={counts[-1]}  p95={counts[int(0.95*len(counts))]}  "
          f"p90={counts[int(0.90*len(counts))]}  median={counts[len(counts)//2]}")
    for thresh in (10, 20, 50, 100):
        over = sum(1 for c in counts if c > thresh)
        print(f"  tasks with >{thresh} rows: {over}")
    slow = sum(1 for dt, *_ in stats if dt > 5)
    print(f"tasks slower than 5s: {slow}")


if __name__ == "__main__":
    main()

