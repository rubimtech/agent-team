---
name: task-manager
description: 'MCP Task Manager: claim, report, complete tasks.'
metadata:
  category: development
---

# MCP Agent Task Manager — Agent Workflow

You are one executor in a shared task management system (MCP Agent Task Manager). Tasks are created by humans or other agents; agents claim, execute, and close them.

## Agent Identity

1. Use a **stable name** for your role (e.g. `tool-role`)
2. Get `agent_id`:
   - Find yourself via GET /api/agents
   - Or register: register_agent(name=..., description=..., capabilities=[...])
3. ID is persistent — reuse across sessions

## Typical Work Cycle

1. **Look for tasks** — `list_free_tasks` (filter by repo/branch/tags)
2. **Claim a task** — `claim_task(agent_id, task_id)` (pending → in_progress)
3. **Work in your branch** — send heartbeats and progress reports
4. **Commit before completing** —
   ```bash
   git add -A
   git commit -m "task <task_id>: <description>"
   ```
5. **Complete the task** — `complete_task(agent_id, task_id, result=<what was done + sha>, actual_minutes=<time>)`
   Or `submit_for_review` if human review is needed
6. **Can't continue?** — `release_task` (back to pending) or report blocker

## How to Create Tasks

- Decompose large goals into specific tasks for parallel work
- `create_task(agent_id, title, description, priority, tags, dependencies?)`
- Give enough context: repo, branch, dependencies, acceptance criteria
- Watch dependencies and scope — don't overlap files

## Rules (Brief)
- **No overlap**: claimed task is yours until complete/release
- **Commit before complete_task**: result must be in git
- **Don't go idle**: heartbeat and progress on long tasks
- **Write for humans**: result describes what, where, and commit SHA

## REST Fallback

If no MCP tools available, use REST at `$TASK_MANAGER_URL` (default `https://atm.apps.rubim.tech`):
| Action | Request |
|---|---|
| Find/register self | GET /api/agents, POST /api/agents |
| Create task | POST /api/tasks |
| Free tasks | GET /api/tasks?status=pending |
| Claim | POST /api/tasks/{id}/claim |
| Complete | POST /api/tasks/{id}/complete |