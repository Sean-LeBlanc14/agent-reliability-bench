"""Labeler for the failure taxonomy"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from paths import REPO_ROOT

LABELS = {"w": "wrong_query", "h": "hallucinated_answer"}
SKIP_BUCKETS = {"interpretation_failure", "no_runnable_sql"}
MAX_ROWS = 5


def load_bench():
    path = REPO_ROOT / "bench" / "bench.jsonl"
    return {json.loads(l)["task_id"]: json.loads(l) for l in open(path)}


def load_trace(name, cache):
    if name not in cache:
        recs = [json.loads(l) for l in open(REPO_ROOT / "runs" / name)]
        cache[name] = [r for r in recs if r.get("event") == "episode"]
    return cache[name]


def key(d):
    return (d["arm"], d["run_idx"], d["task_id"])


def fmt_rows(rows):
    if rows is None:
        return "    None"
    if not rows:
        return "    (empty)"
    out = "\n".join("    " + json.dumps(r) for r in rows[:MAX_ROWS])
    if len(rows) > MAX_ROWS:
        out += f"\n    ... {len(rows) - MAX_ROWS} more"
    return out


def flatten(x):
    if isinstance(x, (list, tuple)):
        return [v for i in x for v in flatten(i)]
    return [x]


def unsupported(ep):
    """Scalars in the ANSWER that appear nowhere in the returned rows.

    Truncated display makes this uncheckable by eye, so compute it over all rows.
    """
    raw = ep["answer_raw"].split("ANSWER:", 1)[-1].strip()
    try:
        vals = flatten(json.loads(raw))
    except json.JSONDecodeError:
        return None
    have = {str(v) for v in flatten(ep["attempts"][-1].get("rows") or [])}
    return [v for v in vals if v is not None and str(v) not in have]


def show(item, ep, task):
    print("=" * 70)
    print(f"arm{item['arm']}/k{item['run_idx']}/{item['task_id']}  "
          f"bucket={item['bucket']}  difficulty={ep['difficulty']}  "
          f"terminal={ep['terminal_reason']}  attempts={len(ep['attempts'])}")
    print("=" * 70)
    print(f"\nQ: {task['question']}")
    print(f"\ngold SQL: {task['gold_sql']}")
    print(f"gold rows ({len(task['gold_rows'])}):")
    print(fmt_rows(task["gold_rows"]))
    for a in ep["attempts"]:
        print(f"\n--- attempt {a['attempt_idx']}  trigger={a.get('trigger')} ---")
        print(f"  sql: {a['sql']}")
        if not a["exec_ok"]:
            print(f"  ERROR: {a.get('exec_error')}")
        else:
            print(f"  rows ({a.get('row_count')}):")
            print(fmt_rows(a.get("rows")))
    print(f"\nANSWER: {ep['answer_raw']!r}")
    miss = unsupported(ep)
    print(f"unsupported values: {'unparseable' if miss is None else miss}")
    print(f"parse={ep['parse_status']}  grade={ep['grade_status']}")


def prompt(item):
    while True:
        raw = input("\n[w]rong_query [h]allucinated "
                    "(add 'u' uncertain, 'n' note) [s]kip [q]uit > ").strip().lower()
        if raw == "q":
            return None
        if raw == "s":
            return "skip"
        parts = raw.split()
        if not parts or parts[0] not in LABELS:
            print("  unrecognized")
            continue
        note = input("  note > ").strip() if "n" in parts[1:] else ""
        return {
            "arm": item["arm"],
            "run_idx": item["run_idx"],
            "task_id": item["task_id"],
            "label": LABELS[parts[0]],
            "uncertain": "u" in parts[1:],
            "notes": note,
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="analysis/worklist_k0.jsonl")
    ap.add_argument("--labels", default="analysis/failure_labels.jsonl")
    ap.add_argument("--bucket", help="only label episodes in this bucket")
    args = ap.parse_args()

    labels_path = REPO_ROOT / args.labels
    items = [json.loads(l) for l in open(REPO_ROOT / args.manifest)]
    items = [i for i in items if i["bucket"] not in SKIP_BUCKETS]
    if args.bucket:
        items = [i for i in items if i["bucket"] == args.bucket]

    done = set()
    if labels_path.exists():
        done = {key(json.loads(l)) for l in open(labels_path)}
    todo = [i for i in items if key(i) not in done]
    print(f"{len(done)} labeled, {len(todo)} remaining")

    bench = load_bench()
    cache = {}
    with open(labels_path, "a") as out:
        for n, item in enumerate(todo, 1):
            ep = load_trace(item["trace"], cache)[item["episode_idx"]]
            # a mismatch here means the join key is meaningless, so fail loud
            assert (ep["arm"], ep["run_idx"], ep["task_id"]) == key(item), item
            print(f"\n\n[{n}/{len(todo)}]")
            show(item, ep, bench[item["task_id"]])
            rec = prompt(item)
            if rec is None:
                break
            if rec == "skip":
                continue
            out.write(json.dumps(rec) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
