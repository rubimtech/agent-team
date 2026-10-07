# Contributing to a Shared Task Catalog

Depth for `agent-org-orchestration`. When the goal is large enough to have a task catalog
(`task/todo/T##-*.md` plus a roadmap), you will be asked to extend it. Another agent or
the user may be editing the same catalog at the same time.

## Read the existing tasks as a specification, not a wishlist

Each task file carries a header block (phase, wave, dependencies, code zone, references)
and an acceptance section. Read several before writing one — the catalog's own house
style is the fastest way to match it.

Conventions worth adopting when they appear:

- **A header block naming the exact code zone** (paths, new files) and the reference
  material. This is what makes a task executable by a subagent with no extra context.
- **Acceptance as observable facts**, not "works correctly": isolation holds for foreign
  ids, config without the new section reproduces old behaviour, an unchanged input
  yields an unchanged output.
- **An out-of-scope section.** Naming what a task deliberately does not do is what stops
  the implementer from ballooning it.
- **A rationale block** explaining what was removed from a previous draft and why. This is
  the most valuable part of the file: it records a decision so the next author does not
  re-litigate it.
- **A return condition on deferred work** — what event brings the task back into scope.

## Check whether the ordering already accounts for your dependency

The catalog's wave table is a dependency graph. Before proposing an order, verify the
foundation the feature needs actually lands first, and check the code — a task can be
scheduled before the thing it depends on is instrumented.

If you find a task ordered before its own prerequisite, say so with the evidence (a grep
count, a missing hook) rather than silently reordering. The reorder is the maintainer's
call; the observation is yours.

## Concurrent editors: write beside, not into

When another agent owns part of the catalog:

- **Do not renumber.** Wave codes and task ids are referenced from headers, dependency
  blocks and the roadmap table. Inserting your tasks as a new numbered section and
  leaving existing numbering untouched avoids collisions with in-flight work you cannot
  see.
- **Keep your additions in files you own** where the layout allows it, so a conflict is
  impossible rather than unlikely.
- **Fix counters you invalidate.** Adding two tasks to a catalog whose header says "13
  tasks" leaves a document that lies; update the count in the same edit.
- **Re-read the file after patching.** An edit tool can report a clean diff while
  touching lines you did not target; verify the specific hunks you care about and check
  the diff for foreign changes before moving on.

## When the catalog's plan is better than your draft

Say so plainly, and merge into it rather than adding a rival plan. If an existing task was
narrowed for a stated technical reason, respect the narrowing and put your broader need
in a new task with its own dependencies — two documents describing one component is how
one of them goes stale unnoticed.