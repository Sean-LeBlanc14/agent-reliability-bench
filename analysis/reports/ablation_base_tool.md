# Tool-swap ablation - base model as the SQL tool

**EXPLORATORY TIER. Not pre-registered, no confirmatory status, no CIs.**

Arms 2 and 3 over the full 150-task bench at k=1, with the un-fine-tuned
Qwen2.5-Coder-1.5B-Instruct behind `generate_sql()` in place of the P1 QLoRA
adapter. Purpose: test the pre-registered limitation that repair prompts are
out of distribution for the fine-tune, so a weak H1b could not be separated
from "this tool cannot consume feedback in this format."

- traces: `runs/ablation_arm2_k0_20260812_184324_d05cf2c0b135.jsonl`,
  `runs/ablation_arm3_k0_20260812_185637_d05cf2c0b135.jsonl` (gitignored)
- counts: `analysis/ablation_results.txt`
- config hash: `d05cf2c0b135`, identical to the main runs by design
- tool: `Qwen/Qwen2.5-Coder-1.5B-Instruct`, no adapter
- orchestrator: `claude-haiku-4-5-20251001`, temp 0
- git commit: `b70a5a8`

The adapter is the only variable. Same bench, same `build_messages` render, same
`_repair_question` text, same `derive_seed` keys, same quantization config, same
`CONFIG`. The base path keeps 4-bit loading even though nothing in its training
justifies it, so quantization is held constant rather than sitting inside the
contrast.

**Integrity checks.** Both arms show exactly 101 episodes finishing in one
attempt, which is only possible if attempt 0 was byte-identical across arms.
Seed pairing survived the tool swap.

An earlier pair of cells was discarded because its provenance stamp predated the
commit that selected the base tool. Re-running under the correct commit
reproduced every reported quantity exactly, including the per-episode pass/fail
sequence. Seed derivation is therefore reproducible across processes on this
hardware and library set, which is a direct check on the seed-matching the main
study's pairing depends on.

## pass@1

| arm | pass@1 | easy | medium | hard | extra |
|---|---|---|---|---|---|
| 2 | 92/150 = 61.3% | 30/38 = 78.9% | 40/65 = 61.5% | 14/25 = 56.0% | 8/22 = 36.4% |
| 3 | 86/150 = 57.3% | 26/38 = 68.4% | 36/65 = 55.4% | 15/25 = 60.0% | 9/22 = 40.9% |

Arm 3 is 4.0 points below arm 2, 86 against 92 tasks. The adapter's H1b contrast
was -1.1 points, so the gap did not open in the predicted direction, it widened
against arm 3.

- One run at k=1. Main-study arm-1 cells spread 82 to 93 across k, so a 4-point
  pass@1 gap sits inside known run-to-run variation and cannot carry a claim on
  its own. The repetition rates are far outside that spread and are what this
  ablation actually establishes.

## Failure decomposition

| bucket | arm 2 | arm 3 |
|---|---|---|
| failures | 58 | 64 |
| no runnable SQL | 19 | 25 |
| exhausted empty | 6 | 12 |
| final result empty (any terminal) | 6 | 12 |
| wrong SQL | 32 | 26 |
| repair-induced degradation | 7 | 0 |
| interpretation failure | 1 | 1 |

Attempts used: arm 2 `{1: 101, 2: 20, 3: 29}`, arm 3 `{1: 101, 2: 10, 3: 39}`.
Arm 3 recovers on the first repair half as often and reaches the cap far more.

Arm 3 trades wrong SQL for output that does not run or returns nothing. This is
the same shape as the main runs, amplified: arm 2 churns and occasionally breaks
a working state, arm 3 sits still.

## Verbatim repetition

| arm | repeats / consecutive pairs | rate | adapter at k=0 |
|---|---|---|---|
| 2 | 4/78 | 5.1% | 2/53 = 3.8% |
| 3 | 37/88 | 42.0% | 10/59 = 16.9% |

**The pre-registered limitation is closed, in the opposite direction from the
one it anticipated.** Copying is not an artifact of fine-tuning on a fixed
prompt format. Removing the adapter roughly doubled it. Whatever drives a
1.5B-class model to re-emit its previous query when that query is in the
prompt, the fine-tune partially suppressed rather than caused.

## Repeat triggers

| arm | empty_result | exec_error |
|---|---|---|
| 2 | 2/15 = 13.3% | 2/63 = 3.2% |
| 3 | 15/23 = 65.2% | 22/65 = 33.8% |

**This does not replicate the main runs, it reverses them.** Pooled arm 3 in the
main study was flat, 10/47 = 21.3%
