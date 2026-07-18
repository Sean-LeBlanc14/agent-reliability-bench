# Agent Reliability Bench

A controlled study of how scaffold choice affects agent reliability,
using text2sql as the testbed. The eval harness is the product;
the agent is the test subject.

Model: Qwen2.5-Coder-1.5B + QLoRA adapter
(see [text2sql](https://github.com/Sean-LeBlanc14/text2sql))

## Preregistered Hypotheses (written 2026-07-15, before implementation)

- **H1a (total scaffold effect):** Agent + repair (arm 3) lifts task
  success by ≥10 points over single-shot (arm 1).
- **H1b (repair-specific effect):** Agent + repair (arm 3) lifts task
  success by ≥5 points over the no-repair agent (arm 2) — i.e., repair
  contributes meaningfully beyond agenthood alone.
- **H2 (stability cost):** pass^3 (all 3 of 3 runs correct) improves
  less than pass@1 across the ladder — repair raises average success
  but is unstable run-to-run.

## Design

Three-arm comparison, same model, same benchmark:

1. **Single-shot** - one query, no retries
2. **Agent, no repair** - observe -> generate -> execute -> answer, step-capped
3. **Agent + repair** - arm 2 plus error-feedback re-generation

Grading: the agent must end its output with `ANSWER: <value(s)>`, parsed and
graded by normalized exact-match against executed gold rows. Row order is
enforced only when the gold query orders its result; otherwise comparison is
multiset (duplicate-sensitive). Column permutations are accepted, numerics
are coerced and rounded, and unparseable answers are their own failure
status. No LLM judge. The comparison core is inherited from the Project 1
scorer, where it was validated by unit tests and produced the published
execution-accuracy numbers; the grader here adds the answer-parsing layer
(44 tests total).

## Benchmark

150 questions sampled from Spider dev (1,034 examples), proportionally
stratified by the official Spider hardness classifier (easy/medium/hard/extra,
via vendored [taoyds/spider](https://github.com/taoyds/spider) evaluation
code). Sampling is deterministic (seed 42) and fully regenerable:
classify -> filter -> sample -> execute gold SQL.

**Eligibility rule (applied before sampling, before any arm ran):** tasks
whose gold result exceeds 20 rows are excluded (70/1,034, 6.8% of the pool).
The answer-emission grading format requires the agent to output the complete
result set; beyond ~20 rows the task measures output-length stamina rather
than reliability. The threshold was fixed from the pool's row-count
distribution (p95 = 28, then a cliff to 753+) prior to measuring any arm.

Each task stores the question, db_id, gold SQL, executed gold rows, official
difficulty, and an `order_matters` flag (true iff the gold query has a
top-level `ORDER BY` — subquery ORDER BY does not constrain outer row order).

Spider dev obtained via HuggingFace export; train/dev disjointness verified
during Project 1's contamination audit.

## Results

*(pending)*

## Reproduce

*(pending)*
