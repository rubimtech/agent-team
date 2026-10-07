---
name: task-manager-insights
description: Query and maintain the shared MCP Task Manager via REST.
tags: [task-manager, rest]
metadata:
  category: development
  version: 1
  author: hermes
  license: MIT
  hermes:
    tags: [task-manager, rest]
    related_skills: [task-manager]
---

# Task Manager Inspection Patterns

Procedures for querying and maintaining the shared MCP Agent Task Manager at `$TASK_MANAGER_URL` (default `https://atm.apps.rubim.tech`). Supplements the `task-manager` skill.

## Listing All Tasks

The `limit` parameter caps at **1000**; larger values return a 422. Use `?limit=1000` and filter locally.

```bash
curl -s -m 30 "$TASK_MANAGER_URL/api/tasks?limit=1000"
```

Agents: `GET $TASK_MANAGER_URL/api/agents`.

## Stale In-Progress Detection

After listing tasks, flag any task where:
- `assignee_id` is `Remediation Coordinator (main)` AND `branch` is `main`
- `started_at` is more than a few days old

These hang indefinitely. Report them to the user — do not silently continue them.

## Quick Status Summary

Group tasks by `status`. For today's activity, filter by `created_at` / `completed_at` starting with the current date. Zero completed tasks overall indicates the board is newly populated or has never been closed.