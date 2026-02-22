---
name: skill-creator
description: Guide for creating effective skills. Use when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations.
disable-model-invocation: true
---

# Skill Creator

Create modular, self-contained skills that extend Claude's capabilities.

## Core Principles

### 1. Conciseness
- Context window is a shared resource — every token counts
- Include only what Claude doesn't already know
- Prefer concise examples over verbose explanations

### 2. Degrees of Freedom
- **High** (text guidelines): multiple valid approaches, creative tasks
- **Medium** (pseudocode/parameterized scripts): preferred patterns exist
- **Low** (exact scripts): operations are fragile, consistency critical

### 3. Progressive Disclosure
1. **Metadata** (name + description) — always in context (~100 words)
2. **SKILL.md body** — when skill triggers (<5k words, under 500 lines)
3. **Bundled resources** — loaded as needed by Claude

## Skill Structure

```
skill-name/
├── SKILL.md           # Required — frontmatter + instructions
├── scripts/           # Executable code (Python/Bash)
├── references/        # Docs loaded into context as needed
└── assets/            # Files used in output (templates, icons)
```

## Creation Process

### Step 1: Understand the Skill

Ask the user:
- What functionality should this support?
- What are 2-3 concrete usage examples?
- What should trigger this skill?
- Should only the user invoke it (`disable-model-invocation: true`) or Claude too?
- Should it run inline or in a subagent (`context: fork`)?

### Step 2: Plan Reusable Contents

For each usage example, identify:
- **Scripts**: deterministic operations, repeated code generation
- **References**: domain docs, API specs, schemas
- **Assets**: templates, icons, fonts for output

### Step 3: Create the Skill

Initialize the directory:
```bash
mkdir -p .claude/skills/<skill-name>/scripts
mkdir -p .claude/skills/<skill-name>/references
mkdir -p .claude/skills/<skill-name>/assets
```

### Step 4: Write SKILL.md

**Frontmatter** (between `---` markers):

```yaml
---
name: skill-name
description: What it does + when to use it. This drives auto-triggering.
disable-model-invocation: true    # optional: manual-only
user-invocable: false              # optional: Claude-only
allowed-tools: Read, Grep, Bash   # optional: restrict tools
context: fork                      # optional: run in subagent
agent: Explore                     # optional: subagent type
model: sonnet                      # optional: model override
---
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No | Display name, becomes `/slash-command`. Lowercase, hyphens, max 64 chars. Falls back to directory name. |
| `description` | Recommended | What + when. Claude uses this to decide auto-triggering. |
| `argument-hint` | No | Shown in autocomplete: `[issue-number]`, `[filename]` |
| `disable-model-invocation` | No | `true` = only user can invoke via `/name` |
| `user-invocable` | No | `false` = hidden from `/` menu, Claude-only |
| `allowed-tools` | No | Tools allowed without permission prompts |
| `context` | No | `fork` = run in isolated subagent |
| `agent` | No | Subagent type when `context: fork` (`Explore`, `Plan`, custom) |
| `model` | No | Model override for this skill |

**Body**: Write clear instructions in imperative form. Reference bundled resources.

**Variables available**:
- `$ARGUMENTS` — all args passed to skill
- `$ARGUMENTS[N]` or `$N` — specific arg by index
- `${CLAUDE_SESSION_ID}` — current session ID
- `` !`command` `` — shell command output injected before Claude sees content

### Step 5: Implement Resources

- Write scripts, test them by running
- Write reference docs, keep them focused
- Delete unused example directories

### Step 6: Validate

Check:
- [ ] SKILL.md exists with valid YAML frontmatter
- [ ] `name` is lowercase-hyphenated, max 64 chars
- [ ] `description` includes "when to use"
- [ ] SKILL.md body < 500 lines
- [ ] No auxiliary files (README, CHANGELOG)
- [ ] References max 1 level deep from SKILL.md
- [ ] Scripts are executable and tested

## Design Patterns

### Pattern A: Reference content (inline)
For conventions, style guides, domain knowledge:
```yaml
---
name: api-conventions
description: API design patterns for this codebase
---
When writing API endpoints:
- Use RESTful naming
- Return consistent error formats
```

### Pattern B: Task content (manual invoke)
For deployments, commits, generation:
```yaml
---
name: deploy
description: Deploy to production
disable-model-invocation: true
context: fork
---
Deploy $ARGUMENTS to production:
1. Run tests
2. Build
3. Push to target
```

### Pattern C: Research in subagent
```yaml
---
name: deep-research
description: Research a topic thoroughly
context: fork
agent: Explore
---
Research $ARGUMENTS:
1. Find relevant files
2. Analyze code
3. Summarize with file references
```

### Pattern D: Dynamic context injection
```yaml
---
name: pr-summary
description: Summarize PR changes
context: fork
allowed-tools: Bash(gh *)
---
PR diff: !`gh pr diff`
PR comments: !`gh pr view --comments`
Summarize this pull request.
```

## Where to Store

| Scope | Path | Applies to |
|-------|------|------------|
| Personal | `~/.claude/skills/<name>/SKILL.md` | All your projects |
| Project | `.claude/skills/<name>/SKILL.md` | This project only |

## Tips

- Include "ultrathink" in content to enable extended thinking
- Use `context: fork` only for skills with explicit tasks, not guidelines
- Keep description actionable — it's the primary trigger for auto-invocation
- Challenge every line: does Claude need this to succeed?
