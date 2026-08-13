# Arm 3 - resample with error feedback

Retry arm with feedback. On an execution error or an empty result, the loop
re-calls `generate_sql()` with the previous SQL and the executor error injected
into the question slot via `_repair_question()`. Same cap of 3 total calls as
arm 2. Three runs at k=0,1,2 over the 150-task bench.

Cross-arm contrasts, hypothesis outcomes, and band-shift analysis live in
`main_contrasts.md`. This report covers arm 3 on its own.

- traces: `runs/main_arm3_k0_20260722_152542_d05cf2c0b135.jsonl`,
  `runs/main_arm3_k1_20260722_203443_d05cf2c0b135.jsonl`,
  `runs/main_arm3_k2_20260722_205613_d05cf2c0b135.jsonl` (gitignored)
- counts: `analysis/cell_metrics.jsonl`, intervals in `analysis/intervals.json`
- config hash: `d05cf2c0b135`
- tool: `Qwen/Qwen2.5-Coder-1.5B-Instruct` + P1 QLoRA adapter
- orchestrator: `claude-haiku-4-5-20251001`, temp 0
- git commit: `9ca1c7e`, tag `p2-frozen`

This arm carries the pre-registered OOD limitation. The adapter trained on a
single zero-shot turn, and the repair render puts content in the question slot
that the adapter never saw. See the README section for the full statement and
for the five-task render check that preceded the runs.

## pass@1

**Pre-registered** (README, H1a and H1b).

| run | pass@1 |
|---|---|
| k=0 | 100/150 = 66.7% |
| k=1 | 91/150 = 60.7% |
| k=2 | 100/150 = 66.7% |
| pooled | 291/450 = 64.7% |

95% CI on the pooled rate is [57.8%, 71.6%].

Spread is 9 tasks, between arm 1's 11 and arm 2's 7. The k=1 cell is low in all
three arms, which follows from attempt 0 being seed-matched across arms.

## Difficulty

| run | easy | medium | hard | extra |
|---|---|---|---|---|
| k=0 | 32/38 = 84.2% | 42/65 = 64.6% | 16/25 = 64.0% | 10/22 = 45.5% |
| k=1 | 32/38 = 84.2% | 36/65 = 55.4% | 15/25 = 60.0% | 8/22 = 36.4% |
| k=2 | 33/38 = 86.8% | 43/65 = 66.2% | 14/25 = 56.0% | 10/22 = 45.5% |

Easy is 32, 32, 33, identical to arms 1 and 2 in every run. No retry scaffold
of either kind converts an easy task, because easy failures are answered rather
than failed and never trigger a retry.

Against arm 2 the differences are small and unsigned: k=0 matches on easy,
medium, and extra and loses one on hard; k=1 loses two on medium; k=2 matches
on three and loses one on hard.

## Failure decomposition

| bucket | k=0 | k=1 | k=2 |
|---|---|---|---|
| failures | 50 | 59 | 50 |
| no runnable SQL | 12 | 18 | 10 |
| exhausted empty | 7 | 7 | 7 |
| final result empty (any terminal) | 7 | 7 | 7 |
| wrong SQL | 27 | 31 | 30 |
| repair-induced degradation | 1 | 1 | 2 |
| interpretation failure | 4 | 3 | 3 |

No runnable SQL is 12, 18, 10 against arm 2's 13, 16, 8. The two retry arms
recover execution failures at effectively the same rate, which is the H1b null
visible at the mechanism level rather than in the headline number.

`exhausted empty` is exactly 7 in all three runs and exceeds arm 2's 4, 4, 5.
Arm 3 ends on empty results more often than arm 2 does.

Repair-induced degradation is 1, 1, 2 against arm 2's 6, 7, 3. Exploratory
tier. Arm 3 rarely converts an empty result into an execution failure, because
it rarely changes the query at all. That reads as a virtue in isolation and is
the same behavior that produces the repetition rate below.

Interpretation failure is 3 to 4, unchanged from arms 1 and 2.

## Verbatim repetition

**Pre-registered** (README, OOD limitation section).

| run | repeats / consecutive pairs | rate |
|---|---|---|
| k=0 | 10/59 | 16.9% |
| k=1 | 20/71 | 28.2% |
| k=2 | 11/52 | 21.2% |
| pooled | 41/182 | 22.5% |

Against arm 2's 3.8%, 3.1%, 6.0%, roughly 5x in every paired cell and in the
same direction all three times. Because seeds are arm-independent, the two arms
resample under matched seeds and differ only in prompt content, so this gap
isolates the effect of the repair context on tool variance.

This is the five-task render check reproducing at scale, on 182 real repair
pairs rather than 5 constructed ones.

The mechanism is exploratory and was tested separately. The prediction that
repeats would concentrate on the contentless `empty_result` trigger failed:
pooled, arm 3 repeats on 10/47 = 21.3% of `empty_result` pairs against 31/135 =
23.0% of `exec_error` pairs, with the direction flipping across cells. So the
copying is trigger-independent for this tool. The driver is the previous query
being present in the prompt, not the error message being uninformative. The
strong form is that arm 3 re-emits a byte-identical query about 23% of the time
even when handed a real SQLite error.

## Consistency

**Pre-registered** (README, H2).

pass^3 is 81/150 = 54.0%, CI [46.0%, 62.0%].

| band | tasks |
|---|---|
| never solved | 36 |
| solved 1 of 3 | 18 |
| solved 2 of 3 | 15 |
| always solved | 81 |

33 tasks unstable, against 31 in arm 1 and 29 in arm 2.
