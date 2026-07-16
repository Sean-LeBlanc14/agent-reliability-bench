# Agent Reliability Bench

A controlled study of how scaffold choice affects agent reliability,
using text2sql as the testbed. The eval harness is the product;
the agent is the test subject.

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

Grading: agent must output `ANSWER: <value(s)>`, graded by normalized
exact-match against gold rows. No LLM judge. Fully reproducible.

Benchmark: ~100-150 Spider dev questions, stratified by difficulty.
Model: Qwen2.5-Coder-1.5B + QLoRA adapter (see [text2sql](https://github.com/Sean-LeBlanc14/text2sql))

## Results

*(pending)*

## Reproduce

*(pending)*

