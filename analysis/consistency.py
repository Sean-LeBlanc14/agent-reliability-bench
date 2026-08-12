"""Per-task consistency across the three runs of an arm.

pass@1 averages over runs and hides whether the same tasks succeed each time.
pass^3 is the reliability floor, and the 0-of-3 / 1 / 2 / 3 distribution says
whether the gap between them is a few flaky tasks or broad instability.
"""
import json
import sys
from collections import defaultdict

# arm -> task_id -> run_idx -> correct
by_arm = defaultdict(lambda: defaultdict(dict))

for path in sys.argv[1:]:
    recs = [json.loads(l) for l in open(path)]
    header = next(r for r in recs if r.get("event") == "run_open")
    assert header["git_commit"] == "9ca1c7e", path
    for e in (r for r in recs if r.get("event") == "episode"):
        d = by_arm[e["arm"]][e["task_id"]]
        # a duplicate here means a cell was traced twice, not a rerun replacing one
        assert e["run_idx"] not in d, (path, e["task_id"])
        d[e["run_idx"]] = bool(e["correct"])

ids = None
for arm in sorted(by_arm):
    tasks = by_arm[arm]
    assert len(tasks) == 150, (arm, len(tasks))
    assert all(len(v) == 3 for v in tasks.values()), arm
    # paired comparison is only valid if every arm saw the same benchmark
    assert ids is None or set(tasks) == ids, arm
    ids = set(tasks)

    hist = [0, 0, 0, 0]
    for v in tasks.values():
        hist[sum(v.values())] += 1

    mean = sum(sum(v.values()) for v in tasks.values()) / 450
    print(f"arm {arm}  mean pass@1 {mean:6.1%}   pass^3 {hist[3]:3d}/150 = {hist[3] / 150:5.1%}")
    print(f"  never  {hist[0]:3d}   1of3 {hist[1]:3d}   2of3 {hist[2]:3d}   always {hist[3]:3d}"
          f"   unstable {hist[1] + hist[2]:3d}\n")

unstable = {arm: {t for t, v in tasks.items() if 0 < sum(v.values()) < 3}
            for arm, tasks in by_arm.items()}

print("unstable-set overlap")
for a in sorted(unstable):
    for b in sorted(unstable):
        if a < b:
            i = unstable[a] & unstable[b]
            u = unstable[a] | unstable[b]
            print(f"  arm {a} vs arm {b}: {len(i):3d} shared of {len(u):3d} union"
                  f"   jaccard {len(i) / len(u):5.1%}")
print(f"  unstable in all three: {len(set.intersection(*unstable.values()))}")
print(f"  unstable in any arm  : {len(set.union(*unstable.values()))}\n")


BANDS = ("never", "unstable", "always")


def band(v):
    s = sum(v.values())
    return BANDS[0] if s == 0 else BANDS[2] if s == 3 else BANDS[1]


def shift(a, b):
    m = defaultdict(int)
    for t in by_arm[a]:
        m[band(by_arm[a][t]), band(by_arm[b][t])] += 1
    print(f"arm {a} -> arm {b}")
    for o in BANDS:
        row = {d: m[o, d] for d in BANDS}
        cells = "  ".join(f"{d}: {row[d]:3d}" for d in BANDS)
        print(f"  {o:9s} n={sum(row.values()):3d}   {cells}")
    print()


for a, b in ((1, 2), (1, 3), (2, 3)):
    shift(a, b)
