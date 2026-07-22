# Agent Reliability Bench

A controlled study of how scaffold choice affects agent reliability,
using text2sql as the testbed. The eval harness is the product;
the agent is the test subject.

Tool model: Qwen2.5-Coder-1.5B + QLoRA adapter
(see [text2sql](https://github.com/Sean-LeBlanc14/text2sql))

## Preregistered Hypotheses (written 2026-07-15, before implementation)

- **H1a (total scaffold effect):** Agent + repair (arm 3) lifts task
  success by ≥10 points over single-shot (arm 1).
- **H1b (error-feedback effect):** Agent + repair (arm 3) lifts task
  success by ≥5 points over the resample-only agent (arm 2) at equal
  retry budget — i.e., error feedback contributes beyond bare resampling.
- **H2 (stability cost):** pass^3 (all 3 of 3 runs correct) improves
  less than pass@1 across the ladder — repair raises average success
  but is unstable run-to-run.

*Amended 2026-07-19, before any agent data was collected: H1b restated as the
error-feedback effect at equal retry budget, matching the pinned arm-2 (resample-only) semantics.*

## Design

### Architecture

Two models, held constant across all three arms:

- **Orchestrator** — a frontier API model (cheap capable tier, temp 0), the fixed apparatus.
  Model string pinned and recorded in every trace.
- **Tool** — the Qwen2.5-Coder-1.5B + QLoRA adapter, behind `generate_sql()`. One job:
  question (+ optional error/prev SQL) in, SQL out.

**No-SQL-authorship constraint:** the orchestrator never writes SQL. Enforced structurally — every
tool output carries an ID, and the executor only runs SQL bearing a valid tool-output ID. Trace tests
assert the invariant.

**Tool-input contract:** inputs limited to `(question)` on the first attempt, or
`(question + executor error + previous SQL)` on repair. No free-text rephrasing — closes the
SQL-laundering-via-input leak.

Three-arm comparison, same orchestrator + tool, same benchmark:

1. **Single-shot** — one `generate_sql` call → execute → extraction → `ANSWER`. No loop.
2. **Agent, no repair (resample-on-failure)** — on a repair trigger, re-query with the
   **original question only** (fresh tool resample at temp > 0). Step-capped. Isolates the pure
   inference-compute effect of retrying.
3. **Agent + repair (resample-with-error-feedback)** — **same step cap as arm 2**, but the re-query
   carries question + executor error + previous SQL. Isolates the value of information beyond compute.

Arms 2 and 3 share an identical step cap, so H1b never confounds feedback with extra attempts.
**Repair triggers (exactly two, both `if` statements):** (1) SQL execution error, (2) empty result set.

Grading: each arm emits `ANSWER: <value(s)>` through a **shared answer-extraction prompt** (one module,
imported by every arm, so extraction is held constant and the ladder isolates loop effects), parsed and
graded by normalized exact-match against executed gold rows. Row order is enforced only when the gold
query orders its result; otherwise comparison is multiset (duplicate-sensitive). Column permutations are
accepted, numerics are coerced and rounded, and unparseable answers are their own failure status. No LLM
judge. The comparison core is inherited from the Project 1 scorer, where it was validated by unit tests
and produced the published execution-accuracy numbers; the grader here adds the answer-parsing layer
(46 tests total). **Secondary diagnostic (logged, not primary):** row-level match of the final executed
SQL against gold; divergence between the primary (ANSWER) result and this is the **interpretation-failure
rate** — a wrong answer off a right query, observable in every arm.

## Benchmark

150 questions sampled from Spider dev (1,034 examples), proportionally
stratified by the official Spider hardness classifier (easy/medium/hard/extra,
via vendored [taoyds/spider](https://github.com/taoyds/spider) evaluation
code). Sampling is deterministic (seed 42) and fully regenerable:
classify -> filter -> sample -> execute gold SQL.

**Eligibility rules (applied before sampling, before any arm ran):** tasks
whose gold result exceeds 20 rows are excluded (70/1,034, 6.8% of the pool).
The answer-emission grading format requires the agent to output the complete
result set; beyond ~20 rows the task measures output-length stamina rather
than reliability. The threshold was fixed from the pool's row-count
distribution (p95 = 28, then a cliff to 753+) prior to measuring any arm.

Empty gold results (0 rows) are excluded at the same pre-sampling filter, since the
empty-result repair trigger would otherwise fire on a correct query that legitimately
returns nothing and penalize it. 49/1,034 excluded from the pool. This rule was added
2026-07-19, before any agent data was collected; the deterministic seed-42 sample was
regenerated so that both gold-shape eligibility rules apply before the draw.

Each task stores the question, db_id, gold SQL, executed gold rows, official
difficulty, and an `order_matters` flag (true iff the gold query has a
top-level `ORDER BY` — subquery ORDER BY does not constrain outer row order).
Spider dev obtained via HuggingFace export; train/dev disjointness verified
during Project 1's contamination audit.

## Results

*(pending)*

## Reproduce

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...          # orchestrator calls

python bench/classify_difficulty.py   # Spider dev -> difficulty labels
python bench/sample_benchmark.py      # eligibility filter + stratified sample (seed 42)
python bench/build_bench.py           # execute gold -> bench.jsonl
python bench/test_grader.py           # 46 tests, no data or model needed

python run_smoke.py                   # arm 1, k=1, pipeline validation
python analysis/failure_breakdown.py  # pass@1 + ANSWER-vs-rows decomposition
```

Traces land in `runs/` (gitignored); per-run reports in `analysis/reports/`.
