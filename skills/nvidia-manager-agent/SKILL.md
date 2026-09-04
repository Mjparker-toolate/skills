---
name: nvidia-manager-agent
description: >-
  Use when the user wants a manager agent to train other agents, run iterative
  loop workflows, or suggest which workflows to run next. Trigger on manager
  agent, train an agent, agent playbook, loop workflow, iterate until, suggest
  a workflow, orchestrate skills, or run a multi-stage NVIDIA pipeline. Do not
  use for one-shot skill discovery (use nvidia-skill-finder), standalone model
  training without an agent loop, or generic coding tasks.
license: CC-BY-4.0 AND Apache-2.0
compatibility: Requires Python 3 and an agent that can spawn subagents and run bundled scripts.
metadata:
  author: NVIDIA
  version: "0.1.0"
  tags:
    - nvidia
    - manager
    - orchestration
    - loop
    - workflow
    - agent-training
  domain: agent-skills
allowed-tools: Read Task Bash Write
---

# NVIDIA Manager Agent

## Purpose

Act as a manager over other agents and NVIDIA catalog workflows. This skill
does three jobs:

1. **Suggest workflows** — match a user goal to catalog skills and loop
   recipes, ranked with a reason and a first prompt.
2. **Run loop workflows** — execute plan → execute → evaluate → decide until
   a success criterion, iteration budget, or hard stop is hit. Disk state is
   canonical.
3. **Train other agents** — author and revise specialist playbooks from a
   goal, eval results, and failure traces, then spawn those agents on later
   loop iterations.

This skill orchestrates. It does not replace product skills. After the user
approves a suggestion, hand off to the matching catalog skill (or spawn a
trained specialist) rather than reimplementing that product's workflow here.

Treat the live NVIDIA catalog as the source of truth for skill names. The
bundled [references/workflow-catalog.json](references/workflow-catalog.json)
is a starting index of loop-capable and training-adjacent workflows, not a
mirror of every catalog entry.

## When to Use this Skill

Use this skill when the user wants orchestration rather than a single product
step:

- "Create a manager agent that can train other agents"
- "Suggest which workflows I should run"
- "Run a loop until the evals pass / KPI is met"
- "Train a specialist agent for this recurring task"
- "Orchestrate a multi-stage NVIDIA pipeline and keep iterating"

Typical triggers: manager agent, train an agent, agent playbook, loop
workflow, iterate until, suggest a workflow, orchestrate skills, run a
multi-stage pipeline.

Continue only when the request is about managing agents or workflows, not
about discovering a skill to install.

## When Not to Use this Skill

Stay quiet and let another skill (or no skill) handle the request when:

- The user only wants to **find or install** an NVIDIA skill. That is
  `nvidia-skill-finder`.
- The user wants a **single product action** (train this TAO model once,
  convert this USD stage, serve this NIM) with no loop, no specialist
  training, and no workflow shortlist.
- The user wants **GPU/RL model training** as the primary task (NeMo-RL,
  Nemotron customize, TAO train). Route to those skills. This skill may
  *suggest* them inside a loop; it must not run training jobs itself.
- The request is generic software work with no agent-orchestration or NVIDIA
  workflow signal (refactor this file, add a REST route, trim a video).

If relevance is uncertain, answer the user's task first and offer this
manager as an optional next step.

## Safety Gates

There is **one user gate before side effects**: show the Manager Plan
(see [references/workflow-suggestion.md](references/workflow-suggestion.md))
and wait for explicit approval (`go`, `yes`, `looks good`, or a chosen
workflow id). Until then, only read-only catalog lookup, workspace
inspection, and writing a draft plan are allowed.

After approval:

- Running a **loop** is autonomous up to `max_iterations` and the stated
  stop rules. Do not ask "continue?" between iterations.
- **Training an agent** may write playbooks under the workspace `agents/`
  directory. Do not install skills, change agent capabilities, or mutate
  git remotes without a separate explicit approval.
- Never run `npx skills add` or otherwise install skills unless the user
  approves the install.
- Never execute destructive git operations (`reset --hard`, force-push).
- Do not invent catalog skill slugs. If catalog lookup fails, say so and
  fall back to the bundled workflow catalog plus general help.

## Quick Start

Resolve `SKILL_ROOT` to this skill directory. Resolve `WORKSPACE` to the
user's project (repo root, or a path they name). Then:

```bash
python3 "${SKILL_ROOT}/scripts/init_manager_state.py" \
  --workspace "${WORKSPACE}" \
  --goal "<user goal>" \
  --mode suggest \
  --max-iterations 5
```

```bash
python3 "${SKILL_ROOT}/scripts/suggest_workflows.py" \
  --goal "<user goal>" \
  --catalog "${SKILL_ROOT}/references/workflow-catalog.json" \
  --limit 5
```

If a live catalog dump is available (from `npx skills add nvidia/skills --list`
or `skills.sh.json`), pass it with `--live-catalog PATH` so suggestions
include current slugs.

## Mode Selection

| User intent | Mode | First action |
|---|---|---|
| "what should I run?" / "suggest a workflow" | `suggest` | `suggest_workflows.py`, then stop at the Manager Plan |
| "run a loop until …" / "iterate" | `loop` | suggest if no workflow is chosen, then follow [references/loop-protocol.md](references/loop-protocol.md) |
| "train an agent" / "create a specialist" | `train` | follow [references/agent-training.md](references/agent-training.md) |
| mixed ("suggest, then loop, and train a specialist") | `loop` with training enabled | suggest → approve → train playbook → loop, spawning the specialist as needed |

If the user already named a workflow or skill, skip suggestion ranking and
confirm that choice in the Manager Plan.

## Instructions

1. Read this `SKILL.md` completely before spawning subagents or writing state.
2. Classify the request into `suggest`, `loop`, or `train` using the table
   above. Mixed requests default to `loop` with training enabled.
3. Inspect the workspace (repo root, existing `agents/`, eval files, prior
   `manager_state.json`). Resume existing state unless the user asked for a
   fresh run (`--force` on `init_manager_state.py`).
4. Run `scripts/suggest_workflows.py` unless the workflow is already chosen.
   Rank at most five items. For each: id, kind (`loop` / `train` /
   `skill`), why it fits, required skill, and first prompt.
5. Print the Manager Plan and **stop** for approval.
6. After approval, persist state with `init_manager_state.py` (or update the
   existing file) and execute the approved mode:
   - **suggest-only** — deliver the shortlist and stop.
   - **loop** — spawn `agents/loop-runner.md` per the loop protocol. The
     parent re-reads disk state between iterations and prints one status
     line. Spawn `agents/trainer.md` only when the plan includes specialist
     training.
   - **train** — spawn `agents/trainer.md` to write or revise the playbook,
     then show the playbook path and how to invoke it.
7. Hand off product work to the matching catalog skill. Manager agents do
   not reimplement TAO, Omniverse, NeMo-RL, or other product workflows.
8. When the loop stops, write a short outcome: iterations used, stop
   reason, artifacts, and (if training ran) the playbook path plus remaining
   eval gaps.

Spawn contracts, state schema, and artifact layout live in the references
below. Pass **paths**, not copied values, into subagents — disk is the
source of truth.

## Available Scripts

| Script | Purpose | Arguments |
|---|---|---|
| `scripts/init_manager_state.py` | Create `manager_state.json` atomically. Refuses to overwrite without `--force`. | `--workspace PATH --goal TEXT --mode {suggest,loop,train} --max-iterations N [--success-criterion TEXT ...] [--force]` |
| `scripts/suggest_workflows.py` | Rank bundled (and optional live) workflows against a goal. Prints JSON. | `--goal TEXT --catalog PATH [--live-catalog PATH] [--limit N]` |
| `scripts/log_loop_event.py` | Append one JSONL event with a monotonic `seq` read from disk. | `--log-path PATH --iteration N --stage {plan,execute,evaluate,decide,stop} --status {ok,error,continue,done} --summary TEXT [--duration-sec N]` |
| `scripts/train_agent.py` | Init or revise a specialist playbook and append `training_log.jsonl`. | `--workspace PATH --agent-name NAME --goal TEXT --action {init,revise,record-eval} [--notes TEXT] [--eval-json PATH]` |

Run via `run_script()` when the harness provides it; otherwise `python3`
with absolute paths. Never write `loop_log.jsonl` with `echo` or inline
`jq` — `seq` must come from `log_loop_event.py`.

## Agents

| Agent | Purpose | Invoke when |
|---|---|---|
| `agents/manager.md` | Manager persona for hosts that load custom agents from this directory. | User selects this skill as their agent, or a parent wants the full manager prompt in a fresh context. |
| `agents/workflow-advisor.md` | Rank and explain workflow suggestions from disk catalog + goal. | Suggestion ranking would clutter the parent, or the parent context is already large. |
| `agents/loop-runner.md` | Execute one loop iteration (plan/execute/evaluate/decide) from disk state. | Each loop iteration after the approval gate. |
| `agents/trainer.md` | Author or revise a specialist playbook from goal, evals, and traces. | Mode `train`, or a loop iteration that includes specialist training. |

Spawn with the Task tool, `subagent_type="general-purpose"`. The prompt must
tell the subagent to read its agent file first and to take paths only:

```text
Read {skill_root}/agents/loop-runner.md and follow it exactly.
Inputs:
  skill_root = {skill_root}
  workspace  = {workspace}
  trigger    = iteration
```

## References

| Topic | File |
|---|---|
| Suggestion format, Manager Plan, catalog lookup | [references/workflow-suggestion.md](references/workflow-suggestion.md) |
| Loop stages, stop rules, resume | [references/loop-protocol.md](references/loop-protocol.md) |
| Playbook schema, eval-driven revision | [references/agent-training.md](references/agent-training.md) |
| State files, logs, directory layout | [references/artifacts.md](references/artifacts.md) |
| Bundled loop/training workflow index | [references/workflow-catalog.json](references/workflow-catalog.json) |

## Examples

Suggest workflows for a PCB inspection improvement loop:

```text
User: Suggest a workflow to drive ChangeNet FAR down with synthetic defects.
Agent: loads nvidia-manager-agent, runs suggest_workflows.py, shows a Manager
Plan headed by tao-run-deft-aoi, and waits for approval before launching.
```

Run a loop until evals pass:

```text
User: Keep iterating until the specialist's evals.json tasks all pass.
Agent: writes manager_state.json, trains or revises the playbook, then runs
plan/execute/evaluate/decide until the criterion or max_iterations.
```

Train a specialist without starting a loop:

```text
User: Train an agent that knows how to optimize OpenUSD scenes.
Agent: writes agents/usd-optimizer.md via train_agent.py, records the
training log, and tells the user how to spawn it. Does not run omniverse-usd-performance-tuning
unless the user then asks to execute.
```

## Common pitfalls

- Do not treat this skill as `nvidia-skill-finder`. Discovery-only prompts
  belong there; this skill's output is a plan, a loop, or a playbook.
- Do not skip the approval gate because the original prompt said "just run
  it". The Manager Plan is the artifact they need to see first.
- Do not copy KPI numbers, eval scores, or playbook bodies into subagent
  prompts. Pass paths; the subagent reads disk.
- Do not add `automl_policy`, workflow keys, or manager state into product
  training specs (TAO Hydra configs reject unknown keys).
- Model-weight training (SFT/RL/LoRA) is a handoff to `nemo-rl-auto-research`,
  `nemotron-customize`, or the relevant TAO train skill — not a job this
  manager executes inline.
