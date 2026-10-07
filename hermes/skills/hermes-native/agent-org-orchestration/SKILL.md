---
name: agent-org-orchestration
description: Use when orchestrating a multi-agent org to reach a goal.
metadata:
  category: software-development
---

# Agent Org Orchestration

You are the orchestrator. The unit of work is a **goal**, not a turn: someone states an
outcome, you assemble the staff that can reach it, run them in waves, gate the result,
and accept or reject the product. This skill covers the decisions that shape — and
constrain — that design.

## Step 0 — enumerate your real limits before designing around them

Do not assume your delegation toolset is the ceiling. Get the actual facts:

- **Can a delegated child delegate again?** In Hermes, `delegate_task` children cannot
  call `delegate_task`, `memory`, `clarify`, or `cronjob`. A child asking for a
  sub-agent is not a design detail — it forces the depth of your whole tree.
- **What does a child return?** Only its final summary. Long context inside a child is
  destroyed on return; anything the next step needs must live outside the child.
- **What is parallel, and what is capped?** Note the per-call item cap and whether
  results return inline or between turns.

Write these down as a table of *constraint → what it forbids → what lifts it*. A
constraint you have not named will silently shape the architecture later.

## Step 1 — check whether a service surface already lifts the limit

Before designing a workaround for your own toolset, look for an external surface the
same system already exposes. Delegation depth is the common case: a service that
publishes an agent-call operation over MCP/REST turns a 2-level tree into an
unbounded one, because *you* call the service and the service does the nesting.

- Verify the surface **in config or code**, not from a README: the tool name, its
  parameters, and whether it can select which team/role handles the request.
- A service runtime (sessions, leases, dead-letter queues, idempotency, multi-tenancy)
  and a personal assistant (browser, local files, interactive tooling) occupy
  **different layers**. When asked "keep the project or just use my assistant", the
  answer is usually composition, not replacement — name the layer each occupies.
- Confirm the composition is actually wired: the ability to address a *role* (not just
  a default agent) is what makes it a staff rather than a single worker.

## Step 2 — split decisions from execution, and write the boundary down

State who does what in one table, and make it a file rather than a conversational
agreement: goal and acceptance criteria, staff and limits, execution, enforcement, and
acceptance each get an owner and a location. The invariant worth stating explicitly is
that the orchestrator **never does the work by hand** — it routes and decides.

Without this file the boundary erodes: the moment you hand-write a deliverable to save
time, the org stops being a system and becomes a series of manual interventions.

## Step 3 — put state on disk, not in context

A goal-driven effort outlives one context window. Everything the next step needs lives
in a mission folder — goal and acceptance criteria, org/limits config, artifacts,
gate verdicts, and an append-only decision log. Your own context holds routing only.

Two rules make the difference between a system and a session:

- **One wave = one dispatch call.** Independent items go in a single call, not a
  sequence of one-item calls; a wave is capped by the config's parallel limit.
- **Nothing important lives only in a transcript.** If closing the session loses it,
  it was not state.

## Step 4 — gates receive artifacts, not reports

A reviewer handed a summary reviews the summary. Hand it the diff, the file, the
measurement. A FAIL must be an artifact too — a concrete list of defects — because
"try again" is not a fix instruction and cannot be verified.

A gate is only a gate if its verdict feeds the next iteration. A reviewer invoked as
an ordinary worker produces advice, not control.

## Step 5 — put limits in before autonomy

Sequence the work so the guardrails land first: usage capture, then budget/limits, then
capability contracts, then policy, then review gates, then workspace isolation. The
dependency is not stylistic — a spend limit with no usage capture has nothing to
measure, and a cycle limit with no counter is a wish.

- Make the over-limit action **`stop_and_report`**, with no alternative in the enum.
  Continuing past a limit is spending without control, and that decision belongs to the
  orchestrator, not the worker.
- Prove the limit fires. A guardrail task whose acceptance is "does not error" is
  untested; the test must show the system **stops** on cycle N+1.
- Any field nobody checks at runtime is a declaration, not a control. Either enforce it
  in the same wave or drop it — a config knob that lies is worse than its absence,
  because it reads as a control that works.

## Pitfalls

- **Designing around a toolset limit before checking for a service surface.** You will
  build a shallower system than the environment already permits, and the shortfall gets
  baked into the architecture. Check for the lifting surface first.
- **Reading a delegated child's context as available state.** It returns a summary;
  everything else is gone. Write results to disk at the child's boundary, not after.
- **Making the review phase a step instead of a gate.** Sequential "build, then review"
  with no feedback path produces advice nobody must apply. Wire the verdict back.
- **Treating parallel independence as file-disjointness.** Two workers in different
  files still invalidate each other's verification runs. Serialize heavy validation
  against other work, and re-run the whole battery after the batch lands.
- **Renumbering a shared plan while another agent owns it.** Add a new numbered section
  and leave existing numbering untouched, then cross-link. Renumbering collides with
  in-flight work you cannot see.
- **Skipping the "who verifies this" step because the plan looks done.** A specification
  with acceptance criteria is a claim; the run is the audit.
- **Writing a limits file and calling it a control.** Until the enforcing code lands, it
  is a plan. Label it so in the file and in every report.

## Supporting files

- `references/service-backed-org.md` — probe commands for enumerating delegation limits,
  locating an MCP/REST surface, and the mission-folder + org-config shape that keeps a
  goal-driven effort resumable.
- `references/authoring-org-files.md` — writing the goal doc, ORG config and protocol
  without the corruption and comment-syntax traps, plus the declarative-vs-enforced
  labelling rule.
- `references/shared-task-catalog.md` — extending a `task/`-style catalog that another
  agent may be editing: match its house style, add without renumbering, verify the
  ordering against the code.