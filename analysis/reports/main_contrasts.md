# Contrasts and hypothesis outcomes

Cross-arm results for the nine main cells. Per-arm detail lives in
`main_arm1.md`, `main_arm2.md`, `main_arm3.md`. The tool-swap ablation is in
`ablation_base_tool.md`.

- counts: `analysis/cell_metrics.jsonl`
- intervals: `analysis/intervals.json`
- config hash: `d05cf2c0b135`
- git commit: `9ca1c7e`, tag `p2-frozen`

All intervals are 95% percentile bootstrap, 10,000 draws, seed 0, resampling
the 150 tasks with all three arms scored on the same draw. Runs are held fixed,
so the intervals cover benchmark composition rather than sampling noise across
k. That distinction matters: arm 1's three runs came in at 93, 82, and 91, and
none of that spread is inside these intervals.

## Levels

**Pre-registered** (README, H1a/H1b/H2).

| metric | arm 1 | arm 2 | arm 3 |
|---|---|---|---|
| pass@1 | 59.1% [52.0, 66.4] | 65.8% [58.9, 72.7] | 64.7% [57.8, 71.6] |
| pass^3 | 49.3% [41.3, 58.0] | 56.0% [48.0, 64.0] | 54.0% [46.0, 62.0] |

## Contrasts

| contrast | pass@1 | pass^3 |
|---|---|---|
| arm 1 to arm 2 | +6.7 [+4.0, +9.6] | +6.7 [+2.7, +10.7] |
| arm 1 to arm 3 | +5.6 [+3.1, +8.4] | +4.7 [+1.3, +8.0] |
| arm 2 to arm 3 | -1.1 [-3.6, +1.3] | -2.0 [-6.0, +2.0] |

Pairing is doing visible work. The arm 1 pass@1 interval spans 52.0 to 66.4,
14.4 points wide. The arm 1 to arm 3 contrast spans 3.1 to 8.4, 5.3 points.
Scoring every arm on the same resampled task set removes the benchmark-
composition variance that dominates the level estimates.

## H1a - total scaffold effect

Predicted: arm 3 lifts task success by at least 10 points over arm 1.
Observed: +5.6 [+3.1, +8.4].

**Not met, and informatively so.** The interval excludes 10, so the prediction
is ruled out rather than merely unobserved. It also excludes zero, so the effect
is real and clearly positive at somewhat above half the predicted size.

The mechanism is visible in the failure decomposition. No-runnable-SQL falls
from 23, 31, 23 in arm 1 to 12, 18, 10 in arm 3, roughly halved in every run.
The scaffold's gain comes almost entirely from converting execution failures,
which is what the repair triggers are built to catch.

## H1b - error-feedback effect

Predicted: arm 3 lifts task success by at least 5 points over arm 2 at equal
retry budget. Observed: -1.1 [-3.6, +1.3].

**Ruled out.** The interval excludes 5 comfortably, so the predicted effect is
not merely unobserved but excluded. It also spans zero, so the correct statement
has two parts: no detectable difference in either direction, and a ruled-out +5.

The -1.1 point estimate is not evidence that arm 3 is worse than arm 2. The
interval covers zero and the pass^3 contrast behaves the same way, -2.0
[-6.0, +2.0].

The pre-registered OOD limitation applies here and is not resolved by this
result. A null H1b is consistent with error feedback carrying little value for
this agent, or with this tool being unable to consume feedback in this format.
See `ablation_base_tool.md`, which tests the second explanation directly and
finds it does not account for the null.

At mechanism level the null is equally clean. No-runnable-SQL is 13, 16, 8 in
arm 2 against 12, 18, 10 in arm 3. Both retry arms recover execution failures at
effectively the same rate.

## H2 - stability cost

Predicted: pass^3 improves less than pass@1 across the ladder, so repair raises
average success but is unstable run-to-run.

| contrast | pass@1 | pass^3 | difference |
|---|---|---|---|
| arm 1 to arm 2 | +6.7 | +6.7 | 0.0 |
| arm 1 to arm 3 | +5.6 | +4.7 | -0.9 |

**Not supported.** At arm 2 the two gains are identical, not smaller. At arm 3
pass^3 improves by 0.9 points less, which is the predicted direction but far
inside the intervals, which span [+1.3, +8.0] and [+3.1, +8.4] and overlap
almost entirely.

The band-shift analysis below strengthens the same conclusion from a different
direction: the scaffold does stabilize tasks, one band at a time.

## Consistency bands

**Pre-registered** (README, H2).

| band | arm 1 | arm 2 | arm 3 |
|---|---|---|---|
| never solved | 45 | 37 | 36 |
| solved 1 of 3 | 18 | 14 | 18 |
| solved 2 of 3 | 13 | 15 | 15 |
| always solved | 74 | 84 | 81 |
| unstable (1 or 2 of 3) | 31 | 29 | 33 |

The unstable band looks nearly flat at 31, 29, 33. Taken alone that would
suggest the scaffold buys capability without buying consistency. It does not,
and the band-shift matrix is why.

## Band shifts

Exploratory tier.

arm 1 to arm 2:

| from \ to | never | unstable | always |
|---|---|---|---|
| never (45) | 37 | 8 | 0 |
| unstable (31) | 0 | 21 | 10 |
| always (74) | 0 | 0 | 74 |

arm 1 to arm 3:

| from \ to | never | unstable | always |
|---|---|---|---|
| never (45) | 36 | 8 | 1 |
| unstable (31) | 0 | 25 | 6 |
| always (74) | 0 | 0 | 74 |

arm 2 to arm 3:

| from \ to | never | unstable | always |
|---|---|---|---|
| never (37) | 34 | 3 | 0 |
| unstable (29) | 2 | 24 | 3 |
| always (84) | 0 | 6 | 78 |

Arm 2 moves 10 of arm 1's 31 unstable tasks to always-solved, while 8
never-solved tasks flow in to replace them. The band total barely moves because
two different populations are exchanging places, not because nothing happened.
An earlier reading that the scaffold buys capability and not consistency was
wrong and is retracted.

Never-to-always in one step is 0 for arm 2 and 1 for arm 3. Tasks move one band
at a time.

Arm 2 to arm 3 is the only non-monotone pair. 6 always-solved tasks become
unstable and 2 unstable become never, against 6 tasks improving. That is the
H1b null expressed at task level, and it is a slightly unfavorable net rather
than a wash.

## Unstable-set overlap

Exploratory tier.

| pair | shared | union | jaccard |
|---|---|---|---|
| arm 1, arm 2 | 21 | 39 | 53.8% |
| arm 1, arm 3 | 25 | 39 | 64.1% |
| arm 2, arm 3 | 24 | 38 | 63.2% |

19 tasks are unstable under all three arms. 42 are unstable under at least one.
So instability is substantially a property of the task rather than of the
scaffold, but not entirely: the union is more than double the intersection.

## Integrity checks

Arm 1 to arm 2 and arm 1 to arm 3 are monotone with zero regressions. This is
architectural rather than empirical. Attempt 0 in arms 2 and 3 is seed-matched
to arm 1 and byte-identical to it, so a task solved in arm 1 cannot fail in
either retry arm. Its value is as a check that seed matching held across all
450 episodes of those arms.

`consistency.py` additionally asserts that no cell was traced twice and that all
three arms saw the same 150 task ids. Both pass, so the paired comparison is
valid on its own terms.
