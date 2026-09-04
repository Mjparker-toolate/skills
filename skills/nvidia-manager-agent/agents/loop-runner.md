# Loop Runner

> Spawn a general-purpose subagent and pass these instructions as the prompt.

You execute **one** manager loop iteration. You do not decide to stop the
campaign; the parent does that after you return.

## Inputs (paths only)

The parent passes `skill_root`, `workspace`, and `trigger` (`iteration`).
Read disk; do not trust values pasted in the prompt except those paths.

- `{skill_root}/references/loop-protocol.md`
- `{skill_root}/references/artifacts.md`
- `{workspace}/.nvidia-manager/manager_state.json`
- `{workspace}/.nvidia-manager/loop_log.jsonl` (tail)

## Work

1. Re-read `manager_state.json`. If `status` is `done`, `error`, or
   `stopped`, print that fact and exit without logging a new event.
2. Log **plan** with `scripts/log_loop_event.py` summarizing the next
   product action from `chosen_workflow`.
3. **execute**: invoke the chosen catalog skill or spawn the specialist
   playbook at `{workspace}/agents/<name>.md` if `trained_agents` is set.
   Do not reimplement that skill here. Record artifact paths in
   `{workspace}/.nvidia-manager/iterations/iterN/notes.md`.
4. **evaluate** against `success_criteria`. Prefer eval or KPI files on
   disk. Log evaluate with pass/fail in `--summary`.
5. Do **not** log `decide` or `stop`. The parent logs those.
6. Echo the status line the last `log_loop_event.py` call printed, then exit.

## Logging

Always use the script (absolute paths):

```bash
python3 "{skill_root}/scripts/log_loop_event.py" \
  --log-path "{workspace}/.nvidia-manager/loop_log.jsonl" \
  --iteration N \
  --stage plan \
  --status ok \
  --summary "..."
```

Never write the JSONL file with `echo` or `jq`.

## Limits

- Do not install skills.
- Do not change git remotes or force-push.
- Do not start a new iteration after evaluate; return to the parent.
