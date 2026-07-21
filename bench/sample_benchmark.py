"""
Proportional stratified sample of Spider dev -> benchmark question set.
"""

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO_ROOT = Path(__file__).parent.parent
IN_FILE = REPO_ROOT / "analysis" / "dev_with_difficulty.jsonl"
OUT_FILE = REPO_ROOT / "bench" / "benchmark_questions.jsonl"

N_TOTAL = 150
SEED = 42
DIFFICULTIES = ["easy", "medium", "hard", "extra"]
MAX_GOLD_ROWS = 20


def main():
    examples = [json.loads(l) for l in open(IN_FILE)]
    pool_size = len(examples)
    n_empty = sum(1 for ex in examples if ex["gold_row_count"] == 0)
    examples = [
        ex for ex in examples
        if ex["gold_row_count"] is not None and 0 < ex["gold_row_count"] <= MAX_GOLD_ROWS
    ]

    by_diff = defaultdict(list)
    for ex in examples:
        by_diff[ex["difficulty"]].append(ex)

    total = len(examples)
    print(f"eligible pool: {total} / {pool_size}")
    print(f"excluded for empty gold (0 rows): {n_empty} / {pool_size}")

    quotas = {d: N_TOTAL * len(by_diff[d]) / total for d in DIFFICULTIES}
    alloc = {d: int(quotas[d]) for d in DIFFICULTIES}
    remainder = N_TOTAL - sum(alloc.values())
    for d in sorted(DIFFICULTIES, key=lambda d: quotas[d] - alloc[d], reverse=True)[:remainder]:
        alloc[d] += 1

    rng = random.Random(SEED)
    sample = []
    for d in DIFFICULTIES:
        sample.extend(rng.sample(by_diff[d], alloc[d]))

    # stable order: by difficulty, then db_id, then question
    order = {d: i for i, d in enumerate(DIFFICULTIES)}
    sample.sort(key=lambda ex: (order[ex["difficulty"]], ex["db_id"], ex["question"]))

    with open(OUT_FILE, "w") as f:
        for i, ex in enumerate(sample):
            row = {
                "task_id": f"t{i:03d}",
                "question": ex["question"],
                "db_id": ex["db_id"],
                "gold_sql": ex["query"],
                "difficulty": ex["difficulty"],
            }
            f.write(json.dumps(row) + "\n")

    print("allocation:", alloc, "total:", sum(alloc.values()))
    print(f"wrote {len(sample)} -> {OUT_FILE}")


if __name__ == "__main__":
    main()

