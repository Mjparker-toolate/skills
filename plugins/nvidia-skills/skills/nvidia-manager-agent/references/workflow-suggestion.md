# Workflow Suggestion

Use this reference after `nvidia-manager-agent` loads and the request needs a
shortlist of workflows. Ranking is a recommendation until the user approves.

## Catalog lookup

Check the live NVIDIA catalog before naming a slug to install. When shell
access is available, try:

```bash
npx skills add nvidia/skills --list
```

Fallback sources if the CLI is unavailable, blocked, or fails:

- https://github.com/NVIDIA/skills/tree/main/skills
- https://build.nvidia.com/skills
- https://raw.githubusercontent.com/NVIDIA/skills/main/skills.sh.json

Save a dump (JSON or text) and pass it to `scripts/suggest_workflows.py`
via `--live-catalog` when you have one. If lookup fails, say the live catalog
could not be checked and rank only the bundled
[workflow-catalog.json](workflow-catalog.json). Do not invent slugs or emit
`npx skills add ... --skill <name>` for a name that did not come from the
live catalog or the bundled index.

The bundled catalog is a **loop and training index**. It highlights workflows
this manager can drive or hand off to. It is not the full NVIDIA catalog.
`nvidia-skill-finder` remains the skill to use when the user only wants to
discover or install a product skill.

## Ranking

Run:

```bash
python3 "${SKILL_ROOT}/scripts/suggest_workflows.py" \
  --goal "<user goal>" \
  --catalog "${SKILL_ROOT}/references/workflow-catalog.json" \
  --limit 5
```

Add `--live-catalog PATH` when a catalog dump exists. The script scores
token overlap against `triggers`, `title`, `when`, and `kind`. Prefer:

1. An exact skill or workflow the user named, if it exists in the catalog.
2. `kind: loop` when the user asked to iterate until a KPI or eval gate.
3. `kind: train` when the user asked to create or improve an agent playbook.
4. `kind: skill` for a one-shot product handoff that still belongs in a
   manager plan (for example a finder install as a prerequisite).

Return at most five rows. Each row must include: `id`, `kind`, `skill`,
`score`, `why`, `first_prompt`, and `install_hint`.

`--format plan` (the default) prints those rows already formatted for the
plan below, plus the `Live catalog checked?` line. Paste them under the plan
header instead of restating them; use `--format json` only when a caller
needs the fields as data.

## Manager Plan

Print this table and stop. Do not launch loops, write playbooks (except a
draft plan), or install skills until the user approves.

```text
## Manager Plan

Goal: <one sentence>
Mode: suggest | loop | train
Workspace: <absolute path>
Max iterations: <n or n/a>
Success criteria: <bullets, or "none yet">

Suggested workflows (highest first):
1. <id> (<kind>, skill=<slug>) — <why>
   First prompt: <one line>
2. ...

Train specialist?: <no | yes, name=<agent-name>>
Live catalog checked?: <yes | no, reason>

Approve by naming a workflow id, or type go / yes. Say stop to cancel.
```

If a required product skill is not installed, say so in the plan and include
the install command **without running it**:

```bash
npx skills add nvidia/skills --skill <skill-name> --global --yes
```

Ask before installing. A catalog match is only a recommendation until the
user confirms.

## After approval

- Persist the chosen workflow id, mode, and success criteria with
  `scripts/init_manager_state.py` (use `--force` only when replacing a
  previous run the user asked to discard).
- If mode is `suggest`, stop after delivering the shortlist.
- If mode is `loop` or `train`, continue with
  [loop-protocol.md](loop-protocol.md) or
  [agent-training.md](agent-training.md).
