"""
Schema Extraction and Prompt Construction.

Shared so both run_baseline and later the fine-tuned-model eval, so both use
identical prompting. Otherwise the accuracy comparision measures the prompt
change, not the training.
"""

from __future__ import annotations

import os
import json
import random
from typing import Callable, List, Tuple

RunQuery = Callable[[str, str], tuple]

SYSTEM = (
    "You are an expert data analyst who writes SQLite SQL."
    "Given a database schema and a question, reply with a single SQL query that "
    "answers it. Output only the SQL: no explanation, no markdown, no comments."
)

_SCHEMA_CACHE: dict[str, str] = {}


def load_split(path: str) -> List[dict]:
    """Load a Spider split as a list of {question, query, db_id} dicts."""

    if os.path.isdir(path):
        from datasets import load_from_disk
        ds = load_from_disk(path)
        return [dict(r) for r in ds]
    with open(path) as f:
        text = f.read()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]


def get_schema_ddl(run_query: RunQuery, db_id: str) -> str:
    """Return the CREATE TABLE statements for a database using run_query"""

    if db_id in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[db_id]
    rows, err = run_query(
        db_id,
        "SELECT sql FROM sqlite_master "
        "WHERE type='table' AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%'",
    )
    if err is not None:
        raise RuntimeError(f"schema fetch failed for {db_id}: {err}")
    ddl = "\n\n".join(r[0].strip() for r in rows if r and r[0])
    _SCHEMA_CACHE[db_id] = ddl
    return ddl


def _user_turn(schema: str, question: str) -> str:
    return f"Schema:\n{schema}\n\nQuestion: {question}\nSQL:"


def build_messages(
    run_query: RunQuery,
    db_id: str,
    question: str,
    few_shots: List[Tuple[str, str, str]],
) -> List[dict]:
    """
    Build the chat message list: system + few-shot turns + target question.

    few_shots: list of (schema_ddl, question, sql) triples.
    """

    messages = [{"role": "system", "content": SYSTEM}]
    for sc, q, sql in few_shots:
        messages.append({"role": "user", "content": _user_turn(sc, q)})
        messages.append({"role": "assistant", "content": sql.strip()})
    schema = get_schema_ddl(run_query, db_id)
    messages.append({"role": "user", "content": _user_turn(schema, question)})
    return messages


def build_prompt_completion(
    run_query: RunQuery,
    db_id: str,
    question: str,
    gold_sql: str,
) -> Tuple[List[dict], List[dict]]:
    """
    Training pair for SFT. The prompt is the zero-shot eval prompt, so the model
    trains on what it was evaluated on. Returns (prompt_messages, completion_messages)
    """
    
    prompt = build_messages(run_query, db_id, question, few_shots=[])
    completion = [{"role": "assistant", "content": gold_sql.strip()}]
    return prompt, completion


def select_few_shots(
    run_query: RunQuery,
    train_data: List[dict],
    n: int = 3,
    seed: int = 0,
    cache_path: str = "fewshots.json",
    min_query_len: int = 30,
    max_query_len: int = 130,
    max_schema_chars: int = 1200,
) -> List[Tuple[str, str, str]]:
    """
    Pick a fixed, reproducible set of few_shot_examples from train.

    Criteria: distinct db's, compact schemas, non-trivial but short gold SQL.
    Cached to `cache_path` so baseline and fine_tune runs reuse the same shots.
    """

    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return [tuple(x) for x in json.load(f)]

    rng = random.Random(seed)
    pool = [d for d in train_data if min_query_len <= len(d["query"]) <= max_query_len]
    rng.shuffle(pool)

    chosen: List[Tuple[str, str, str]] = []
    seen_db: set[str] = set()
    for d in pool:
        if d["db_id"] in seen_db:
            continue
        try:
            sc = get_schema_ddl(run_query, d["db_id"])
        except RuntimeError:
            continue
        if len(sc) > max_schema_chars:
            continue
        chosen.append((sc, d["question"], d["query"]))
        seen_db.add(d["db_id"])
        if len(chosen) == n:
            break

    if len(chosen) < n:
        raise RuntimeError(
            f"only found {len(chosen)} few-shot examples; loosen the length/schema "
            "filters in select_few_shots()"
        )

    with open(cache_path, "w") as f:
        json.dump([list(c) for c in chosen], f, indent=2)
    return chosen

