---
name: revit-reuse-ladder
description: 'Reuse ladder: check 6 rungs before writing code.'
metadata:
  category: process
---

# Reuse Ladder

Pre-code reuse discipline: stop at the first rung that holds before writing any new code.

## When to Use

**Before** writing new code, not after. The whole value is in the first five minutes.

**Triggers:**
- About to create a new file or public symbol
- About to add a new tool, service, helper, or module
- "Optimize" / "improve" / "refactor" something
- You catch yourself writing: Retry, CircuitBreaker, Factory, Base<T>, Manager for the first time in this repo

## The Ladder (stop at the first rung that holds)

```
0. Does this need to exist?          → if not: say so, propose not doing it
1. Existing tool already does it?     → reuse it (or extend its arguments)
2. Existing service/helper/symbol?    → reuse it, don't rewrite
3. Library extension covers it?       → use the extension
4. Compatibility wrapper covers it?   → use the wrapper
5. Base class helper?                 → use the provided helper
6. One line / one expression?         → write one line
7. Only then: the minimum that works
```

Rungs 1-2 catch most duplication. Rungs 3-4 catch most raw-API bugs.
Rung 0 catches most unnecessary work.

## Mandatory RECON Artifact

Before the first write that introduces a new symbol, emit exactly one of:

```
RECON: reuse <symbol> at <file>:<line> — <why it fits>
RECON: extend <tool> argument <arg> instead of new — <why>
RECON: new because <rungs 1-6 all checked and failed, with evidence>
RECON: not needed because <reason> — skip this work
```

If the line is `new because`, it must name what was checked. A declaration of novelty without evidence is the same as no recon.

## What Is Never on the Chopping Block

If a reuse path would skip one of these, the reuse path is wrong:
- Input validation at the boundary
- Transaction / rollback for any write
- Error mapping to readable failure messages
- DTO conversion before data crosses the boundary

## Red Flags
- New file with no RECON line before it
- Re-implementing a library extension inline
- Adding Retry/CircuitBreaker/RateLimiter without accepted spec
- Removing validation/rollback "because the reused path doesn't have it"

## Verification
- [ ] RECON artifact emitted before first new symbol
- [ ] Rung checks cited where novelty claimed
- [ ] No duplicate created for existing behavior
- [ ] Nothing from "never on the chopping block" was cut