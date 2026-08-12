"""Which trigger precedes a verbatim repeat. Post-hoc, exploratory tier.

The repair prompt labels both triggers "Error:", but only exec_error carries a
real message; empty_result is a canned sentence with nothing to act on. If
repeats concentrate there, the copying is a response to contentless feedback
rather than to feedback as such.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

for path in sys.argv[1:]:
    recs = [json.loads(l) for l in open(path)]
    header = next(r for r in recs if r.get("event") == "run_open")
    assert header["git_commit"] == "9ca1c7e", path
    eps = [r for r in recs if r.get("event") == "episode"]

    pairs, rep = defaultdict(int), defaultdict(int)
    for e in eps:
        a = e["attempts"]
        for i in range(len(a) - 1):
            t = a[i]["trigger"]
            pairs[t] += 1
            rep[t] += a[i]["sql"] == a[i + 1]["sql"]

    print(f"arm {eps[0]['arm']} k{eps[0]['run_idx']}")
    for t in sorted(pairs):
        print(f"  {t:14s} {rep[t]:3d}/{pairs[t]:3d} = {rep[t] / pairs[t]:5.1%}")
