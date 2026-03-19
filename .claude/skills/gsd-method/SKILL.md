---
name: gsd-method
description: "GSD (Get Shit Done) — meta-prompting and spec-driven development method for Claude Code. Maximum output, minimal overhead. Solves context rot. Use when starting a large feature, multi-step implementation, or complex task that benefits from a spec-first approach. Also triggers on: 'напиши спеку', 'разбей на задачи', 'spec-driven', 'большая фича', or when the user wants structured task breakdown before coding."
---

# GSD -- Get Shit Done

## When to Use

- Solo dev building with Claude Code (primary use case)
- Any project where context rot kills quality past task 10-15
- Greenfield: new project from idea to shipped code
- Brownfield: adding features to existing codebase
- When you need clean git history with atomic commits per task
- When "vibe coding" produces inconsistent garbage at scale

## What It Is

GSD is a meta-prompting, context engineering, and spec-driven development system. Created by TACHES (glittercowboy). 30K+ stars, MIT license. Works with Claude Code, OpenCode, Gemini CLI, Codex, Copilot.

**Core philosophy:** The complexity is in the system, not in your workflow. Behind the scenes: context engineering, XML prompt formatting, subagent orchestration, state management. What you see: a few commands that just work.

**The problem it solves:** Context rot -- quality degradation as Claude fills its context window. By task 15-20, the agent forgets requirements, drifts from vision, starts "being more concise." GSD fixes this by:
- Breaking work into small plans, each executed in a fresh context window
- Externalizing project memory into structured files (not the chat)
- Atomic git commits per task (bisectable history)
- Each executor gets ~200K tokens purely for implementation, zero accumulated garbage

## Prerequisites

- Claude Code (Max plan or API key)
- Node.js 18+ (for npx installer)
- Git initialized in project

## Setup

### Install (one command)

```bash
# Interactive (prompts for runtime + location)
npx get-shit-done-cc@latest

# Non-interactive for Claude Code
npx get-shit-done-cc --claude --global   # Install to ~/.claude/
npx get-shit-done-cc --claude --local    # Install to ./.claude/

# Other runtimes
npx get-shit-done-cc --opencode --global
npx get-shit-done-cc --gemini --global
npx get-shit-done-cc --codex --global
npx get-shit-done-cc --copilot --global

# All runtimes at once
npx get-shit-done-cc --all --global
```

### Update

```bash
npx get-shit-done-cc@latest
```

### Uninstall

```bash
npx get-shit-done-cc --claude --global --uninstall
npx get-shit-done-cc --claude --local --uninstall
```

### Verify

Inside Claude Code, run `/gsd:help`. If it responds -- you're set.

## Core Workflow

The full lifecycle is a chain of slash commands. Each phase runs in a fresh context.

### Step 1: Initialize Project

```
/gsd:new-project
```

The system:
1. **Questions** -- asks until it fully understands your idea (goals, constraints, tech, edge cases)
2. **Research** -- spawns parallel agents to investigate the domain (optional but recommended)
3. **Requirements** -- extracts v1, v2, and out-of-scope
4. **Roadmap** -- creates phases mapped to requirements

You approve the roadmap. Creates: `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `.planning/research/`

For existing codebases, run `/gsd:map-codebase` FIRST -- it analyzes stack, architecture, conventions. Then `/gsd:new-project` knows your codebase.

### Step 2: Discuss Phase (optional but powerful)

```
/gsd:discuss-phase 1
```

Your roadmap has 1-2 sentences per phase. Not enough to build what YOU imagine. This step captures preferences before planning:

- Visual features -> layout, density, interactions, empty states
- APIs/CLIs -> response format, flags, error handling
- Content systems -> structure, tone, depth
- Organization tasks -> grouping criteria, naming, exceptions

Output: `{phase_num}-CONTEXT.md` -- feeds into researcher and planner.

The deeper you go here, the more the system builds YOUR vision. Skip it and you get reasonable defaults.

### Step 3: Plan Phase

```
/gsd:plan-phase 1
```

The system:
1. **Researches** -- investigates how to implement, guided by CONTEXT.md
2. **Plans** -- creates 2-3 atomic task plans with XML structure
3. **Verifies** -- checks plans against requirements, loops until pass

Each plan is small enough for a fresh context window. Creates: `{phase_num}-RESEARCH.md`, `{phase_num}-{N}-PLAN.md`

### Step 4: Execute Phase

```
/gsd:execute-phase 1
```

The system:
1. **Runs plans in waves** -- parallel where possible, sequential when dependent
2. **Fresh context per plan** -- 200K tokens for implementation, zero garbage
3. **Commits per task** -- atomic git commit each
4. **Verifies against goals** -- checks codebase delivers what phase promised

Wave execution: plans grouped by dependencies. Within a wave = parallel. Waves = sequential.

```
WAVE 1 (parallel)        WAVE 2 (parallel)        WAVE 3
[Plan 01] [Plan 02]  ->  [Plan 03] [Plan 04]  ->  [Plan 05]
 User      Product        Orders    Cart           Checkout
```

Walk away, come back to completed work with clean git history.

### Step 5: Verify & Continue

```
/gsd:verify-work 1          # Manual user acceptance testing
/gsd:audit-milestone        # Verify milestone achieved DoD
/gsd:complete-milestone     # Archive milestone, tag release
/gsd:new-milestone [name]   # Start next version
```

### Quick Mode (for small tasks)

```
/gsd:quick                        # Bug fix, small feature, config change
/gsd:quick --discuss              # With lightweight discussion first
/gsd:quick --research             # With focused research before planning
/gsd:quick --discuss --research --full  # All bells and whistles
```

Same agents, same quality. Skips optional steps. Lives in `.planning/quick/`.

## Key Files & Structure

### .planning/ directory

```
.planning/
  PROJECT.md          # Project vision (always loaded by agents)
  REQUIREMENTS.md     # Scoped v1/v2 requirements with phase traceability
  ROADMAP.md          # Phases, dependencies, execution plan
  STATE.md            # Decisions, blockers, position -- memory across sessions
  config.json         # Model profile, workflow agent preferences
  research/           # Domain investigation findings
  quick/              # Quick mode plans and summaries
    001-task-name/
      PLAN.md
      SUMMARY.md
  phases/
    01/
      01-CONTEXT.md   # Discussion output (from discuss-phase)
      01-RESEARCH.md  # Research output (from plan-phase)
      01-1-PLAN.md    # Task plan 1
      01-2-PLAN.md    # Task plan 2
      01-SUMMARY.md   # Execution summary
  todos/              # Captured ideas for later
```

### Context engineering -- what each file does

| File | Purpose | When loaded |
|------|---------|-------------|
| `PROJECT.md` | Project vision | Always |
| `research/` | Ecosystem knowledge (stack, pitfalls) | During planning |
| `REQUIREMENTS.md` | Scoped requirements with phase traceability | Planning, verification |
| `ROADMAP.md` | Where you're going, what's done | Phase transitions |
| `STATE.md` | Decisions, blockers, position | Session start |
| `PLAN.md` | Atomic task with XML structure + verification | Execution |
| `SUMMARY.md` | What happened, committed to history | Post-execution |
| `todos/` | Ideas captured for later | On demand |

Size limits are calibrated to where Claude's quality degrades. Stay under, get consistent results.

## Prompting Patterns

### XML Task Structure (core of every plan)

```xml
<task type="auto">
  <name>Create login endpoint</name>
  <files>src/app/api/auth/login/route.ts</files>
  <action>
    Use jose for JWT (not jsonwebtoken - CommonJS issues).
    Validate credentials against users table.
    Return httpOnly cookie on success.
  </action>
  <verify>curl -X POST localhost:3000/api/auth/login returns 200 + Set-Cookie</verify>
  <done>Valid credentials return cookie, invalid return 401</done>
</task>
```

Key elements:
- `<name>` -- what the task is
- `<files>` -- exactly which files to touch (scopes the work)
- `<action>` -- precise instructions, not vague descriptions
- `<verify>` -- how to check it works (runnable command)
- `<done>` -- definition of done

### Auto mode flag

`--auto` on new-project, discuss-phase, plan-phase lets GSD make reasonable defaults without asking. Good for experienced users who trust the system.

```
/gsd:new-project --auto
/gsd:discuss-phase 1 --auto
/gsd:plan-phase 1 --auto
```

## All Commands Reference

### Core Workflow

| Command | What it does |
|---------|-------------|
| `/gsd:new-project [--auto]` | Questions -> research -> requirements -> roadmap |
| `/gsd:discuss-phase [N] [--auto]` | Capture implementation decisions before planning |
| `/gsd:plan-phase [N] [--auto]` | Research + plan + verify for a phase |
| `/gsd:execute-phase <N>` | Execute all plans in parallel waves |
| `/gsd:verify-work [N]` | Manual user acceptance testing |
| `/gsd:audit-milestone` | Verify milestone achieved DoD |
| `/gsd:complete-milestone` | Archive milestone, tag release |
| `/gsd:new-milestone [name]` | Start next version cycle |

### Brownfield

| Command | What it does |
|---------|-------------|
| `/gsd:map-codebase [area]` | Analyze existing codebase before new-project |

### Phase Management

| Command | What it does |
|---------|-------------|
| `/gsd:add-phase` | Append phase to roadmap |
| `/gsd:insert-phase [N]` | Insert urgent work between phases |
| `/gsd:remove-phase [N]` | Remove future phase, renumber |
| `/gsd:list-phase-assumptions [N]` | See Claude's intended approach before planning |
| `/gsd:plan-milestone-gaps` | Create phases to close gaps from audit |

### Utilities

| Command | What it does |
|---------|-------------|
| `/gsd:settings` | Configure model profile and workflow agents |
| `/gsd:set-profile <profile>` | Switch model profile |
| `/gsd:add-todo [desc]` | Capture idea for later |
| `/gsd:check-todos` | List pending todos |
| `/gsd:debug [desc]` | Systematic debugging with persistent state |
| `/gsd:quick [--full] [--discuss] [--research]` | Ad-hoc task with GSD guarantees |
| `/gsd:health [--repair]` | Validate .planning/ integrity |
| `/gsd:stats` | Project statistics |
| `/gsd:help` | Show all commands |

## Integration with Claude Code

### Model Profiles

Control which model each agent role uses:

| Profile | Planning | Execution | Verification |
|---------|----------|-----------|-------------|
| `quality` | Opus | Opus | Sonnet |
| `balanced` (default) | Opus | Sonnet | Sonnet |
| `budget` | Sonnet | Sonnet | Haiku |
| `inherit` | Inherit | Inherit | Inherit |

```
/gsd:set-profile quality    # Max quality
/gsd:set-profile budget     # Save tokens
```

### Agent System

GSD uses specialized agents (subagents under the hood):
- **Project Researcher** -- domain ecosystem research
- **Phase Researcher** -- implementation-specific research
- **Planner** -- creates task breakdown with XML plans
- **Plan Checker** -- verifies plans against goals
- **Executor** -- implements plans with atomic commits
- **Verifier** -- checks codebase delivers what phase promised
- **Nyquist Auditor** -- ensures test coverage for requirements
- **Codebase Mapper** -- analyzes existing codebase structure
- **Debugger** -- scientific method debugging with persistent state
- **Research Synthesizer** -- combines parallel research outputs

### Security

Protect sensitive files from GSD's codebase analysis:

```json
// .claude/settings.json
{
  "permissions": {
    "deny": [
      "Read(.env)",
      "Read(.env.*)",
      "Read(**/secrets/*)",
      "Read(**/*credential*)",
      "Read(**/*.pem)"
    ]
  }
}
```

### Combining with Superpowers

GSD + Superpowers is a known power combo:
1. `/brainstorm` (Superpowers) -- clarify requirements
2. `/gsd:new-project` -- create project structure
3. `/write-plan` (Superpowers) -- detailed task breakdown informed by GSD context
4. `/gsd:execute-phase` -- wave-based parallel execution
5. Code review (Superpowers) -- review against plan + CLAUDE.md

Superpowers = better at thinking (brainstorm, plan, review). GSD = better at doing (setup, execution, verification).

## Common Issues

### Context rot still happening
**Cause:** Running too many tasks in one session without `/clear`.
**Fix:** GSD handles this via fresh context per plan in execute-phase. If doing manual work, `/clear` between phases. The whole point is: don't accumulate context.

### Plans are too vague
**Cause:** Skipped discuss-phase, so planner has no context about your preferences.
**Fix:** Run `/gsd:discuss-phase N` before `/gsd:plan-phase N`. The deeper you go in discussion, the more precise the plans.

### Execution fails mid-wave
**Cause:** Dependencies between plans not correctly identified.
**Fix:** Check PLAN.md for `depends_on` fields. Run `/gsd:health --repair` to validate .planning/ integrity. Re-plan if needed.

### map-codebase misses files
**Cause:** Files in deny list or gitignored.
**Fix:** Check `.claude/settings.json` deny list. GSD respects Claude Code's permission model.

### "Balanced" profile uses Sonnet for research
**Cause:** Known issue (#680). Balanced uses Opus for planning but Sonnet for researcher agent.
**Fix:** Use `quality` profile if you need Opus for everything, or configure per-agent via `/gsd:settings`.

## References

- **GitHub**: https://github.com/gsd-build/get-shit-done (30K+ stars, MIT)
- **Docs (Mintlify)**: https://gsd-build-get-shit-done.mintlify.app/
- **npm**: https://www.npmjs.com/package/get-shit-done-cc
- **Deep dive article**: https://medium.com/spillwave-solutions/what-is-gsd-spec-driven-development-without-the-ceremony-570216956a84
- **Medium overview**: https://agentnativedev.medium.com/get-sh-t-done-meta-prompting-and-spec-driven-development-for-claude-code-and-codex-d1cde082e103
- **The New Stack**: https://thenewstack.io/beating-the-rot-and-getting-stuff-done/
- **Codecentric anatomy**: https://www.codecentric.de/en/knowledge-hub/blog/the-anatomy-of-claude-code-workflows-turning-slash-commands-into-an-ai-development-system
- **Superpowers + GSD combo**: https://samanvya.dev/blog/claude-code-superpowers-gsd
- **Reddit discussion**: https://www.reddit.com/r/ClaudeAI/comments/1q4yjo0/get_shit_done_the_1_cc_framework_for_people_tired/
- **Latest release**: v1.24.0 (2026-03-15)
