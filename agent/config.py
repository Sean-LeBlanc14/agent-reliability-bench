"""
Frozen run configuration: one source so changes cant desync modules, and one hash so runs
can be traced back to the exact config that produced it.
"""

import hashlib
import json

CONFIG = {
    "tool": {
        "temperature": 0.7,   # >0 is the point: k=3 needs tool variance to measure H2
        "top_p": 0.95,
        "max_new_tokens": 256,
    },
    "orchestrator": {
        "model": "claude-haiku-4-5-20251001",
        "temperature": 0.0,   # not the subject of project: keep as close to deterministic as possible
    },
    "executor": {
        "timeout_s": 30,
        "max_result_rows": 100,   # caps only what's shown to the model, grading will see full rows
    },
    "seed": {
        "base": 1234,
    },
}


def _canonical(obj) -> str:
    # Hash values, not source text, so reformatting doesn't move
    # the hash. Only real parameter changes will
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


CONFIG_HASH = hashlib.sha256(_canonical(CONFIG).encode()).hexdigest()[:12]


def derive_seed(task_id: str, run_idx: int, attempt_idx: int) -> int:
    """
    The same attempt on the same (task, k-run) draws the same tool seed
    across all three arms, so arm differences trace to the scaffold and
    inputs. Excluding arm from the key keeps H1b a clean one-var comparison
    """

    h = hashlib.sha256(f"{task_id}:{run_idx}:{attempt_idx}".encode()).hexdigest()
    return (CONFIG["seed"]["base"] + int(h[:8], 16)) % (2**31 - 1)


if __name__ == "__main__":
    print(f"config_hash: {CONFIG_HASH}")
    print(_canonical(CONFIG))
