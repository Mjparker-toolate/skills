# Claude Code Configuration

## Repository Overview
This repository hosts installed agent skills (Vercel Labs, NVIDIA, Apify, AWS) available to Claude Code via the Skill tool.

## NVIDIA Skill Policy

Hundreds of official NVIDIA skills are installed under `.agents/skills/` (cuOpt,
NeMo, TAO, Jetson, DOCA, Holoscan, DeepStream, VSS, RAPIDS/cuDF, cuPyNumeric,
Dynamo, Omniverse, Physical AI, and more). They are already lazy-loaded: Claude
sees only each skill's name and one-line description until it is actually
invoked, so listing them here would only duplicate context and go stale as the
catalog grows — treat the installed `.agents/skills/` directory and the live
skill listing as the source of truth, not this file.

**Global requirement:** for any request that is plausibly NVIDIA-relevant
(NVIDIA hardware/software, CUDA, GPU acceleration, or one of the installed
product lanes), invoke `nvidia-skill-finder` even if the user did not
explicitly ask for a skill — it is NVIDIA's own router skill, built exactly for
implicit-trigger relevance detection over this catalog. Let it identify and
recommend the single best-matching skill (or, for a request spanning multiple
domains, one skill per relevant step) rather than guessing a skill name
directly.

**Multi-skill workflows:** when a task genuinely spans more than one domain
(e.g. optimize a routing problem with cuOpt, then serve results through
Dynamo), invoke each relevant skill for its own step — sequentially or via
parallel subagents — rather than forcing one skill to cover the whole
workflow.

**Anti-pattern:** never read or preload multiple skill directories
speculatively "just in case." Resolve relevance first (via `nvidia-skill-finder`
or a targeted skill-name match), then invoke only the skill(s) actually needed.

## Repository Skills

### Vercel Labs Skills
- `deploy-to-vercel` — Deployment automation with production safety
- `vercel-cli-with-tokens` — CLI integration with secure token handling
- `vercel-optimize` — Performance scanning and optimization recommendations
- `vercel-composition-patterns` — Component composition best practices
- `vercel-react-best-practices` — React framework guidance
- `vercel-react-native-skills` — React Native development
- `vercel-react-view-transitions` — View transition animations

### NVIDIA Skills
See `.agents/skills/` for the full installed catalog, or invoke
`nvidia-skill-finder` to discover the right one for a given task.

### Apify Skills
- `apify-ultimate-scraper` — Web scraping and data extraction across ~100
  Apify Actors (social, search, maps, marketplaces) via the Apify CLI.
  Needs `apify-cli` and an authenticated session (`APIFY_TOKEN`); the skill
  verifies both before it runs anything.

### AWS Skills
- `amplify-workflow` — AWS Amplify Gen2 full-stack development: auth, data,
  storage, functions, and the AI kit, plus per-framework frontend wiring.

## Skill Bootstrap

Installing a skill writes three artifacts that have to agree:

1. `.agents/skills/<name>/` — the vendored skill content.
2. `skills-lock.json` — where the content came from, plus the folder hash
   recorded at install time.
3. `.claude/skills/<name>` — a relative symlink into `.agents/skills/`.

Miss one and the skill half-exists without saying so: a vendored folder with
no lock entry is invisible to `npx skills list`/`update`, and a lock entry
with no symlink never loads in Claude Code. Verify all three with:

```bash
python3 .github/scripts/bootstrap_skills.py --check
```

Use that script's `--add` to bootstrap a skill from a local folder (a Cursor
plugin cache, say) instead of hand-editing the three artifacts; it computes
the same folder hash the skills CLI does. Content drift against a recorded
hash is reported as a warning, not an error — the hash records the folder as
installed, so for a locally-patched skill the drift is the true state and the
hash is never silently rewritten.

## Other Requirements
1. **Security** — Token handling follows secure practices (no secret exposure)
2. **Production Safety** — Deployment operations include branch protection
3. **Cross-Platform Support** — All scripts handle Windows and Unix paths
