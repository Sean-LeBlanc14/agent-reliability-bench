# Arm 2 - resample on failure

Retry arm without feedback. On an execution error or an empty result, the loop
re-calls `generate_sql()` with the original question only, no repair context.
Cap of 3 total calls. Three runs at k=0,1,2 over the 150-task bench.

Cross-arm contrasts, hypothesis outcomes, and band-shift analysis live in
`main_contrasts.md`. This report covers arm 2 on its own.

- traces: `runs/main_arm2_k0_20260722_211511_d05cf2c0b135.jsonl`,
  `runs/main_arm2_k1_20260722_213536_d05cf2c0b135.jsonl`,
  `runs/main_arm2_k2_20260722_215640_d05cf2c0b135.jsonl` (gitignored)
- counts: `analysis/cell_metrics.jsonl`, intervals in `analysis/intervals.json`
- config hash: `d05cf2c0b135`
- tool: `Qwen/Qwen2.5-Coder-1.5B-Instruct` + P1 QLoRA adapter
- orchestrator: `claude-haiku-4-5-20251001`, temp 0
- git commit: `9ca1c7e`, tag `p2-frozen`

## pass@1

**Pre-registered.**

| run | pass@1 |
|---|---|
| k=0 | 101/150 = 67.3% |
| k=1 | 94/150 = 62.7% |
| k=2 | 101/150 = 67.3% |
| pooled | 296/450 = 65.8% |

95% CI on the pooled rate is [58.9%, 72.7%].

Spread across runs is 7 tasks, against arm 1's 11. The same k=1 run that dipped
in arm 1 is the low cell here too, which is expected given attempt 0 is
seed-matched to arm 1 and byte-identical to it.

## Difficulty

| run | easy | medium | hard | extra |
|---|---|---|---|---|
| k=0 | 32/38 = 84.2% | 42/65 = 64.6% | 17/25 = 68.0% | 10/22 = 45.5% |
| k=1 | 32/38 = 84.2% | 38/65 = 58.5% | 16/25 = 64.0% | 8/22 = 36.4% |
| k=2 | 33/38 = 86.8% | 43/65 = 66.2% | 15/25 = 60.0% | 10/22 = 45.5% |

Easy is 32, 32, 33, identical to arm 1 in all three runs. The retry loop
converts nothing on easy tasks. Every gain over arm 1 lands in medium, hard, and
extra: +4/+2/+2 at k=0, +8/+2/+2 at k=1, +6/+3/+1 at k=2.

The reading is that easy tasks the tool gets wrong are wrong in ways resampling
does not fix, since they are answered rather than failed and so never trigger a
retry.

## Failure decomposition

| bucket | k=0 | k=1 | k=2 |
|---|---|---|---|
| failures | 49 | 56 | 49 |
| no runnable SQL | 13 | 16 | 8 |
| exhausted empty | 4 | 4 | 5 |
| final result empty (any terminal) | 4 | 4 | 5 |
| wrong SQL | 28 | 32 | 32 |
| repair-induced degradation | 6 | 7 | 3 |
| interpretation failure | 4 | 4 | 4 |

No runnable SQL falls to 13, 16, 8 from arm 1's 23, 31, 23, roughly halved in
every run. That is where the arm's gain comes from, and it is the bucket the
retry trigger is designed to reach.

`final result empty` equals `exhausted empty` in all three runs, so every
episode ending on empty rows ended by exhausting the cap rather than by the
orchestrator accepting an empty result.

Interpretation failure is 4 in every run, matching arm 1's 3 to 4. Adding a
retry loop does not change how often correct SQL gets misread.

Repair-induced degradation, an empty result at one attempt followed by an
execution failure at the next, is 6, 7, 3. Exploratory tier. Resampling
sometimes converts a query that ran and returned nothing into one that does not
run at all.

## Verbatim repetition

**Pre-registered.**

| run | repeats / consecutive pairs | rate |
|---|---|---|
| k=0 | 2/53 | 3.8% |
| k=1 | 2/64 | 3.1% |
| k=2 | 3/50 | 6.0% |
| pooled | 7/167 | 4.2% |

Arm 2 never places the previous query in the prompt, so these are chance
collisions between independent samples at temperature 0.7, not copying. They
are the floor the arm 3 rate is measured against.

## Consistency

**Pre-registered.**

pass^3 is 84/150 = 56.0%, CI [48.0%, 64.0%].

| band | tasks |
|---|---|
| never solved | 37 |
| solved 1 of 3 | 14 |
| solved 2 of 3 | 15 |
| always solved | 84 |

29 tasks in the unstable band, against arm 1's 31. The band totals barely move,
which is misleading on its own. `main_contrasts.md` has the task-level flow.
