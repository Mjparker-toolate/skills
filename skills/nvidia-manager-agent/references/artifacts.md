# Artifacts

All manager artifacts live under `${WORKSPACE}/.nvidia-manager/` unless the
user names another directory. Product outputs stay wherever the product
skill writes them; the manager only stores pointers.

```text
${WORKSPACE}/
  agents/                      # specialist playbooks (train_agent.py)
  evals/evals.json             # optional specialist evals
  .nvidia-manager/
    manager_state.json         # canonical run state
    loop_log.jsonl             # append-only stage events
    training_log.jsonl         # append-only playbook revisions
    iterations/
      iter1/
        notes.md               # optional human-readable iteration summary
```

## `manager_state.json`

Written by `scripts/init_manager_state.py`. Update `iteration`, `status`,
`chosen_workflow`, and `trained_agents` in place as the run proceeds. Keep
top-level keys unique.

```json
{
  "version": 1,
  "goal": "Drive ChangeNet FAR down with a DEFT-style loop",
  "mode": "loop",
  "max_iterations": 5,
  "iteration": 0,
  "status": "ready",
  "workspace": "/abs/path",
  "created_at": "2026-09-04T15:00:00+00:00",
  "success_criteria": ["FAR at 100% recall below target"],
  "chosen_workflow": null,
  "trained_agents": []
}
```

`status` is one of `ready`, `running`, `done`, `error`, `stopped`.

## `loop_log.jsonl`

One JSON object per line, appended only by `scripts/log_loop_event.py`.
`seq` is `max(existing seq)+1`, or `1` when the file is new. Never invent
`seq` in the shell.

```json
{
  "seq": 1,
  "iteration": 1,
  "stage": "plan",
  "status": "ok",
  "summary": "Will invoke tao-run-deft-aoi baseline evaluate",
  "duration_sec": null,
  "ts": "2026-09-04T15:01:00+00:00"
}
```

## `training_log.jsonl`

One object per `train_agent.py` action:

```json
{
  "ts": "2026-09-04T15:02:00+00:00",
  "action": "init",
  "agent_name": "usd-optimizer",
  "playbook": "/abs/path/agents/usd-optimizer.md",
  "goal": "Optimize OpenUSD scenes for load time and VRAM",
  "notes": null,
  "eval_json": null
}
```

## Path rules

- Resolve every path argument to an absolute path before calling a script.
- Do not write manager state into product spec YAML.
- Do not commit secrets into playbooks, notes, or logs.
- `.nvidia-manager/` may be gitignored by the user's project; do not force
  adding it to git.
