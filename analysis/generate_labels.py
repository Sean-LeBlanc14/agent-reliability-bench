"""
Assign failure labels mechanically from the frozen manifest.

Hand labeling was dropped after the unsupported-values check came back empty on
every candidate episode: no ANSWER contains a value absent from the rows the tool
returned, so hallucinated_answer has no instances and wrong_query is forced.
This script reasserts that check per episode rather than trusting the prior run,
so a trace or rule change surfaces as a failure here instead of silently.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from analysis.failure_breakdown import unsupported
from paths import REPO_ROOT

SKIP_BUCKETS = {"interpretation_failure"}


def load_episodes(name, cache):
    if name not in cache:
        recs = [json.loads(l) for l in open(REPO_ROOT / "runs" / name)]
        cache[name] = [r for r in recs if r.get("event") == "episode"]
    return cache[name]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="analysis/worklist_k0.jsonl")
    ap.add_argument("--labels", default="analysis/failure_labels.jsonl")
    args = ap.parse_args()

    items = [json.loads(l) for l in open(REPO_ROOT / args.manifest)]
    cache = {}
    out = []
    for item in items:
        if item["bucket"] in SKIP_BUCKETS:
            continue
        ep = load_episodes(item["trace"], cache)[item["episode_idx"]]
        assert (ep["arm"], ep["run_idx"], ep["task_id"]) == (
            item["arm"], item["run_idx"], item["task_id"]), item
        miss = unsupported(ep)
        if miss:
            raise SystemExit(
                f"unsupported values in {item['arm']}/{item['task_id']}: {miss}\n"
                "hallucinated_answer has instances; labels are no longer mechanical."
            )
        out.append({
            "arm": item["arm"],
            "run_idx": item["run_idx"],
            "task_id": item["task_id"],
            "label": "wrong_query",
            "uncertain": False,
            "notes": "",
        })

    with open(REPO_ROOT / args.labels, "w") as f:
        for rec in out:
            f.write(json.dumps(rec) + "\n")
    print(f"wrote {len(out)} labels to {args.labels}")


if __name__ == "__main__":
    main()
