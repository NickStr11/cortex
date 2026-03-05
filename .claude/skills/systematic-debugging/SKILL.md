---
name: systematic-debugging
description: "Use when encountering any bug, test failure, or unexpected behavior. 4-phase root cause analysis before fixes. Adapted from obra/superpowers."
---

# Systematic Debugging

**Iron Law: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

## When to Use

Any bug, test failure, unexpected behavior, error message. Do NOT skip because bug "looks simple" or you "think you know".

## Phase 1: Root Cause Investigation

1. **Read full error** — every word, file names, line numbers, expected vs actual
2. **Reproduce** — run failing test/code, confirm same error
3. **Check recent changes** — `git log`, `git diff`, when did it start?
4. **Trace data flow** — where data originates, transforms, diverges from expected
5. **Add evidence gathering** — logging/debug output at key points. NO FIXES YET.
6. **Document** — "Error X at line Y", "Data entering A, exiting B", "Started after commit Z"

## Phase 2: Pattern Analysis

1. **Find working examples** — similar code that works in same codebase
2. **Compare** — what's different between working and broken? List ALL differences
3. **Understand dependencies** — config, environment, assumptions

## Phase 3: Hypothesis & Testing

1. **Form single hypothesis** — "X is root cause because Y" (be specific)
2. **Test minimally** — smallest possible change, one variable at a time
3. **Verify** — worked? → Phase 4. Didn't? → new hypothesis. Don't stack fixes.

## Phase 4: Implementation

1. **Failing test first** — reproduces the bug
2. **Minimal fix** — only what root cause requires. No refactoring, no "improvements"
3. **Verify** — failing test passes, full suite green, original symptom gone
4. **Cleanup** — remove debug code

### Phase 4.5: When 3+ Fixes Failed

STOP. Question the architecture:
- Is the fundamental approach correct?
- Re-read reference implementation from scratch
- Is there a simpler way?
- Am I fighting the framework?

## Red Flags — STOP and Return to Phase 1

- "Quick fix for now, investigate later"
- "Just try changing X"
- "I don't fully understand but this might work"
- Proposing solutions before tracing data flow
- Each fix reveals new problem in different place
- 3+ failed attempts → question architecture (Phase 4.5)
