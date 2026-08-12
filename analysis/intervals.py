"""Paired bootstrap CIs on the arm contrasts.

Resampling is over tasks because that is the independent unit; the 3 runs are
replicates within a task. The same resampled task list is scored under every
arm in a draw, which is what makes the contrast paired and the interval
narrower than two independent intervals would suggest.

Intervals cover benchmark composition only. The three runs are held fixed, so
run-to-run seed variation is not in these bounds.
"""
import argparse
import json
import random
from collections import defaultdict

N_BOOT = 10_000
SEED = 0
PAIRS = ((1, 2), (2, 3), (1, 3))

ap = argparse.ArgumentParser()
ap.add_argument("traces", nargs="+")
ap.add_argument("--out", help="write point estimates and CIs as JSON")
args = ap.parse_args()

by_arm = defaultdict(lambda: defaultdict(dict))

for path in args.traces:
    recs = [json.loads(l) for l in open(path)]
    header = next(r for r in recs if r.get("event") == "run_open")
    assert header["git_commit"] == "9ca1c7e", path
    for e in (r for r in recs if r.get("event") == "episode"):
        d = by_arm[e["arm"]][e["task_id"]]
        assert e["run_idx"] not in d, (path, e["task_id"])
        d[e["run_idx"]] = bool(e["correct"])

rate = {arm: {t: sum(v.values()) / 3 for t, v in tasks.items()}
        for arm, tasks in by_arm.items()}
solid = {arm: {t: float(sum(v.values()) == 3) for t, v in tasks.items()}
         for arm, tasks in by_arm.items()}
SRC = {"p1": rate, "p3": solid}

ids = sorted(rate[1])
assert all(set(m) == set(ids) for m in rate.values())

rng = random.Random(SEED)
draws = defaultdict(list)

for _ in range(N_BOOT):
    samp = [rng.choice(ids) for _ in ids]
    for arm in rate:
        draws["p1", arm].append(sum(rate[arm][t] for t in samp) / len(samp))
        draws["p3", arm].append(sum(solid[arm][t] for t in samp) / len(samp))
    for a, b in PAIRS:
        for m in ("p1", "p3"):
            draws[m, a, b].append(draws[m, b][-1] - draws[m, a][-1])


def ci(key):
    v = sorted(draws[key])
    return v[int(0.025 * N_BOOT)], v[int(0.975 * N_BOOT)]


def point(m, arm):
    return sum(SRC[m][arm].values()) / len(ids)


def contrast(m, a, b):
    return sum(SRC[m][b][t] - SRC[m][a][t] for t in ids) / len(ids)


for m, label in (("p1", "pass@1"), ("p3", "pass^3")):
    print(label)
    for arm in sorted(rate):
        lo, hi = ci((m, arm))
        print(f"  arm {arm}        {point(m, arm):6.1%}   [{lo:6.1%}, {hi:6.1%}]")
    for a, b in PAIRS:
        lo, hi = ci((m, a, b))
        print(f"  arm {a} -> arm {b}  {contrast(m, a, b):+6.1%}   [{lo:+6.1%}, {hi:+6.1%}]")
    print()

if args.out:
    # n_boot/seed/commit are stamped so a figure regenerated later is provably
    # the same numbers as the one in the draft, not a fresh resample
    payload = {"n_boot": N_BOOT, "seed": SEED, "git_commit": "9ca1c7e",
               "arms": {}, "contrasts": {}}
    for m in ("p1", "p3"):
        for arm in sorted(rate):
            lo, hi = ci((m, arm))
            payload["arms"][f"{m}_arm{arm}"] = {"point": point(m, arm), "lo": lo, "hi": hi}
        for a, b in PAIRS:
            lo, hi = ci((m, a, b))
            payload["contrasts"][f"{m}_arm{a}_arm{b}"] = {
                "point": contrast(m, a, b), "lo": lo, "hi": hi}
    with open(args.out, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"wrote {args.out}")
