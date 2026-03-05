---
name: subagent-dev
description: "Execute implementation plans via fresh subagent per task + two-stage review (spec compliance → code quality). Adapted from obra/superpowers."
---

# Subagent-Driven Development

Fresh subagent per task + two-stage review = high quality, fast iteration.

## When to Use

- Have a plan with independent tasks
- Want quality gates between tasks
- Tasks can be implemented sequentially in current session

## Process

### 1. Load Plan
Read plan once, extract ALL tasks with full text and context.

### 2. For Each Task

**a) Dispatch implementer subagent** (Task tool, subagent_type=general-purpose):
- Provide FULL task text (don't make subagent read plan)
- Include context: what project, what we're building, where this fits
- If subagent asks questions → answer, re-dispatch

**b) Spec compliance review** (Task tool, subagent_type=code-reviewer):
- Input: original spec text + what was implemented
- Check: implemented everything required? Added anything not requested?
- If issues → implementer fixes → re-review → repeat until clean

**c) Code quality review** (Task tool, subagent_type=code-reviewer):
- ONLY after spec compliance passes
- Check: code quality, patterns, maintainability
- If issues → implementer fixes → re-review → repeat until clean

**d) Mark task complete**

### 3. After All Tasks
Run full test suite, verify everything works together.

## Rules

- Fresh subagent per task (no context pollution)
- Spec compliance BEFORE code quality (right order)
- Never skip reviews
- Never start on main branch without user consent
- Don't let implementer self-review replace actual review
- If subagent fails → dispatch fix subagent, don't fix manually

## Prompt Template for Implementer

```
Context: [project name], [what we're building]
Tech: [stack]

Task: [full task text from plan]

Files to touch:
- [exact paths]

Requirements:
1. Follow TDD: failing test → implementation → green
2. Commit after each logical unit
3. Run tests before declaring done

Return: summary of changes + test results
```
