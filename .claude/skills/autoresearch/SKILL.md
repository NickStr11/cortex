---
name: autoresearch
description: "Run autonomous AI research experiments a la Karpathy. Agent loop: edit code, train 5 min, eval, keep/discard, repeat. ~100 experiments overnight on single GPU."
---

# Autoresearch (Karpathy)

## When to Use

- You want to optimize ML training code (architecture, hyperparams, optimizer) autonomously
- You have a single NVIDIA GPU and want to run ~100 experiments overnight unattended
- You want to explore the "agentic research loop" pattern: agent edits code, runs experiment, evaluates, keeps or reverts
- You want a minimal, hackable base (~630 lines) for autonomous ML experimentation
- You want to adapt the pattern to your own training scripts or research domains

## What It Is

An open-source repo by Andrej Karpathy (released March 2026, 37K+ stars). A single-GPU LLM training setup where an AI agent (Claude, Codex, etc.) autonomously:

1. Reads `program.md` (human-written research strategy)
2. Edits `train.py` (GPT model + optimizer + training loop)
3. Runs training for exactly 5 minutes (wall clock)
4. Measures `val_bpb` (validation bits per byte, lower = better)
5. Keeps the change if improved, reverts via git if not
6. Repeats indefinitely

**Three files that matter:**

| File | Who edits | Role |
|------|-----------|------|
| `prepare.py` | Nobody (fixed) | Data prep, tokenizer, dataloader, eval utilities, time budget |
| `train.py` | AI agent | GPT model definition, optimizer (Muon+AdamW), training loop, all hyperparams |
| `program.md` | Human | Agent instructions = "research org operating manual" |

The key insight: human iterates on `.md`, agent iterates on `.py`. The real research artifact is `program.md` -- your ability to write good agent instructions IS the research skill.

Results: autoresearch improvements were merged into nanochat's Time-to-GPT-2 leaderboard, cutting the record from 2.02h to 1.80h on 8xH100 (~11% improvement).

## Prerequisites

- **GPU**: Single NVIDIA GPU (tested on H100; community forks exist for smaller GPUs and Apple Silicon)
- **Python**: 3.10+
- **uv**: Package manager (astral.sh/uv)
- **AI agent**: Claude Code, Codex CLI, or any coding agent that can read/write files and run shell commands
- **Git**: For the keep/revert loop

### For smaller GPUs

Karpathy recommends tuning these in `train.py`:
- Reduce `DEPTH` (e.g., 8 -> 4)
- Lower `TOTAL_BATCH_SIZE` (e.g., to 16K tokens)
- Lower `MAX_SEQ_LEN`
- Simplify `WINDOW_PATTERN` to `"L"`

### Apple Silicon forks

- **autoresearch-macos** by @miolini -- swaps FlashAttention-3 for PyTorch native SDPA
- **autoresearch-mlx** by @trevin-creator -- drops PyTorch/CUDA entirely, runs on MLX. M4 Max achieved val_bpb 1.294

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/karpathy/autoresearch.git
cd autoresearch

# 2. Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies
uv sync

# 4. One-time data prep (~2 min): downloads data, trains BPE tokenizer
uv run prepare.py

# 5. Verify setup: manual training run (~5 min)
uv run train.py
```

If step 5 completes and prints a `val_bpb` score, setup is working.

## Running the Agent

```bash
# Option A: Claude Code (recommended)
# Open the repo in Claude Code, then:
cd autoresearch
claude

# Then prompt:
# "Read program.md and kick off a new experiment. Do the setup first."

# Option B: Codex CLI
codex -C autoresearch "Read program.md and start experimenting"

# Option C: Any agent
# Point your agent at the repo, tell it to read program.md
```

The agent will:
1. Read `program.md` for instructions
2. Create a git feature branch
3. Modify `train.py` (architecture, hyperparams, optimizer, etc.)
4. Run `uv run train.py` (5 min fixed budget)
5. Check `val_bpb` -- keep if improved, `git revert` if not
6. Commit successful changes
7. Loop back to step 3

**Rate**: ~12 experiments/hour, ~100 experiments overnight (8h).

## How It Works

### The Experiment Loop

```
Human writes program.md
         |
         v
Agent reads instructions
         |
         v
  +---> Agent modifies train.py
  |      |
  |      v
  |   uv run train.py (5 min budget)
  |      |
  |      v
  |   Evaluate val_bpb
  |      |
  |    Better?
  |   /      \
  | Yes       No
  |  |         |
  | git commit  git revert
  |  |         |
  +--+---------+
```

### What the Agent Can Change in train.py

- **Model architecture**: depth, embedding dims, attention heads, MLP structure, window patterns
- **Optimizer**: Muon + AdamW settings, learning rates, warmup/cooldown schedules
- **Training loop**: batch size, sequence length, gradient accumulation
- **Everything else**: value embeddings, residual tricks, activation functions

### What's Fixed (prepare.py)

- Dataset download and tokenization
- BPE tokenizer (vocab_size=8192 default)
- Evaluation logic and token budget
- 5-minute wall-clock time budget

This separation prevents the agent from "cheating" by modifying the evaluation.

### Design Choices

- **Single file to modify**: keeps scope manageable, diffs reviewable
- **Fixed time budget**: normalizes across hardware, enables fair comparison
- **Git-based versioning**: clean keep/revert mechanism, full experiment history
- **One metric (val_bpb)**: unambiguous, no multi-objective confusion

## Configuration

### program.md (the key lever)

This is where you define the agent's research strategy. Key things to specify:

- What to explore (architecture changes vs hyperparams vs optimizer tricks)
- Constraints (don't exceed VRAM, keep training stable)
- Priority order (try X before Y)
- What NOT to change (keep certain invariants)

The default `program.md` is intentionally bare-bones. Writing a better `program.md` is the main human contribution.

### train.py defaults worth knowing

| Parameter | Default | Notes |
|-----------|---------|-------|
| `DEPTH` | 8 | Model layers, reduce for smaller GPUs |
| `vocab_size` | 8192 | Can go down to 256 for byte-level |
| `MAX_SEQ_LEN` | varies | Lower for constrained VRAM |
| `DEVICE_BATCH_SIZE` | power of 2 | Scale to GPU memory |
| `TOTAL_BATCH_SIZE` | power of 2 | Scale down for smaller GPUs (e.g., 16K) |
| `WINDOW_PATTERN` | `"SSSL"` | Attention pattern, simplify to `"L"` for speed |
| Optimizer | Muon + AdamW | Agent can change everything |

## Adapting for Your Research

The autoresearch pattern is generalizable beyond nanochat. The core requirements:

1. **One editable file**: the code the agent modifies
2. **One clear metric**: unambiguous, numerical, automatable
3. **Fixed time budget**: normalizes experiments
4. **Git versioning**: clean revert on failure

### To adapt to your own project:

```bash
# 1. Fork autoresearch or start fresh
# 2. Replace train.py with your training script
# 3. Replace prepare.py with your data/eval setup
# 4. Write program.md with your research strategy
# 5. Ensure your script outputs a clear metric the agent can parse
# 6. Point an agent at program.md and let it run
```

### Beyond ML training

The pattern works for anything with a measurable metric:
- Code optimization (benchmark score)
- Prompt engineering (eval accuracy)
- Parameter tuning (any numerical objective)
- Test improvement (coverage %)

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| OOM during training | GPU VRAM too small for defaults | Reduce `DEPTH`, `TOTAL_BATCH_SIZE`, `MAX_SEQ_LEN` in `train.py` |
| FlashAttention-3 not found | Not on H100 / CUDA not available | Use autoresearch-macos fork (SDPA) or autoresearch-mlx fork (Apple Silicon) |
| Agent modifies prepare.py | Agent ignoring instructions | Strengthen constraints in `program.md`, or make `prepare.py` read-only via filesystem permissions |
| val_bpb plateaus after N experiments | Hill-climbing stuck in local optimum | Rewrite `program.md` to suggest different exploration directions (e.g., "try architectural changes, not just hyperparams") |
| Agent makes breaking changes | Code doesn't compile/run | `program.md` should instruct agent to always run a quick sanity check before full 5-min training |
| Experiments not reverting on failure | Git state confusion | Ensure agent works on a feature branch; check `git log` for clean history |

## References

- GitHub repo: https://github.com/karpathy/autoresearch
- VentureBeat overview: https://venturebeat.com/technology/andrej-karpathys-new-open-source-autoresearch-lets-you-run-hundreds-of-ai
- Agent Wars deep dive: https://agent-wars.com/news/2026-03-12-autoresearch-karpathy-ai-agent-llm-training-overnight
- Karpathy's explanation (via blog posts and X): the human's job is to write better `program.md`, the agent's job is to execute research
- macOS fork: https://github.com/miolini/autoresearch-macos
- MLX fork: https://github.com/trevin-creator/autoresearch-mlx
- aiHola analysis: https://aihola.com/article/karpathy-autoresearch-autonomous-agents
- Medium deep analysis: https://medium.com/@aristojeff/autoresearch-why-karpathy-turned-program-md-into-a-research-operating-system-58ae2532374d
