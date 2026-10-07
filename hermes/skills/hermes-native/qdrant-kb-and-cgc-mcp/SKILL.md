---
name: qdrant-kb-and-cgc-mcp
description: 'Use when searching the Qdrant KB or code graph via MCP.'
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Qdrant, MCP, semantic-search, CodeGraphContext, FalkorDB, bge-m3]
    related_skills: [qdrant, adopting-external-mcp-servers]
---

# Qdrant KB + CodeGraphContext MCP

Two search backends live in this setup. Both are registered as Hermes MCP servers
(`qdrant-kb`, `cgc`); their tools appear in a NEW session, not the one that added them.

## qdrant-kb — semantic search over named Qdrant collections

`memory-store` only reads its own `agent_memory` and derived `ws-*` code collections.
Everything else — `revit_api_knowledge`, `navisworks_api_bge`, `pyRevit_Projects_Nice3point`,
`archicad_api_29`, `revit_api`, `Revit_SDK_Samples` — needs `qdrant-kb`.

Tools: `kb_collection_health`, `kb_search`, `kb_fetch`, `kb_get_points`.
Start with `kb_collection_health`; it reports per-collection point counts and whether the
embedder can serve it.

### The calibration gate — why a collection may be refused

`kb_search` refuses a collection whose vectors were not produced by its bge-m3 embedder,
because searching it returns ranked noise that looks like a real answer. The gate is
**self-retrieval**, not self-cosine:

- Take real points, build a query from the point's own text, search its own collection.
- Pass requires median top-1 >= 0.5 AND >= 50% of probes find their own text in top-5.

Two traps that produced false verdicts while building this:

1. **Do NOT gate on self-cosine** (re-embed one payload field, compare to the stored
   vector). The indexer embeds a whole chunk, so re-embedding a single field compares two
   different texts. `revit_api_knowledge` measured 0.78 that way and was nearly written off
   as a foreign model, while its actual top hits were dead-on at 0.61–0.72.
2. **Match self-retrieval on payload TEXT, not point id.** These corpora hold near-duplicate
   points, so a correct search legitimately returns a different id with identical content.
   The id-based check scored `revit_api_knowledge` 2/5 and would have written off a healthy
   collection.

Measured outcome: the six Revit/Navisworks/ARCHICAD/pyRevit collections all pass
(median top-1 0.85–1.0). `price_products` FAILS at median top-1 0.36 — it was indexed by
price_parser with `multilingual-e5-large`, not bge-m3. It stays in the catalog on purpose so
health reports it as not servable instead of the catalog looking complete while silently
omitting the price corpus.

### Node 26 ломает запуск обоих серверов

`node` в PATH Hermes — node **26.7.0**, в котором **удалён флаг
`--experimental-transform-types`**: процесс умирает на старте с `bad option:
--experimental-transform-types`, сервер лежит в `parked`, tools не появляются ни в
одной новой сессии. Симптом в `logs/mcp-stderr.log`: `node.EXE: bad option:
--experimental-transform-types` рядом с `starting MCP server 'qdrant-kb'|'memory-store'`.

Фикс — через `hermes config set` (сам `patch` по config.yaml блокируется охранителем):

```
hermes config set mcp_servers.memory-store.command "C:/Users/olegs/AppData/Local/hermes/node/node"
hermes config set mcp_servers.qdrant-kb.command    "C:/Users/olegs/AppData/Local/hermes/node/node"
```

Node 22 (`.../hermes/node/node`) принимает флаг и соответствует ABI нативных
модулей. Node 24 (`C:/Program Files/nodejs/node`) флаг принимает, но `better-sqlite3`
скомпилирован под NODE_MODULE_VERSION 127 (= node 22) и на 24 падает с
`was compiled against a different Node.js version`. Проверка после фикса:
`hermes mcp test memory-store` → `Tools discovered: 9`, `hermes mcp test qdrant-kb`
→ `Tools discovered: 4`.

### Registering it again / debugging

Source: `D:/DEV/harness-plugins/memory-store/src/qdrant-kb.ts`, run with
`node --experimental-transform-types` (node 22!). `MEMORY_ONNX_DIR` defaults in-code to
`C:\Users\olegs\AppData\Local\hermes\models\bge-m3-onnx`; `hermes mcp add`'s repeated
`--env` flags overwrite each other, so an env-only path does not survive into config.yaml
and every search then fails with "No local ONNX model found" while the server still lists
its tools.

Probe outside Hermes before blaming config:
`cd D:/DEV/harness-plugins/memory-store && MEMORY_QDRANT_URL=http://localhost:6333 node --experimental-transform-types test/probe-kb-e2e.ts`

## cgc — CodeGraphContext over FalkorDB (graph queries)

Container `harness-plugins-codegraphcontext-1`, port 8104, graph `codegraph`, backed by
FalkorDB. Start it with `cd D:/DEV/harness-plugins && docker compose --profile cgc up -d
codegraphcontext`. 29 tools, including `find_code`, `analyze_code_relationships`,
`execute_cypher_query`, `find_dead_code`, `calculate_cyclomatic_complexity`,
`list_indexed_repositories`.

### Container paths, not host paths

`D:/DEV` is mounted read-only at `/repos`, and `CGC_ALLOWED_ROOTS` must be `/repos` — the
sandbox compares the caller's path string literally, so a host path in that variable rejects
every request with "outside the allowed roots". Index as `repo_path: "/repos/<Project>"`.

### DEFAULT_DATABASE must be `falkordb-remote`, and NOT set in compose

This is the single most expensive trap here. Plain `DEFAULT_DATABASE=falkordb` selects the
LOCAL unix-socket backend, so `cgc index` in the CLI dies with
`Error 2 connecting to .../global/db/falkordb.sock. No such file or directory` — while the
HTTP API on port 8104 keeps working happily over TCP against the real FalkorDB. Two working
paths, two different databases, no error that points at the cause.

Fix: `cgc config set DEFAULT_DATABASE falkordb-remote` (persists in the `cgc-data` volume)
AND remove `DEFAULT_DATABASE` from the compose `environment:` block — an env var there
shadows the `.env` value, and compose wins. Confirm with
`docker logs ... | grep "Using database"`, which must say `falkordb-remote (source:
/home/cgc/.codegraphcontext/.env)`.

Note the data consequence: switching backends does NOT migrate the graph. The old local
`global/db/falkordb` file keeps its contents while the TCP graph reads as empty, so
re-index both repos after the switch.

### Cypher through this gateway: use DOUBLE quotes

String literals with SINGLE quotes fail with a bare "An unexpected error occurred while
executing the query":

- `WHERE f.lang = 'python'` -> error
- `WHERE f.lang = "python"` -> works
- `WHERE f.name =~ '.*x.*'` -> error

So `CONTAINS` and `STARTS WITH` are unavailable; filter with `=` on an exact name and
paginate. This is a quoting/escaping limitation in the gateway, not FalkorDB.

### Indexing is not instant, and .NET repos stall without bin/obj ignored

`add_code_to_graph` reports `processed_files: 0` for minutes while working — check
`get_repository_stats` or the node counts rather than trusting the job counter. If the job
never progresses, run the CLI inside the container, which shows real errors:

`docker exec harness-plugins-codegraphcontext-1 cgc index /repos/<Project>`

Python repos index in ~60s. **C# needs the build dirs ignored first.** The stock
`IGNORE_DIRS` has `dist`/`build` but NOT `bin`/`obj`, and UiController carries 1.7 GB of
committed build output (`dist` 750M, `bin` 253M, per-project publish dirs ~250M each).
Indexing it ran >16 min at 100% CPU, produced zero C# nodes, and starved the API — a
`cgc config set IGNORE_DIRS "...,bin,obj"` plus a container restart took it from
"unresponsive" to a normal run.

Read the value back after setting it (`grep IGNORE_DIRS /home/cgc/.codegraphcontext/.env`);
it lives in the `cgc-data` volume and survives restarts.

If a run wedges the container (API stops answering, CPU pegged), restart it —
`docker compose --profile cgc restart codegraphcontext` keeps the config volume, and the
partially-written graph stays queryable.

Node counts are misleading after an interrupted run, and so are `lang` filters. `File` nodes
carry only `[path, name, is_dependency]` — NO `lang` property — so
`WHERE f.lang = "csharp"` returns 0 and looks like "C# indexing produced nothing" when the
files are actually there. Count per repository instead:

`MATCH (r:Repository {name: "UiController"})-[:CONTAINS*1..3]->(n:Function) RETURN count(n) AS c`

A healthy UiController index holds 266 File and ~900 Function nodes. Note that
`CONTAINS*1..3` is needed to reach symbols; a plain `MATCH (n:Function)` returns Python only.

## Verifying a change here

Quote real numbers, never the tool's own success flag: `kb_collection_health` calibration
medians, a Cypher node/edge count, or a named `kb_search` hit with its score.