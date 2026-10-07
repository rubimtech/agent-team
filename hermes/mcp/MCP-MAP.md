# MCP-серверы команды: откуда, как поднять, как проверить

Блоки для вставки в `config.yaml` профиля лежат рядом:
`mcp-servers.full.yaml` (9 серверов — оркестратор, архитектор, дев, QA) и
`mcp-servers.reviewer.yaml` (7 — ревьюер, без `ui` и `ssh`).

В экспорте пути записаны плейсхолдерами (`{{REPO}}`, `{{HERMES_HOME}}`, `{{LOCALAPPDATA}}`,
`{{HARNESS_PLUGINS}}`, `{{KNOWLEDGEBASE_MCP}}`, `{{SSH_MCP}}`) — их подставляет
`scripts/apply_team.py`. Сервер, чьи пути не разрешились, скрипт помечает `enabled: false`
и перечисляет в отчёте: не выдумывать путь, а доустановить зависимость.

| Сервер | Транспорт | Источник | Как поднять | Проверка |
|---|---|---|---|---|
| `cgc` | HTTP/SSE `http://127.0.0.1:8104/api/v1/mcp/sse` | `{{HARNESS_PLUGINS}}/CodeGraphContext` (docker) | `cd {{HARNESS_PLUGINS}} && docker compose --profile cgc up -d codegraphcontext` | `curl -s http://127.0.0.1:8104/openapi.json` → `CodeGraphContext Gateway` |
| `qdrant-kb` | stdio: `node --experimental-transform-types {{HARNESS_PLUGINS}}/memory-store/src/qdrant-kb.ts` | `{{HARNESS_PLUGINS}}/memory-store` | нужен Qdrant на `127.0.0.1:6333` + `MEMORY_QDRANT_URL` | `hermes -p <бот> mcp test qdrant-kb` → 4 тула (`kb_search`, `kb_fetch`, `kb_collection_health`, `kb_get_points`) |
| `knowledgebase` | stdio: `{{KNOWLEDGEBASE_MCP}}/.venv/Scripts/python.exe {{KNOWLEDGEBASE_MCP}}/launch_mcp.py` | `{{KNOWLEDGEBASE_MCP}}` | `python -m venv .venv && .venv/Scripts/pip install -r requirements.txt` | `hermes -p <бот> mcp test knowledgebase` → 9 тулов |
| `memory-store` | stdio: `node … memory-store/src/mcp-server.ts` | `{{HARNESS_PLUGINS}}/memory-store` | переменные `MEMORY_ONNX_DIR` (bge-m3 ONNX), `MEMORY_QDRANT_URL`, `MEMORY_COLLECTION` | `hermes -p <бот> mcp test memory-store` → 9 тулов |
| `task_manager` | HTTP `https://atm.apps.rubim.tech/mcp` | внешний сервис | ничего ставить не нужно; проверить, что хост отвечает | `curl -s -o /dev/null -w "%{http_code}" https://atm.apps.rubim.tech/api/agents` → 200 |
| `revit` | stdio: `{{REPO}}/.kilo/scripts/mcp-revit-bridge.cmd` | репозиторий (мост `tools/RevitMcpStdioBridge`) | **запустить Revit** с загруженным плагином ReVibe (`deploy-isolated.ps1`). Альтернатива для чужих клиентов — `.kilo/scripts/setup-mcp-bridge.ps1 -Client all` | `hermes -p <бот> mcp test revit` → тулы `capability_*`, `dll_list/dll_load/dll_reload/dll_unload`, `code_runner_*` |
| `ui` | stdio: `{{LOCALAPPDATA}}/UiController/RevitUiController.McpServer.exe` | `.kilo/scripts/ui-setup.ps1` | `powershell -ExecutionPolicy Bypass -File .kilo/scripts/ui-setup.ps1` (стационарно `-Flavour Portable`), демон стартует при входе | `hermes -p <бот> mcp test ui` → `ui_state`, `ui_invoke`, `ui_ribbon_find`, `revit_api` … |
| `excel` | stdio: `{{HERMES_HOME}}/bin/uvx.exe excel-mcp-server stdio` | Hermes (uvx) | `uvx` идёт с Hermes; переменная `EXCEL_FILES_PATH` | `hermes -p <бот> mcp test excel` |
| `ssh` | stdio: `{{LOCALAPPDATA}}/Programs/Python/Python311/python.exe {{SSH_MCP}}/mcp_server.py` | `{{SSH_MCP}}` | venv + `servers.yaml` с хостами | `hermes -p <бот> mcp test ssh` |

## Три разных статуса «сервер доступен»

1. **Сервер жив** — доказано вызовом (HTTP/stdio вернул тулы).
2. **Сервер подключён к боту** — есть блок в `config.yaml` профиля и `hermes -p <бот> mcp list` показывает `enabled`.
3. **Инструмент получен** — бот реально вызвал тул в сессии (только это и считается доказательством).

## Особенности, которые ломают настройку

- **`connect_timeout` у stdio-серверов должен быть коротким** (в блоке: `revit` 20 с, `ui` 45 с,
  остальные 60–90 с). Любой CLI-вызов профиля (`hermes -p X config set|mcp list|chat`) поднимает
  **все** его MCP-серверы; недоступный сервер с длинным таймаутом превращает каждую команду в
  многоминутное ожидание (а с живым мостом Revit — в зависание). Поэтому роль-настройки
  (`model`, `skills`, `terminal`, `agent`, `delegation`, `memory`) `apply_team.py` пишет прямо
  в `config.yaml`, а не через `hermes config set`; `verify_team.py` при этом проверяет
  отсутствие дублирующихся ключей верхнего уровня.
- **Профили не наследуют `mcp_servers` активного профиля.** Прописывать каждому боту отдельно
  (это и делает `apply_team.py`), иначе сессия честно сообщает «No MCP servers configured».
- **`hermes mcp add --url` интерактивен** — спрашивает про auth и виснет без PTY. Поэтому блок
  пишется в `config.yaml` напрямую, а проверяется через `hermes -p <бот> mcp list`.
- **Дефис в имени сервера → подчёркивание в имени тула:** `qdrant-kb` → `mcp__qdrant_kb__kb_search`.
  Ботам это сказано в SOUL: искать через `tool_search`, а не угадывать имя.
- **Пути с бэкслешами** в `hermes mcp add --env` съедаются — писать значения через `/`.
- **`revit` поднимается только когда Revit запущен**: мост сам находит живой инстанс и переживает
  перезапуск, но без Revit тулов в сессии нет (это ожидаемо, а не поломка конфига).
- **`ui` → `revit_api`** требует, чтобы демон держал окно Revit (`ui_connect` / `ui_list_apps`);
  `Not connected … open sessions: 0` означает «Revit закрыт», а не «MCP сломан».
