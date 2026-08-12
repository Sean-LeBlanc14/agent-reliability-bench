"""Attempt-to-attempt state transitions for the repair loop.

State is the attempt's own outcome, which is exactly what `trigger` records:
an exec failure, an empty result, or non-empty rows (no trigger, episode
ends). Row-normalized, so each row answers "the loop fired on X, what came
back". Pools every trace passed in, so per-cell reads mean running it on one.
"""
import json
import sys
from collections import defaultdict

STATES = ("exec_error", "empty_result", "ok_rows")


def state(a):
    return a.get("trigger") or "ok_rows"


counts = defaultdict(int)
reps = defaultdict(int)

for path in sys.argv[1:]:
    recs = [json.loads(l) for l in open(path)]
    header = next(r for r in recs if r.get("event") == "run_open")
    assert header["git_commit"] == "9ca1c7e", path
    for e in (r for r in recs if r.get("event") == "episode"):
        a = e["attempts"]
        for i in range(len(a) - 1):
            o, d = state(a[i]), state(a[i + 1])
            # non-empty rows terminate the episode, so it can never be an origin
            assert o != "ok_rows", (path, e["task_id"], i)
            counts[e["arm"], o, d] += 1
            if a[i]["sql"] == a[i + 1]["sql"]:
                # same query, same read-only DB, so a repeat must land on the diagonal
                assert o == d, (path, e["task_id"], i)
                reps[e["arm"], o] += 1

for arm in sorted({k[0] for k in counts}):
    print(f"arm {arm}")
    for o in STATES[:2]:
        row = {d: counts[arm, o, d] for d in STATES}
        n = sum(row.values())
        if not n:
            continue
        cells = "  ".join(f"{d}: {row[d]:3d} ({row[d] / n:5.1%})" for d in STATES)
        print(f"  from {o:13s} n={n:3d}  {cells}   repeats {reps[arm, o]}")
    print()
