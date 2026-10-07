# Service-Backed Agent Org — probes and layout

Depth for `agent-org-orchestration`. Read when designing the org, or when a delegation
limit appears to cap the tree.

## Enumerate what delegation actually allows

Do not read these off the tool description — verify in the running session.

```bash
grep -nE -A12 "^delegation|max_concurrent|model:|provider:" \
  "$LOCALAPPDATA/hermes/config.yaml" | head -40
```

The three questions that change the architecture:

| Question | If the answer is no |
|---|---|
| Can a delegated child call `delegate_task`? | Tree is 2 levels; a child needing a sub-agent routes through you, costing your context per hop. |
| Can a child set its own model/provider? | "Different models per role" must be done by separate dispatches or by a service that owns model selection. |
| How many items per call, and do results return inline? | Decides wave size and whether you end a turn waiting. |

Where delegation depth is the binding constraint, the escape is a service that nests
agents itself: you call it once, it runs a tree.

## Locate a surface that lifts the limit

Search the service for an agent-invocation operation — MCP server tools, REST routes, or
a CLI entrypoint:

```bash
# MCP tools published by a service
grep -rnE "name=\"[a-z]+\.[a-z]+\"|@server\.tool|def _chat" <src>/mcp/

# REST routes
grep -rnE "@(app|router)\.(post|get)\(" <src>/api/

# Which role handles it — a role/orchestrator parameter is what makes it a staff
grep -rnE "orchestrator|agent_name|role" <src>/api/ <src>/mcp/
```

Three properties decide whether the surface is usable as an org layer:

1. **Role selection.** A parameter choosing which team handles the request. Without it
   you have one worker, not a staff.
2. **Nested depth.** Whether the callee can itself delegate. This is what converts your
   2-level tree into an unbounded one.
3. **State retention.** Whether the callee persists context across calls, so a mission
   can resume in a later session.

## Layout that survives a context window

```
<missions-root>/<slug>/
├── GOAL.md        outcome + acceptance criteria + explicit non-goals
├── ORG.yaml       staff, roles, limits (see below)
├── artifacts/     requirements, specs, decisions, code, reports
├── gates/         <NN>-<role>-<verdict>.md — PASS/FAIL plus defect list
└── LOG.md         append-only: one line per decision, never rewritten
```

Fill the goal **before** hiring anyone. No acceptance criteria, no staff — otherwise the
gate at the end has nothing to check and "looks good" becomes the criterion.

### ORG.yaml shape

Departments map to an existing role selector (the service's orchestrator/agent name),
not to new machinery:

```yaml
departments:
  research: {orchestrator: research, role: "Establish what is needed"}
  design:    {orchestrator: design,    role: "Write spec + acceptance criteria"}
  build:     {orchestrator: build,     role: "Implement"}
  qa:        {orchestrator: qa,        role: "Review and test, emit verdict"}

limits:
  max_hire: 12
  max_parallel_runs: 5
  max_cycles: 6                  # review -> fix; stop after the Nth failure
  max_tokens_project: 500000
  deadline_minutes: 240

on_limit:
  cycles: "stop_and_report"      # enum with no alternative, by design
```

Roles carry skills, capabilities, autonomy, and a per-agent iteration cap:

```yaml
roles:
  coder:    {capabilities: [code.write, code.execute, tests.run], autonomy: execute, max_iterations: 10}
  reviewer: {capabilities: [fs.read], autonomy: readonly}   # must not write code
```

Mark such a file as **declarative** until an enforcing task lands. A limits block the
service reads but does not enforce is a plan, not a control — say which it is in the
file, and never let a report imply enforcement that does not exist yet.

## Wave template

| Wave | Who | In | Out | Gate |
|---|---|---|---|---|
| W0 Research | analyst, researcher | GOAL | requirements artifact | enough for a spec? |
| W1 Design | architect(s), disagreeing | requirements | spec + criteria | criteria verifiable? |
| W2 Build | N implementers in parallel, each isolated | spec | patches/artifacts | tests green? |
| W3 Review | reviewers, testers | **patches, not reports** | PASS/FAIL + defects | — |
| W4 Fix | refactorer/amender hired on demand | FAIL defects | new version | re-gate |
| W5 Accept | orchestrator | all of it | product verdict | — |

W3→W4 loops and is bounded by `max_cycles`. Hitting the bound is a **report**, not a
silent success and not another attempt.

A designer wave earns its keep only when the participants must **disagree**: give each a
mandate to refute the others' proposals, and record one verdict. Several agents agreeing
is not convergence; without an adversarial mandate you have a chorus, and the cheapest
way to get real convergence is to require each participant to attack the others.