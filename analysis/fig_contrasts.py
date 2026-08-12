"""Figure 1: the arm contrasts against their pre-registered thresholds.

Reads intervals.json rather than recomputing, so the figure and the text
cannot disagree and no bootstrap runs at plot time.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt

FIG = Path("figures")
FIG.mkdir(exist_ok=True)

d = json.load(open("analysis/intervals.json"))
assert d["git_commit"] == "9ca1c7e"

ROWS = [
    ("arm1_arm2", "arm 1 \u2192 arm 2\n(not registered)", None),
    ("arm1_arm3", "arm 1 \u2192 arm 3\n(H1a)", 0.10),
    ("arm2_arm3", "arm 2 \u2192 arm 3\n(H1b)", 0.05),
]

fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)

for ax, (m, title) in zip(axes, (("p1", "pass@1"), ("p3", "pass^3"))):
    for y, (key, _, thr) in enumerate(ROWS):
        c = d["contrasts"][f"{m}_{key}"]
        ax.errorbar(c["point"], y,
                    xerr=[[c["point"] - c["lo"]], [c["hi"] - c["point"]]],
                    fmt="o", color="black", capsize=4)
        if thr is not None:
            # thresholds are per-hypothesis, so each is drawn on its own row
            ax.plot(thr, y, marker="|", markersize=18, color="crimson")
    ax.axvline(0, color="0.6", lw=0.8, zorder=0)
    ax.set_title(title)
    ax.set_xlabel("difference in success rate")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:+.0%}")

axes[0].set_yticks(range(len(ROWS)), [r[1] for r in ROWS])
axes[0].set_ylim(-0.5, len(ROWS) - 0.5)
fig.tight_layout()
fig.savefig(FIG / f"fig1_contrasts.png", bbox_inches="tight", dpi=200)
