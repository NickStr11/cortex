---
name: parallel-agents
description: "Dispatch one agent per independent problem domain for concurrent investigation/implementation. Adapted from obra/superpowers."
---

# Dispatching Parallel Agents

Multiple independent problems? One agent per domain, concurrent execution.

## When to Use

- 3+ failures with different root causes
- Multiple independent subsystems to fix/build
- No shared state between tasks (different files, different concerns)

## When NOT to Use

- Failures are related (fix one might fix others)
- Agents would edit same files
- Need to understand full system state first
- Exploratory debugging (don't know what's broken yet)

## Process

### 1. Identify Independent Domains
Group by independence:
- Same root cause → one agent
- Different subsystems → separate agents
- Shared files → sequential, not parallel

### 2. Dispatch Focused Agents

Use Task tool with multiple calls in ONE message (parallel execution).

Each agent gets:
- **Specific problem** — narrow scope
- **Full context** — error messages, test names, relevant code paths
- **Constraints** — "don't change X", "fix only Y"
- **Expected output** — "return summary of root cause and changes"

### 3. Review & Integrate

After all agents complete:
- Review each agent's changes
- Check for conflicts
- Run full test suite
- Integrate if clean

## Good vs Bad Prompts

Bad: "Fix all the tests" → agent gets lost
Good: "Fix 3 failing tests in src/auth/login.test.ts: [specific test names + errors]"

Bad: "Fix the race condition" → no context
Good: [paste error messages, test names, file paths]

Bad: no constraints → agent refactors everything
Good: "Do NOT change production code, fix tests only"

## Example

```
# 6 failures across 3 files after refactoring

Agent 1 → Fix auth/login.test.ts (3 failures, token validation)
Agent 2 → Fix api/orders.test.ts (2 failures, missing mock)
Agent 3 → Fix sync/delta.test.ts (1 failure, race condition)

# All dispatched in single message → parallel execution
# Results: independent fixes, no conflicts, suite green
```
