# Extraction and adapters

## Provenance

Derive the workflow design from the user's shared **Claude API + Zapier SDK + skills integration** project summary. The summary describes tool search, skill search, task routing, deferred definitions, an approval gate, a restricted Zapier bridge, hybrid retrieval, and AgentReport post-checks. The original named implementation files were not supplied in the shared page and were not found in the inspected connected Data-and-Web-Tools-Project tree. Treat this package as an independent implementation of selected general patterns, not a copy of that project or its running integrations.

The original summary's counts, search benchmarks, workspace ID, and connection failures are historical source claims, not current local facts. Do not propagate identifiers, credentials, or connection state into public manifests.

Use publicly documented Agent Skills structure and Hermes extension contracts. Do not extract protected platform prompts or bulk-copy installed proprietary skill contents. For a user-authorized installed skill, inspect metadata first; before redistribution, check its license and remove private configuration. Link to sources instead of copying where rights are unclear.

## Reusable patterns extracted

| Pattern | Implementation in this package | Boundary |
| --- | --- | --- |
| Skill search | Metadata-only discovery, BM25 search | Explicit approved roots only |
| Hybrid retrieval | RRF when real external dense scores are supplied | No embedding/model dependency bundled |
| Deferred tool definitions | Workflow selects complete schemas on demand | Runtime support required; no fabricated tool_reference support |
| Approval gates | Advisory fail-closed decision helper | Host must enforce exact-payload approvals |
| AgentReport | Cross-check report evidence against supplied ledger | Ledger must be independently host-owned |
| Self-improvement | Evidence, regression, diff, review, promotion, rollback loop | No autonomous privilege expansion |

## Expand available capabilities

For each candidate, record ID, kind, source/revision, description, effect, available, authorized, and its complete schema when relevant. Use `unknown` effects until verified from actual tool documentation. Availability does not imply permission; authorization does not imply correct configuration. Mark each adapter as proposed, locally tested, configured, or live-verified.

Prefer live authorized connector discovery over static tool inventories. Load the exact schema before invocation. Do not substitute web research for a missing operational integration. A skill explains how to act; a script adds deterministic logic; a host-native tool adds an actual callable interface. State which one was delivered.

## Zapier adapter contract

If the original bridge becomes available, restrict bridge dispatch to `list_connections`, `input_schema`, and `run_action`. Treat listing connections as metadata access, not blanket permission to run actions. Validate action input using its actual schema, block delete and arbitrary-HTTP actions, bind approval to connection/action/canonical arguments, and execute through the host gate once. Inspect an uncertain outcome before retrying. This package does not bundle or simulate that bridge and does not authenticate Zapier.

## Anthropic workspace contract

Keep the Hermes workspace distinct from Hermes Agent profiles. Inspect the actual installed adapter before using `--workspace` or `ANTHROPIC_WORKSPACE_ID`: those are the source project's interface, not a guaranteed Anthropic SDK or Hermes interface. Prefer a workspace-scoped API credential obtained through approved secret storage; never assume an organization-level key was scoped by setting an unsupported environment variable. Do not switch workspace or send a paid model request just to test this package.

## Sources

- User-provided shared project summary (source link retained in the task context; no original implementation files bundled).
- [Hermes Agent skill creation](https://github.com/Mjparker-toolate/hermes-agent/blob/d7e1652511812feff4bfb1165157959ab4b18a34/website/docs/developer-guide/creating-skills.md).
- [Hermes native plugin contract](https://github.com/Mjparker-toolate/hermes-agent/blob/d7e1652511812feff4bfb1165157959ab4b18a34/website/docs/developer-guide/plugins/index.md).
- [Hermes skill discovery and external directories](https://github.com/Mjparker-toolate/hermes-agent/blob/d7e1652511812feff4bfb1165157959ab4b18a34/website/docs/user-guide/features/skills.md).

No external skill source code was copied into this package.
