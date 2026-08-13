# Arm 1 - single-shot

Baseline arm. One `generate_sql()` call per episode, no repair loop. Three runs
at k=0,1,2 over the 150-task bench.

- traces: `runs/main_arm1_k0_20260722_221512_d05cf2c0b135.jsonl`,
  `runs/main_arm1_k1_20260722_222854_d05cf2c0b135.jsonl`,
  `runs/main_arm1_k2_20260722_224212_d05cf2c0b135.jsonl` (gitignored)
- counts: `analysis/cell_metrics.jsonl`, intervals in `analysis/intervals.json`
- config hash: `d05cf2c0b135`
- tool: `Qwen/Qwen2.5-Coder-1.5B-Instruct` + P1 QLoRA adapter
- orchestrator: `claude-haiku-4-5-20251001`, temp 0
- git commit: `9ca1c7e`, tag `p2-frozen`

## pass@1

**Pre-registered.**

| run | pass@1 |
|---|---|
| k=0 | 93/150 = 62.0% |
| k=1 | 82/150 = 54.7% |
| k=2 | 91/150 = 60.7% |
| pooled | 266/450 = 59.1% |

95% CI on the pooled rate is [52.0%, 66.4%], from a 10,000-draw paired bootstrap
over tasks. The interval is wide because it resamples benchmark composition
while holding the three runs fixed.

The k=1 run at 82 against 93 and 91 is the largest single-cell deviation in the
study. It is not an outlier to be explained away, it is the size of run-to-run
variation at this tool temperature, and it is the reason contrasts rather than
levels carry the results.

Arm 1 at k=0 reproduces the smoke calibration run exactly, on pass@1, every
difficulty split, and every failure bucket, despite the two runs carrying
different config hashes. This is expected. The only `CONFIG` changes between
`d9c233d380d7` and `d05cf2c0b135` were the addition of `agent.max_attempts` and
the `repair` block, both of which are read only by the retry loop. Arm 1 is
single-shot and reads neither, and the `tool` and `seed` values were unchanged,
so identical output under matched seeds is what the design predicts. It is also
a second reproducibility check, across a two-week gap and a config change.

## Difficulty

| run | easy | medium | hard | extra |
|---|---|---|---|---|
| k=0 | 32/38 = 84.2% | 38/65 = 58.5% | 15/25 = 60.0% | 8/22 = 36.4% |
| k=1 | 32/38 = 84.2% | 30/65 = 46.2% | 14/25 = 56.0% | 6/22 = 27.3% |
| k=2 | 33/38 = 86.8% | 37/65 = 56.9% | 12/25 = 48.0% | 9/22 = 40.9% |

Easy is stable across runs. Nearly all the k=1 shortfall lands in medium, 30
against 38 and 37. The gradient is monotone at k=0 apart from hard sitting
slightly above medium, which is a property of the Spider difficulty labels
rather than of the tool.

## Failure decomposition

| bucket | k=0 | k=1 | k=2 |
|---|---|---|---|
| failures | 57 | 68 | 59 |
| no runnable SQL | 23 | 31 | 23 |
| exhausted empty | 0 | 0 | 0 |
| final result empty (any terminal) | 9 | 9 | 7 |
| wrong SQL | 30 | 34 | 33 |
| repair-induced degradation | 0 | 0 | 0 |
| interpretation failure | 4 | 3 | 3 |

`exhausted empty` and `repair-induced degradation` are zero by construction.
Both require a repair loop that arm 1 does not have.

No runnable SQL tracks the k=1 dip closely, 31 against 23 and 23, so the
variation is concentrated in the tool emitting queries that fail to execute
rather than in queries that run and answer wrongly.

Interpretation failure sits at 3 to 4 per cell, 2.0% to 2.7% of episodes, and
holds at that level in all nine main cells across all three arms.

## Consistency

**Pre-registered.**

pass^3, the count of tasks solved in all three runs, is 74/150 = 49.3%, CI
[41.3%, 58.0%].

| band | tasks |
|---|---|
| never solved | 45 |
| solved 1 of 3 | 18 |
| solved 2 of 3 | 13 |
| always solved | 74 |

31 tasks sit in the unstable band. That band is the population every scaffold
result is competing for, since 74 tasks are already solved every time and 45 are
never solved at all.

## Verbatim repetition

Undefined for this arm. Single-shot episodes produce no consecutive attempt
pairs, so the metric has a zero denominator. It is stored as `0/0` in
`cell_metrics.jsonl` and must never be reported as 0%.

## Notes

Attempt 0 in arms 2 and 3 is seed-matched to arm 1 and byte-identical to it.
That is a property of the harness rather than a finding, and its value is as an
integrity check that seed matching held across all 450 episodes of those arms.
