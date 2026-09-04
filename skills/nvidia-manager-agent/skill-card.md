## Description: <br>
Manager agent that suggests NVIDIA workflows to run, executes iterative loop pipelines with disk-canonical state, and trains specialist agents by writing and revising playbooks from goals and evals. <br>

This skill is ready for commercial/non-commercial use. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
CC-BY-4.0 AND Apache-2.0 <br>
## Use Case: <br>
Developers and engineers who need an orchestrator over NVIDIA catalog skills: shortlisting workflows, running plan-execute-evaluate loops, and training specialist coding-agent playbooks. Not for one-shot skill discovery (use nvidia-skill-finder) and not for GPU weight training. <br>

### Deployment Geography for Use: <br>
Global <br>

## Requirements / Dependencies: <br>
**Requires API Key or External Credential:** [No] <br>
**Credential Type(s):** [None] <br>

Product skills suggested by this manager may require their own credentials. Do not include secrets in prompts/logs/output; use least-privilege credentials; rotate keys as appropriate. <br>

## Known Risks and Mitigations: <br>
Risk: Autonomous loops could invoke expensive product workflows (training jobs, cloud spend) or install skills without intent. <br>
Mitigation: Single approval gate (Manager Plan) before side effects; ask before `npx skills add`; product-skill gates still apply; GPU/RL weight training is a handoff, not executed here. <br>

Risk: Suggested slugs could be stale or invented if live catalog lookup fails. <br>
Mitigation: Live catalog check required before install commands; bundled index is explicitly not a full catalog; do not fabricate slugs. <br>

## Reference(s): <br>
- [Workflow Suggestion](references/workflow-suggestion.md) <br>
- [Loop Protocol](references/loop-protocol.md) <br>
- [Agent Training](references/agent-training.md) <br>
- [NVIDIA Skills Catalog](https://build.nvidia.com/skills) <br>
- [NVIDIA Skills GitHub Repository](https://github.com/NVIDIA/skills/tree/main/skills) <br>

## Skill Output: <br>
**Output Type(s):** [Analysis, files, shell commands, configuration instructions] <br>
**Output Format:** [Markdown plus JSON state/logs under `.nvidia-manager/`] <br>
**Output Parameters:** [manager_state.json, loop_log.jsonl, training_log.jsonl, agents/*.md] <br>
**Other Properties Related to Output:** [Approval required before loops, installs, or playbook init] <br>

## Evaluation Agents Used: <br>
Not yet run through Skill Evaluator live agents. Task set is in `evals/evals.json`. <br>

## Evaluation Tasks: <br>
7 evaluation tasks (4 positive activation, 3 negative activation) authored for Skill Evaluator. Live Tier 3 results are not available in this report. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Checks whether skill-assisted execution avoids unsafe behavior such as secret leakage, destructive commands, or unauthorized access. <br>
- Correctness: Checks whether the agent follows the expected workflow and produces the correct final output. <br>
- Discoverability: Checks whether the agent loads the skill when relevant and avoids using it when irrelevant. <br>
- Effectiveness: Checks whether the agent performs measurably better with the skill than without it. <br>
- Efficiency: Checks whether the agent uses fewer tokens and avoids redundant work. <br>

## Evaluation Results: <br>
Tier 3 dimension rollup was not available in this report. <br>

## Skill Version(s): <br>
0.1.0 <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. This manager can spawn subagents and recommend installs; humans must approve the Manager Plan and any capability changes. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
