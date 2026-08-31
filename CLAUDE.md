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

#### Registered NVIDIA Skills:
- `nvidia-cuda-development` — CUDA C/C++ programming, kernel optimization, memory management
- `nvidia-ai-frameworks` — TensorFlow/PyTorch on NVIDIA GPUs, inference optimization
- `nvidia-rapids` — cuML, cuDF, cuGraph data processing
- `nvidia-triton` — Model serving and inference on NVIDIA hardware
- `nvidia-gpu-optimization` — Performance profiling, optimization techniques

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
