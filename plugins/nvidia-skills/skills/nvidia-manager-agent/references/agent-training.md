# Agent Training

"Training" in this skill means **playbook training**: writing and revising
specialist agent instructions from a goal, evals, and failure traces. It is
not GPU weight training. For SFT/RL/LoRA/NeMo-RL campaigns, suggest the
matching catalog skill (`nemo-rl-auto-research`, `nemotron-customize`, or a
TAO train skill) and hand off.

## When to train

- The user asked to create, improve, or specialize an agent.
- A loop plan includes a recurring subtask that should not keep living in
  the parent context (report rendering, a product SOP, a review checklist).
- Eval tasks for a specialist exist and are failing.

Do not train a specialist for a one-line lookup or a single shell command.

## Playbook location

Default: `${WORKSPACE}/agents/<agent-name>.md`

`agent-name` is lowercase kebab-case. Refuse names that contain `..`, `/`,
or whitespace.

## Commands

Initialize:

```bash
python3 "${SKILL_ROOT}/scripts/train_agent.py" \
  --workspace "${WORKSPACE}" \
  --agent-name "<agent-name>" \
  --goal "<specialist goal>" \
  --action init
```

Revise after failures (notes should cite eval ids or log paths, not paste
secrets):

```bash
python3 "${SKILL_ROOT}/scripts/train_agent.py" \
  --workspace "${WORKSPACE}" \
  --agent-name "<agent-name>" \
  --goal "<same or tightened goal>" \
  --action revise \
  --notes "eval pos-002 failed: specialist skipped the approval gate"
```

Record an eval snapshot:

```bash
python3 "${SKILL_ROOT}/scripts/train_agent.py" \
  --workspace "${WORKSPACE}" \
  --agent-name "<agent-name>" \
  --goal "<goal>" \
  --action record-eval \
  --eval-json "${WORKSPACE}/evals/evals.json"
```

Each action appends one object to
`${WORKSPACE}/.nvidia-manager/training_log.jsonl`.

## Playbook schema

Generated playbooks must include YAML frontmatter (`name`, `description`)
and these sections:

| Section | Content |
|---|---|
| Purpose | One paragraph: what this specialist owns |
| When to invoke | Triggers the manager should use |
| When not to invoke | Handoff rules (parent, product skill, human) |
| Instructions | Numbered steps the specialist follows |
| Success criteria | Observable checks, preferably eval ids |
| Training history | Append-only list of revisions (date, reason) |

The trainer subagent (`agents/trainer.md`) may add domain sections after
Instructions, but must not remove the required ones.

## Eval-driven revision

When eval results are present:

1. Read failing `expected_behavior` items and `ground_truth`.
2. Change the smallest playbook section that would have produced the miss.
3. Record the revision with `--action revise` and the eval id in `--notes`.
4. Do not claim the specialist is trained until failing evals are re-run or
   the user accepts the playbook as a draft.

If no eval file exists, write a starter `evals/evals.json` **only when the
user asked for training**, with at least one positive and one negative
task. Negative tasks must describe when the specialist must *not* run.

## Spawn contract

```text
Task(
  description="Train specialist agent",
  subagent_type="general-purpose",
  prompt=(
    f"Read {skill_root}/agents/trainer.md and follow it exactly.\n"
    f"Inputs:\n"
    f"  skill_root = {skill_root}\n"
    f"  workspace  = {workspace}\n"
    f"  agent_name = {agent_name}\n"
    f"  trigger    = init   # or revise | record-eval\n"
  ),
)
```

Pass paths and the agent name. Do not paste the previous playbook body into
the prompt; the trainer reads it from disk.

## Handoff to weight training

If the user actually wants model weights updated, stop playbook training
and recommend the live-catalog skill that matches (commonly
`nemo-rl-auto-research` or `nemotron-customize`). Do not start GPU jobs
from this skill.
