# Loop Protocol

The manager loop is product-agnostic. Product skills own their own stages
(TAO DEFT, NeMo-RL auto-research, i4h e2e, and so on). This protocol only
defines how the manager iterates, what it writes to disk, and when it stops.

Disk is canonical. Between stages, re-read `manager_state.json` and the tail
of `loop_log.jsonl` from the workspace. Do not trust in-memory copies after a
subagent returns.

## Layout

See [artifacts.md](artifacts.md). Default paths under `${WORKSPACE}/.nvidia-manager/`:

| File | Role |
|---|---|
| `manager_state.json` | Goal, mode, iteration, chosen workflow, stop rules |
| `loop_log.jsonl` | One append-only event per stage, monotonic `seq` |
| `iterations/iterN/` | Per-iteration notes and pointers to product outputs |

## Stages (each iteration)

Execute in order. Log every stage with `scripts/log_loop_event.py`.

1. **plan** — Read state. Restate the goal, the chosen workflow/skill, and
   the smallest next action. If a specialist playbook exists, include its
   path. Do not change the goal here.
2. **execute** — Hand off to the chosen catalog skill, or spawn the trained
   specialist (`agents/<name>.md`) via the Task tool. The manager does not
   reimplement product steps. Capture the artifact path the subagent or
   skill wrote.
3. **evaluate** — Score the iteration against success criteria. Prefer
   existing eval files (`evals/evals.json`, product KPI files) over
   anecdotal judgment. Record pass/fail and evidence path.
4. **decide** — `continue`, `done`, or `error`. Update `iteration` in
   `manager_state.json`. Print one status line from disk.

Spawn `agents/loop-runner.md` for execute+evaluate when those steps would
saturate the parent. The parent always runs **decide** itself so stop rules
cannot be skipped in a child context.

```text
Task(
  description="Manager loop iteration",
  subagent_type="general-purpose",
  prompt=(
    f"Read {skill_root}/agents/loop-runner.md and follow it exactly.\n"
    f"Inputs:\n"
    f"  skill_root = {skill_root}\n"
    f"  workspace  = {workspace}\n"
    f"  trigger    = iteration\n"
  ),
)
```

## Stop rules

Stop the loop when any of these is true:

- Every success criterion in `manager_state.json` is met (`status: done`).
- `iteration` has reached `max_iterations`.
- A stage returns `status: error` that is not recoverable (missing
  credentials, missing dataset, unknown skill slug, product hard-stop).
- The user says stop.

Do not auto-retry hard stops. Recoverable issues (missing install the user
already approved, a playbook typo) may be fixed and the same iteration
re-run; log the recovery as a new event with the same `iteration` and a
new `seq`.

`max_iterations` has no silent default at loop start. If the user did not
supply it, ask once during the Manager Plan. Suggestion-only mode does not
need it.

## Resume

If `${WORKSPACE}/.nvidia-manager/manager_state.json` exists and the user did
not ask for a fresh run:

1. Load it.
2. Print the last `loop_log.jsonl` event.
3. Continue from the next stage implied by that event.
4. Do not call `init_manager_state.py` without `--force`.

## Status line

After every logged stage, print exactly one line:

```text
manager iter=<n> stage=<stage> status=<status> seq=<seq> — <summary>
```

`log_loop_event.py` prints that line on stdout after it appends the event.
Echo it verbatim; do not rebuild it by hand or re-read the log to render it.
Pass `--json` instead when a caller needs the event fields as data.

## What the loop must not do

- Pause for "want me to continue?" after the approval gate.
- Render large HTML/Markdown reports inline in the parent. If a product
  skill has a reporter subagent, spawn that skill's reporter.
- Write `loop_log.jsonl` except through `scripts/log_loop_event.py`.
- Launch GPU training, docker jobs, or cloud spend that the chosen product
  skill itself gates. Those gates still apply after the manager's plan gate.
