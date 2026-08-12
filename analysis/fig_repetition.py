"""Figure 3: verbatim repetition rate, the pre-registered check.

Arm 1 is absent rather than plotted at zero. Single-shot has no consecutive
attempt pairs, so the metric is undefined for it, and a zero bar would read as
"never repeats". Denominators vary by cell, so each bar is annotated with its n.
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt

FIG = Path("figures")
FIG.mkdir(exist_ok=True)

rows = [json.loads(l) for l in open("analysis/cell_metrics.jsonl")]
assert len(rows) == 9, len(rows)
for r in rows:
    assert r["git_commit"] == "9ca1c7e"

cells = {(r["arm"], r["run_idx"]): r for r in rows if r["arm"] in (2, 3)}
assert all(c["attempt_pairs"] for c in cells.values())

fig, ax = plt.subplots(figsize=(6.5, 3.4))
width = 0.36

for i, arm in enumerate((2, 3)):
    xs = [k + (i - 0.5) * width for k in range(3)]
    vals = [cells[arm, k]["verbatim_repeats"] / cells[arm, k]["attempt_pairs"]
            for k in range(3)]
    ax.bar(xs, vals, width=width, label=f"arm {arm}")
    for x, k in zip(xs, range(3)):
        c = cells[arm, k]
        ax.annotate(f"{c['verbatim_repeats']}/{c['attempt_pairs']}",
                    (x, c["verbatim_repeats"] / c["attempt_pairs"]),
                    textcoords="offset points", xytext=(0, 3),
                    ha="center", fontsize=7)

ax.set_xticks(range(3), [f"k={k}" for k in range(3)])
ax.set_ylabel("consecutive attempt pairs with identical SQL")
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
ax.legend(frameon=False, fontsize=8, ncol=2, loc="lower left", bbox_to_anchor=(0, 1.0))
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)

fig.tight_layout()
fig.savefig(FIG / "fig3_repetition.png", bbox_inches="tight", dpi=200)
