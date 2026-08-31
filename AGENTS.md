<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 NVIDIA Corporation. All rights reserved. -->

# Agent Instructions

## Efficient capability routing

- Keep the default context small. Match tasks against skill metadata first and read a full `SKILL.md` only after selecting that skill.
- For NVIDIA capability discovery, start with `nvidia-skill-finder`; do not preload or scan every skill in the catalog.
- Select the smallest set that fully covers the request. Add another skill, plugin, tool, or agent only when it owns a distinct subtask or materially improves accuracy.
- Prefer project-scoped capabilities. Global installs should be limited to lightweight routers and broadly useful tools.
- Run independent tasks in parallel whenever doing so will not reduce result quality or create write conflicts. Keep dependent or high-risk edits sequential.
- Delegate only substantial independent work. Use parallel workers for bounded scans and reserve deep reasoning for ambiguous, high-risk, or synthesis-heavy work.
- Stop capability discovery once the task is covered.

## Repository invariants

- `skills/` is a signed mirror of product-owned source repositories. Do not hand-edit signed skill payloads unless the task explicitly includes the upstream sync and signing workflow.
- `plugins.d/` is the source of truth for plugin packaging. Treat `plugins/`, plugin manifests, and marketplace JSON files as generated output; regenerate them with `.github/scripts/build-plugins.sh` after changing plugin configuration.
- Preserve unrelated working-tree changes. Do not repair existing metadata, benchmark, or signature drift unless it is in scope.
- Keep repository instructions project-specific. Personal, organization, and science-account preferences or memories do not belong in this public repository.

## Proportional verification

- Run focused checks for the files changed, then the broader checks required by repository automation.
- For plugin or marketplace changes, run `python3 -m unittest discover -s .github/scripts/tests -v` and `.github/scripts/build-plugins.sh --check`.
- If a restricted Codespaces mount makes `.agents/` read-only or rejects rsync group preservation, run the drift check in a writable temporary copy. Do not patch the build script solely for the host-filesystem limitation.
- Run `git diff --check` before handoff and confirm no unintended signed skill changed.
