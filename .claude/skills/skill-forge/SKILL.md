---
name: skill-forge
description: "Create a new Claude Code skill from any topic. Uses Exa to research context, then generates a ready-to-use SKILL.md. Usage: /skill-forge <topic>"
---

# Skill Forge

Generate a Claude Code skill from scratch by researching a topic via Exa and building a context-rich SKILL.md.

## Input

`$ARGUMENTS` — topic or task description. Examples:
- "WireGuard VPN setup on Ubuntu"
- "Playwright E2E testing patterns"
- "FastAPI + SQLAlchemy async CRUD"
- "Kubernetes pod debugging"

## Process

### Step 1: Parse Intent

Extract from `$ARGUMENTS`:
- **skill_name**: short kebab-case slug (e.g. `wireguard-setup`)
- **domain**: what area (infra, backend, frontend, devops, data, etc.)
- **search_queries**: 2-3 targeted search queries for Exa

### Step 2: Research via Exa

Run **all searches in parallel** (single message, multiple tool calls):

```
# Broad context — guides, tutorials, best practices
mcp__exa__web_search_exa(query="<topic> guide best practices 2025 2026", numResults=10)

# Code examples — real implementations
mcp__exa__get_code_context_exa(query="<topic> implementation examples", tokensNum=8000)

# Troubleshooting — common pitfalls
mcp__exa__web_search_exa(query="<topic> common mistakes troubleshooting", numResults=5)
```

### Step 3: Distill Knowledge

From search results, extract:
- **Core concepts** — what the user MUST know
- **Step-by-step procedure** — concrete commands/code
- **Code snippets** — working examples (verified from multiple sources)
- **Common pitfalls** — what breaks and how to fix it
- **Tool-specific flags/options** — exact CLI args, config keys

**Rules:**
- NO generic advice ("make sure to test"). Only specific, actionable content.
- Include exact commands, exact config snippets, exact code.
- If sources disagree — note both approaches with trade-offs.
- Prefer 2025-2026 sources over older ones.

### Step 4: Generate SKILL.md

Write to `.claude/skills/{skill_name}/SKILL.md`:

```markdown
---
name: {skill_name}
description: "{one-line description of what this skill enables}"
---

# {Title}

## When to Use
{1-3 bullet points — trigger conditions}

## Prerequisites
{What must be installed/configured before using this skill}

## Procedure
{Numbered steps with exact commands and code blocks}

## Code Templates
{Ready-to-use code snippets — copy-paste ready}

## Common Issues
{Problem → Cause → Fix format, 3-5 entries}

## References
{URLs of the best sources found during research}
```

### Step 5: Confirm

- Show the user the generated skill path
- Show key stats: N sources researched, N code examples included
- Suggest: "Try it: describe a task related to {topic} and I'll use the new skill"

## Quality Gates

- Skill MUST have at least 3 concrete code blocks
- Skill MUST have at least 3 common issues with fixes
- No placeholder text ("TODO", "add here", "customize this")
- Every command must include flags/args that matter
- Test: could someone with zero knowledge of the topic follow the skill and succeed?

## Example Output Structure

```
.claude/skills/wireguard-setup/
  SKILL.md          # The generated skill
```

Single file. No extra scaffolding. The skill IS the knowledge.
