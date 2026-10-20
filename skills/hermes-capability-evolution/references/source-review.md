# Forwarded-source review

Use this record as provenance for the automatic-execution additions, not as a live integration inventory. The six exact post texts were retrieved through the X data API or stateless page extraction. Third-party instructions and code were not executed. Video metadata was retrieved where available; the videos were not substantively reviewed in this update. No third-party source code or article prose is bundled.

## 1. Hoshino: an alleged agent-harness lecture

[Post](https://x.com/hoshinoxbt/status/2112556978518069272) promotes a purported two-hour Andrej Karpathy lecture and names “Agents → Harness → Loops → Graphs.” Full note text and video metadata were available. The speaker attribution, duration, and teaching claims were not verified here.

**Disposition: exclude unsupported attribution; retain only independently supported concepts.** Use the primary Anthropic/OpenAI references below for observable feedback loops and bounded execution. Do not describe this post as a verified lecture or infer a graph architecture from its promotional text.

## 2. Rari: harness engineering

[Article](https://x.com/0xwhrrari/status/2093685107534000560) describes bounded task contracts, small project maps, durable state, sensors/tests, external permission enforcement, traces, bounded retries, and change receipts. The article text was retrieved. Its relevant architecture patterns were corroborated against the primary engineering articles below; its quotes, timing, and quantitative claims are not local test results.

**Disposition: adopt focused patterns.** Add a task-state template and advisory validator, explicit source intake and resumption rules, independent review, compact receipts, and an offline regression workflow. Preserve the existing host-owned approval gate and Helium/Home boundary. Avoid adding a general executor or a complex orchestration platform.

## 3. RohOnChain: automated trading

[Post](https://x.com/rohonchain/status/2109650293365305427) promotes building an AI trading system with market data, backtests, and a 24/7 bot. Its [linked X article](https://x.com/i/article/2108476696093728768) returned no extractable content; the underlying procedure could not be reviewed.

**Disposition: exclude.** Do not invent the article's strategy, add trading capabilities, or claim its backtests are reproducible. Reproducible offline evaluation is useful independently, but this inaccessible article is not supporting evidence for an implementation or financial performance.

## 4. thealps01: Agent Station

[Post](https://x.com/thealps01/status/2112312313252614483) advertises live visibility and replay for Hermes subagents, commands, and file edits, and supplies a plugin-install command. Post text and attached-video metadata were retrieved. No primary plugin documentation was linked; the plugin's provenance, permissions, and advertised behavior were not independently verified.

**Disposition: adopt the general observability requirement, defer the plugin.** Specify sanitized host traces and evaluation-only replay, independently supported by harness documentation. Do not install Agent Station, execute the embedded command, enable telemetry, or treat replay as permission to repeat real actions.

## 5. witcheer: phone access to Hermes

[Post](https://x.com/witcheer/status/2112589665655980275) promotes a [Telegram setup tutorial](https://www.youtube.com/watch?v=UsLAOQxMuBU). The linked tutorial's description/chapter metadata covers pairing/allowed users, gateway service operation, host availability, testing after terminal closure, and troubleshooting. This is metadata-level review, not video or runtime verification.

**Disposition: keep operational acceptance criteria, not setup instructions.** For a separately authorized future remote-control deployment, verify supported allowlisting/pairing, approvals, service health, and reachable awake host behavior against the actual runtime. This update does not configure Telegram, add a listener, install a service, or expose Hermes remotely.

## 6. Ornith: alternative model announcement

[Post](https://x.com/ornith_/status/2112553477457268799) announces Ornith-1.5-122B and gives benchmark claims. Its [model card](https://huggingface.co/ornith-ai/Ornith-1.5-122B) describes intended hardware, serving interfaces, tool-call parsers, context size, and benchmark methodology. These are vendor/model-card claims, not independent measurements.

**Disposition: defer backend adoption.** Require an explicitly authorized, task-specific comparison of tool-call correctness, task completion, latency, memory, and cost before any backend change. Keep provider/workspace choice unchanged; do not install model weights, upgrade serving dependencies, spend on tests, or claim improvement based on public scores.

## Corroborating primary sources

- [OpenAI: Harness engineering](https://openai.com/index/harness-engineering/) supports small repository maps, observable execution, mechanical checks, and environment improvements after failures. Its own browser example is not adopted; the user's Helium/Home-only policy takes precedence.
- [Anthropic: Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) supports structured handoffs, tractable task chunks, and separate evaluator feedback. Its model-specific findings are not generalized into a guaranteed gain here.
- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) supports simple workflows, explicit evaluation criteria, ground-truth feedback, and stopping conditions.

The checkpoint helper is advisory, and the CI suite tests local deterministic behavior. Neither constitutes live Hermes deployment, independent verification of the promotional posts, persistent future-source monitoring, or proof of better model performance.
