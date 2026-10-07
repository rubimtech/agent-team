# Промт развёртывания команды ботов RevitAiTools

> **Как этим пользоваться:** скопируй этот файл целиком в новый чат Hermes на новой машине
> (или скажи агенту: «выполни `agent-team/BOOTSTRAP-PROMPT.md` из репозитория RevitAiTools»).
> Агент обязан проверить, чего не хватает, установить/подключить это и отчитаться.

---

## Задача

В репозитории `RevitAiTools` (корень — тот, где лежит каталог `agent-team/`) есть экспорт команды
из 5 Hermes-ботов: `revit-orchestrator`, `revit-pm`, `revit-ai-dev`, `revit-qa-tester`,
`revit-code-reviewer`. Нужно развернуть её на этой машине так, чтобы полный цикл разработки
(приём задачи → требования → код → сборка → тест в живом Revit → ревью) работал, и чтобы боты
имели доступ к репозиторию, скиллам `.kilo/`, базам знаний Revit API и MCP-инструментам.

Ты — установщик и проверяющий. Ты **не** переписываешь роли ботов и не меняешь их SOUL «по вкусу»:
экспорт — источник истины. Всё, что не совпало с реальностью машины, — это находка для отчёта.

## Шаг 0. Проверь себя и окружение

1. `hermes --version` и `hermes doctor` — Hermes установлен и работает?
2. Найди `HERMES_HOME`: переменная окружения `HERMES_HOME`, иначе
   `%LOCALAPPDATA%\hermes` (Windows). Все профили живут в `<HERMES_HOME>/profiles/<имя>`.
3. Зафиксируй корень репозитория — каталог, в котором лежит `agent-team/`.
4. Если Hermes не установлен — установи (инструкция: https://hermes-agent.nousresearch.com/docs),
   затем продолжи. Профилей команды на чистой машине, скорее всего, нет — это нормально.

## Шаг 1. Прочитай экспорт, прежде чем что-то делать

- `agent-team/TEAM.md` — роли, конвейер, матрица MCP и скиллов.
- `agent-team/mcp/MCP-MAP.md` — что за сервер, откуда, как поднять, как проверить.
- `agent-team/skills/SKILLS-MANIFEST.md` — откуда берутся скиллы и правило отбора дублей.
- `agent-team/bots/<бот>/SOUL.md` — роль бота (это его системный промпт; менять содержимое нельзя).
- `agent-team/mcp/mcp-servers.full.yaml` и `mcp-servers.reviewer.yaml` — блоки для `config.yaml`.
- `agent-team/MANIFEST.json` — состав экспорта и контрольные суммы файлов.

## Шаг 2. Инвентаризация предпосылок (что есть — что отсутствует)

Проверь каждый пункт **командой**, а не предположением. Отсутствующее — доустанови (Шаг 4).

| Предпосылка | Проверка | Если нет |
|---|---|---|
| Hermes | `hermes --version` | установить Hermes |
| Node для MCP | `<HERMES_HOME>/node/node.exe --version` или `node -v` | поставить Node (Hermes-сборка node обычно уже есть) |
| Python 3.11 для stdio-MCP | `%LOCALAPPDATA%\Programs\Python\Python311\python.exe -V` | поставить Python 3.11 |
| `uvx` (для excel-MCP) | `<HERMES_HOME>/bin/uvx.exe --version` | идёт с Hermes; иначе `pip install uv` |
| Ключ провайдера LLM | ключ для `routerai` (или другого) в `<HERMES_HOME>/.env` | **спросить у пользователя**, положить в `.env` |
| Qdrant | `curl -s http://127.0.0.1:6333/collections` | поднять Qdrant (docker) |
| Коллекции Revit API | в ответе есть `revit_api_knowledge`, `revit_api`, `Revit_SDK_Samples` | коллекции не переносятся: сообщить пользователю, что нужна индексация |
| CodeGraph | `curl -s http://127.0.0.1:8104/openapi.json` | `docker compose --profile cgc up -d codegraphcontext` в `harness-plugins` |
| harness-plugins (memory-store, qdrant-kb) | есть каталог с `memory-store/src/mcp-server.ts` | клонировать/доставить; путь сообщить в отчёте |
| KnowledgeBaseMCP | есть каталог с `launch_mcp.py` + `.venv/Scripts/python.exe` | venv + `pip install -r requirements.txt` |
| SSH-MCP | есть каталог с `mcp_server.py` + `servers.yaml` | venv + зависимости |
| UiController | `%LOCALAPPDATA%\UiController\RevitUiController.McpServer.exe` и живой `RevitUiController.Daemon.exe --daemon` | `powershell -ExecutionPolicy Bypass -File .kilo/scripts/ui-setup.ps1` |
| Revit + плагин ReVibe | `%LOCALAPPDATA%\RuBIMtech\ReVibe\plugins\revitCopilot\R2x` | сборка/деплой: `.kilo/scripts/build-all.ps1`, `.kilo/scripts/deploy-isolated.ps1` |
| Task Manager | `curl -s -o /dev/null -w "%{http_code}" https://atm.apps.rubim.tech/api/agents` → 200 | сообщить как отсутствующее |

## Шаг 3. Разверни команду

```bash
# план (ничего не пишет) — прочитай, что будет сделано
python agent-team/scripts/apply_team.py

# развернуть: профили, SOUL/AGENTS/profile.yaml, MCP-блоки, модель, Bot Chat, скиллы
python agent-team/scripts/apply_team.py --apply

# проверка состава
python agent-team/scripts/verify_team.py
```

Скрипт идемпотентен: повторный запуск не создаёт дублей и не перезаписывает чужие правки
поверх ваших изменений (MCP-блок вставляется только если его нет).
Если путь внешней зависимости не разрешился, соответствующий сервер помечается `enabled: false`
и попадает в список «требует ручной установки» — это и есть точный список того, чего не хватает.

Пути, если они нестандартные, передавай явно:
`--repo`, `--hermes-home`, `--model`, `--provider`; переменные окружения `HARNESS_PLUGINS`,
`KNOWLEDGEBASE_MCP`, `SSH_MCP`.

## Шаг 4. Доустанови отсутствующее

Действуй по `mcp/MCP-MAP.md`. Порядок — от дешёвого к дорогому:

1. **Скиллы**: `apply_team.py` уже собрал `<HERMES_HOME>/skills-revita` из `.kilo/skills` (+10
   Hermes-native). Проверь: `hermes -p revit-orchestrator skills list | wc -l`.
2. **Task Manager** — ничего ставить не нужно, только доступность хоста.
3. **CodeGraph** — Docker: `docker compose --profile cgc up -d codegraphcontext`, затем
   проиндексировать репозиторий (`add_code_to_graph` или CLI в контейнере) и **проверить
   `get_repository_stats`**, а не журнал задачи.
4. **Qdrant-коллекции** — если отсутствуют, сообщи пользователю: перенос коллекций не
   автоматизирован, нужен прогон индексации из `harness-plugins/memory-store`.
5. **UiController** — `.kilo/scripts/ui-setup.ps1` (по умолчанию Portable), проверить
   `RevitUiController.Host.exe state`.
6. **Revit + плагин** — `build-all.ps1` (при необходимости `-Only R26`), `deploy-isolated.ps1`,
   затем запустить Revit и убедиться, что мост `revit` отдаёт тулы.
7. **Ключи и секреты** — только через `hermes setup` / `.env`; **никогда** не печатать значение
   ключа в чат и не пересылать его текстом.

## Шаг 5. Докажи живьём (не отчётом, а вызовом)

1. `python agent-team/scripts/verify_team.py` — таблица по 5 ботам: заголовок, модель, Bot Chat,
   число MCP-серверов, ключ, AGENTS.md. Никаких находок — иначе сначала исправь.
2. По каждому боту — один настоящий вызов MCP из его сессии:

```bash
hermes -p revit-orchestrator chat -c "Bot Chat" --create-if-missing -q "Вызови mcp__cgc__list_graphs и mcp__qdrant_kb__kb_collection_health, ответь 2 строками: что ответили."
hermes -p revit-qa-tester  chat -c "Bot Chat" --query-file probe-revit.txt   # probe обязан честно сказать, жив ли Revit
```

3. Модель: убедись, что она поддерживает tool calling (вопрос-проба выше даст вызов инструмента).
   Если вызовов инструментов нет — модель не подходит: сообщи и предложи альтернативу.
4. Runtime-полоса (Revit) проверяется только при запущенном Revit. Нет Revit — зафиксируй
   `LIMITATIONS` и не выдавай «работает».
5. Новые профили подхватываются мультиплексным гейтвеем: если боты не видны в Bots-табе,
   `hermes gateway restart` (предупреди пользователя, что это коротко прервёт активные чаты).

## Шаг 6. Отчёт пользователю

Формат — ровно это, без пересказа процесса:

```
Развёрнуто: <N> профилей, <M> MCP-серверов, скиллов <K>, модель <model>.
Проверено живьём: <инструмент → что ответил> (по каждому).
Не работает / требует действия: <пункт → что нужно от пользователя>.
Изменено на машине: <пути профилей, каталог скиллов>.
```

## Жёсткие правила

- **Не выдумывать пути и адреса.** Чего не нашёл — перечисли как отсутствующее.
- **Не печатать секреты** (ключи, токены) — ни в чат, ни в файлы отчёта.
- **Не менять SOUL ботов** и не переименовывать профили: экспорт — источник истины.
- **Не включать** сервера, помеченные `enabled: false`, пока их зависимость реально не поднята.
- **Не выдавать успех без вызова**: «подключено» подтверждается `mcp test` / `tools/list`,
  «работает» — ответом инструмента.
- **Проверять контрольные суммы** `MANIFEST.json` для `bots/**`: расхождение — повод спросить,
  а не «поправить файл молча».
- Не трогать `main`, не пушить, не коммитить за пользователя: только сообщить, что готово к коммиту.
