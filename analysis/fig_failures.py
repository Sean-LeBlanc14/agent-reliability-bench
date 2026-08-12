"""Figure 2: what the failure budget is made of, per cell.

Reads cell_metrics.jsonl. Nine bars rather than three arm means, because the
run-to-run spread (arm 1 k=1 especially) is real and the CIs deliberately do
not cover it — averaging it away here would hide it everywhere.
"""
import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

FIG = Path("figures")
FIG.mkdir(exist_ok=True)

SEGMENTS = [
    ("no_runnable_sql", "no runnable SQL"),
    ("exhausted_empty", "exhausted, empty"),
    ("tool_wrong", "wrong SQL"),
    ("interpretation_failure", "interpretation"),
]

rows = [json.loads(l) for l in open("analysis/cell_metrics.jsonl")]
assert len(rows) == 9, len(rows)
rows.sort(key=lambda r: (r["arm"], r["run_idx"]))

for r in rows:
    assert r["git_commit"] == "9ca1c7e"
    # the classify() buckets partition the episodes; if this breaks, a bucket
    # was added or renamed and the stack is no longer exhaustive
    assert sum(r[k] for k, _ in SEGMENTS) == r["total"] - r["correct"], r

fig, ax = plt.subplots(figsize=(7.5, 3.6))
x = range(9)
bottom = [0] * 9

for key, label in SEGMENTS:
    vals = [r[key] for r in rows]
    ax.bar(x, vals, bottom=bottom, label=label, width=0.7)
    bottom = [b + v for b, v in zip(bottom, vals)]

ax.set_xticks(x, [f"arm {r['arm']}\nk={r['run_idx']}" for r in rows])
ax.set_ylabel("failing episodes (of 150)")
ax.legend(frameon=False, fontsize=8, ncol=4,
          loc="lower left", bbox_to_anchor=(0, 1.0))
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)

fig.tight_layout()
fig.savefig(FIG / f"fig2_failures.png", bbox_inches="tight", dpi=200)
