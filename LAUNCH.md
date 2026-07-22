# LAUNCH — go/no-go for the k=3 run

Reported numbers come from the tagged commit only. Any red gate means do not
launch. At 02:00, an ambiguous gate counts as red.

Cost ceiling, $20

## Recovery model, decided

One model only, rerun the whole cell. There is no resume and no skip-completed
logic. Cells are independent and seeds derive from (task, run-idx, attempt), so
a rerun reproduces the lost cell. Resume would mean new untested code landing
hours before a freeze.

## Process survival

- [ ] Kickoff runs inside `tmux`, detached and reattached once during the smoke
      to prove the session survives
- [ ] Sleep and suspend disabled for the duration (`systemd-inhibit` wrapper below)
- [ ] GPU steady-state temp noted during the 20-task smoke, since sustained load
      is a regime none of the runs so far have entered

## Code state

- [ ] `git status --porcelain` prints nothing
- [ ] `python -m pytest -q` fully green
- [ ] `_repair_question` closing line is the original wording (alternate tried, reverted)
- [ ] OOD limitation section committed, commit precedes kickoff
- [ ] `run_arm1.py` exists (renamed from `run_smoke.py`) and accepts `--run-idx` and `--tag`
- [ ] Trace filenames carry arm and run-idx, so nine cells are distinguishable without
      opening them

## Validation

- [ ] API dry-run, 10 episodes, real token counts, projection under ceiling
- [ ] 20-task smoke across all three arms, zero crashes
- [ ] Every trace line parses, `run_close` present, episode count matches task count
- [ ] Arm-3 smoke contains at least one episode with `n_attempts > 1`
- [ ] Arm-3 smoke contains at least one `empty_result` trigger, so the frozen
      empty-result constant is rendered by the real tool before the run (force it
      with a known-empty task if none occurs naturally)
- [ ] `kill -9` mid-cell, partial trace still parses, and rerunning the same
      `--arm`/`--run-idx` reproduces identical SQL. Orchestrator text may vary
      within temp-0 API nondeterminism, which is the pre-registered caveat
- [ ] Disk headroom at least 3x projected trace size

### Closed before this list was written
- Render check fired red on verbatim repetition. One alternate rendering was tried,
  did not help, was reverted. Accepted and pre-registered.
- Repair path confirmed end to end against the real tool.

## Pre-decided responses

- Cost over ceiling -> trim orchestrator max output tokens and re-project. If that
  value lives in CONFIG it moves CONFIG_HASH, so it changes before the tag, not after.
- Smoke crash -> fix, then a full re-smoke, not a partial one. If the re-smoke lands
  later than 03:00, sleep and launch in the morning. A tired launch that has to be
  rerun costs more than the hours it saves.
- Cell dies mid-run -> delete its partial trace, rerun that cell alone.
- Partial trace fails to parse -> delete and rerun the cell, and treat it as a bug
  in trace flushing rather than as a data-loss event.

## Kickoff

    tmux new -s p2
    git tag -a p2-frozen -m "frozen for k=3 run" && git rev-parse HEAD

Arm 3 k=0 runs alone first. It is the newest code and the only path exercising the
repair render, error truncation and the empty-result constant. A bug there should
surface at minute 20, not hour 12.

    systemd-inhibit --what=idle:sleep --why="p2 k=3 run" \
      python run_agent.py --arm 3 --run-idx 0 --tag main 2>&1 | tee -a launch.log

Stop. Run the checks below. Only then start the remaining eight cells.

    systemd-inhibit --what=idle:sleep --why="p2 k=3 run" bash -c '
      for k in 1 2; do python run_agent.py --arm 3 --run-idx $k --tag main; done
      for k in 0 1 2; do python run_agent.py --arm 2 --run-idx $k --tag main; done
      for k in 0 1 2; do python run_arm1.py --run-idx $k --tag main; done
    ' 2>&1 | tee -a launch.log

## After the first cell, before walking away

- [ ] Trace filename carries arm and run-idx
- [ ] `run_open` records `run_tag: main`, the frozen `config_hash`, and the tagged commit
- [ ] Episode count matches the bench
- [ ] Wall time per episode is in line with the smoke. Far higher means stop and diagnose
- [ ] Open one arm-3 repair prompt from this `main` trace and confirm it matches the
      frozen template. `config_hash` covers the parameters but not a path or import
      surprise between smoke and main invocation
