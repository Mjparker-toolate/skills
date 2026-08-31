# Claude Code Configuration

## Repository Overview
This repository contains Vercel Labs agent skills and extends its capabilities with global skill requirements for relevant queries.

## Global Skill Requirements

### NVIDIA Skills (Always Available When Relevant)
The following NVIDIA-related skills are configured as global requirements and will be automatically available when queries involve:
- CUDA development and optimization
- GPU computing and acceleration
- NVIDIA libraries (cuML, cuDF, cuGraph, etc.)
- Tensor computing and deep learning on NVIDIA hardware
- GPU memory optimization
- NVIDIA AI frameworks
- Parallel computing with NVIDIA tools

**Availability Rule:** These skills will be automatically surfaced and callable whenever a query is determined to be relevant to NVIDIA technologies, CUDA programming, or GPU acceleration.

#### Registered NVIDIA Skills (from NVIDIA/skills repository):
- `cuopt-*` — NVIDIA cuOpt numerical optimization
- `nemo-*` — NVIDIA NeMo LLM/language model skills (20+ variants)
- `nv-medical-ai` — Medical AI frameworks from NVIDIA
- `tao-*` — NVIDIA TAO (Transfer Learning Toolkit) skills
- `rapids-cudf` — Accelerated DataFrame processing with cuDF
- `cudaq-guide` — Quantum computing development
- `jetson-*` — Edge AI on Jetson hardware
- `holoscan-*` — Medical imaging SDK
- `earth2studio-*` — Earth science AI models
- `vss-*` — Vector Search Services (15+ skills)
- `dali-*` — Data pipeline acceleration
- `deepstream-*` — Streaming analytics
- `dynamo-*` — NVIDIA Dynamo capabilities
- `mcore-*` — Model core frameworks
- `rag-*` — Retrieval-augmented generation
- `nemotron-*` — NeMotron model variants
- `portfolio-optimization` — Financial portfolio optimization
- `skill-card-generator` — Skill metadata and documentation
- `omniverse-*` — Digital twin and simulation
- `physical-ai-*` — Physical AI research tools

## Repository Skills

The following agent skills are installed and available:

### Vercel Labs Skills
- `deploy-to-vercel` — Deployment automation with production safety
- `vercel-cli-with-tokens` — CLI integration with secure token handling
- `vercel-optimize` — Performance scanning and optimization recommendations
- `vercel-composition-patterns` — Component composition best practices
- `vercel-react-best-practices` — React framework guidance
- `vercel-react-native-skills` — React Native development
- `vercel-react-view-transitions` — View transition animations

## Skill Invocation

Skills can be invoked using:
```bash
npx skills use "skill-name" --skill "operation"
```

## Global Requirements
This repository enforces:
1. **NVIDIA Skill Availability** — NVIDIA skills are always available for relevant queries
2. **Security** — Token handling follows secure practices (no secret exposure)
3. **Production Safety** — Deployment operations include branch protection
4. **Cross-Platform Support** — All scripts handle Windows and Unix paths
