---
name: verification-dod
description: 'Definition of Done: test evidence, verify agent work.'
metadata:
  category: development
---

# Verification and Definition of Done

AI-generated code must be verified, not trusted.

## Verification Pyramid

```
         ┌──────────┐
         │  Manual  │  ← human review (edge cases, design)
        ├──────────┤
       │ Integration│  ← runtime test
      ├────────────┤
     │   Build check│  ← compile all configurations
    ├───────────────┤
   │  Static analysis│  ← lint, no warnings, null checks
  ├──────────────────┤
 │   Unit / API tests│  ← automated tests
└──────────────────────┘
```

Each level must pass before moving to the next.

## Definition of Done Checklist

### Code level
- [ ] Build succeeds
- [ ] No new warnings
- [ ] Nullable annotations correct
- [ ] Uses project patterns, not raw APIs

### MCP / Tool level
- [ ] Tool runs against real target
- [ ] Error input returns structured error, not crash
- [ ] Interface matches actual parameters
- [ ] Response is DTO, not internal type

### Documentation level
- [ ] Public API documented
- [ ] Known-issues updated
- [ ] Test evidence captured

## GATES.md for Machine-Checkable Verification

For complex features, create a GATES.md with:
- `CHECK:` — command that verifies outcome
- `EXPECT:` — what success looks like in stdout
- `EVIDENCE:` — filled after successful run

See completion-gates skill for full format.

## Test Evidence Pattern

```
## Test evidence: Feature X
### Setup
[Environment, commands to set up]

### Test 1: happy path
[Input, expected output, actual output]

### Test 2: error case
[Input, expected error, actual error]

### Build verification
[Build output]
```

## Verification
- [ ] All levels of pyramid passed
- [ ] Test evidence captured
- [ ] Feature reviewed by human