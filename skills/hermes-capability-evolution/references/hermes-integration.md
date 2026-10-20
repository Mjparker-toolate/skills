# Hermes integration

## Use as an Agent Skill

Clone the user's skills repository on the intended Hermes machine. Add its `skills` directory to the existing Hermes configuration without replacing other settings:

```yaml
skills:
  external_dirs:
    - /absolute/path/to/skills-repository/skills
```

Use the active Hermes profile's actual config path. The documented default is `~/.hermes/config.yaml`; do not assume the Helium Home browser profile also names a Hermes profile. Reload/restart through the installed Hermes version's supported workflow, then confirm `hermes-capability-evolution` appears in `skills_list` and can be loaded through `skill_view`. Do not claim installation until this succeeds. External directories may be writable: use review and filesystem permissions as needed.

## Use the native tool plugin

The skill directory also contains `plugin.yaml`, `__init__.py`, and its sibling helper script. Copy the **whole** reviewed `hermes-capability-evolution` directory into the active Hermes profile's `plugins` directory, or use that installed version's supported local-plugin installation workflow. Never copy only `__init__.py`: its helper path is relative to the package.

Inspect `hermes plugins --help` on the actual runtime before choosing local installation syntax. Enable the plugin through the supported plugin workflow. Confirm registration of:

- `capability_search`: BM25 search and optional RRF of supplied dense scores.
- `capability_preflight`: advisory fail-closed action check, never an authorization service.
- `capability_report_check`: reference checks against supplied report/call/installed-skill records.

These tools are pure in-memory helpers. No tool dispatch, external HTTP, browser operation, automatic hook, model request, connector authentication, or skill mutation occurs. Metadata discovery is available through the CLI only, with explicit root arguments, rather than granting an agent a general filesystem scan tool.

The native registration follows the documented `register(ctx)` / `ctx.register_tool(name=..., toolset=..., schema=..., handler=...)` interface. A mock-context test validates wiring and JSON handler outputs. A real Hermes runtime is still required for end-to-end registration verification.

## Workspace labeled Hermes

Configure Anthropic independently using the installed framework's supported provider setup and approved credential store. A workspace label is not a credential or a runtime profile. Do not assume the shared project's custom `ANTHROPIC_WORKSPACE_ID` variable controls native Hermes provider routing. Verify the actual adapter before requesting a workspace-scoped change. Do not copy organization keys into the skill, repo, manifests, logs, or shell history.

## Adoption boundaries

Repository inclusion makes the skill available to users of this catalog; it does not silently update Cue's synchronized skill configuration or an offline Hermes installation. Apply the workflow in the current task, but distinguish that from persistent adoption across chats. If a supported skill-install/update operation is unavailable, report the remaining deployment step instead of inventing a remote installation receipt.

## Validation

Run the skill-creator validator and all bundled tests. The scripts use Python's standard library and relative paths. Linux functional execution is tested; macOS and Windows portability is designed but must be directly verified on those systems before claiming native execution there.
