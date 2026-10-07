# `agent-team/` — команда AI-ботов для этого репозитория

Экспорт Hermes-команды, которая закрывает полный цикл разработки RevitAiTools:
**приём задачи → требования и риски → код и сборка → независимый тест (в том числе в живом Revit)
→ ревью → приёмка**. Всё работает в этом репозитории, с его правилами (`.kilo/rules`),
скиллами (`.kilo/skills`), каталогом MCP-тулов (`revitCopilot/McpServer/Tools`) и базами знаний
по Revit API.

## Состав

```
agent-team/
├─ README.md                     ← этот файл: как пользоваться и разворачивать
├─ BOOTSTRAP-PROMPT.md           ← промт: отдать агенту на новой машине, он всё поставит
├─ TEAM.md                       ← орг-схема, роли, конвейер, матрица MCP/скиллов
├─ MANIFEST.json                 ← состав экспорта + sha256 файлов ботов
├─ bots/<профиль>/               ← SOUL.md (роль), profile.yaml, AGENTS.md,
│                                   config-keys.yaml (модель, тулсеты, cwd, скиллы, делегирование)
│   ├─ revit-orchestrator/       ← Revit Project Orchestrator
│   ├─ revit-pm/                 ← Revit Architect (требования/риски)
│   ├─ revit-ai-dev/             ← C# Developer
│   ├─ revit-qa-tester/          ← Test Engineer
│   └─ revit-code-reviewer/      ← Reviewer
├─ mcp/
│   ├─ mcp-servers.full.yaml     ← 9 серверов (оркестратор, архитектор, дев, QA)
│   ├─ mcp-servers.reviewer.yaml ← 7 серверов (ревьюер, без ssh/ui)
│   └─ MCP-MAP.md                ← откуда каждый сервер, как поднять, как проверить
├─ skills/
│   ├─ SKILLS-MANIFEST.md        ← правило отбора скиллов и список Hermes-native
│   └─ hermes-native/            ← 10 скиллов, которых нет в репозитории (нужны ботам)
└─ scripts/
    ├─ export_team.py            ← пересобрать экспорт из живых профилей
    ├─ apply_team.py             ← развернуть/обновить команду (идемпотентно)
    └─ verify_team.py            ← приёмка состава (таблица + находки)
```

## Развернуть на новой машине

```bash
# 1. Hermes установлен, ключ провайдера лежит в <HERMES_HOME>/.env
# 2. репозиторий склонирован (каталог agent-team/ внутри)
python agent-team/scripts/apply_team.py            # план: что будет сделано
python agent-team/scripts/apply_team.py --apply    # развернуть
python agent-team/scripts/verify_team.py           # приёмка
```

Либо просто отдать агенту `agent-team/BOOTSTRAP-PROMPT.md` — в нём пошаговый разбор: что
проверить, чего может не хватать, как это поставить и как доказать, что работает.

Скрипт `apply_team.py` создаёт профили, пишет роли, подставляет машинные пути в MCP-блоки,
пиннит модель (в `config.yaml` **и** в `sessions.model` — иначе сессия откатывает модель),
создаёт сессию `Bot Chat`, собирает общий каталог скиллов `<HERMES_HOME>/skills-revita`.
Сервера, чьи зависимости не найдены, он не «включает наугад», а помечает `enabled: false`
и перечисляет в отчёте.

## Как этим пользоваться (после развёртывания)

1. Открой Hermes → таб **Bots** → **Revit Orchestrator** (или `hermes -p revit-orchestrator chat -c "Bot Chat"`).
2. Ставь задачу словами, например: «нужен инструмент, который расставляет розетки по помещениям
   выбранного этажа и пишет спецификацию».
3. Дальше оркестратор сам: определит класс работы (MCP-тул или модуль с UI), задаст тебе вопросы,
   сделает разведку по коду и базам знаний, заведёт задачу в `tasks/todo/` и Task Manager и
   раздаст её команде. Артефакты — в репозитории: `tasks/`, `.kilo/plans/`, `GATES.md`.
4. Приёмка — только после QA и ревьюера: в отчёте будет «что сделано, где, чем проверено,
   что осталось». Незакрытые пункты бот обязан назвать прямо.

Если нового бота не видно в Bots-табе — профиль создан после старта мультиплексного гейтвея:
`hermes gateway restart` (коротко прервёт активные чаты).

## Статус развёртывания на текущей машине

| Проверка | Результат |
|---|---|
| Профили команды | 5 из 5, `Bot Chat` есть у каждого, модель `xiaomi/mimo-v2.6-flash` |
| `cgc` (CodeGraph) | подключён; проиндексированы `RevitAiTools`, `UiController`, `price_parser` |
| `qdrant-kb` | подключён; `revit_api_knowledge` — 66 675 точек, servable (medianTop1 0.85) |
| `knowledgebase` / `memory-store` | подключены (9 тулов каждый) |
| `task_manager` | подключён (atm.apps.rubim.tech, 20 тулов) |
| `ui` (UiController) | подключён, демон запущен; `revit_api` ждёт окно Revit (`ui_connect`) |
| `revit` (мост) | **ждёт запущенный Revit с плагином** — без него runtime-полоса недоступна |
| Сервер `ssh`, `excel` | подключены |

## Что требует ручной установки (на чистой машине)

| Компонент | Как поставить |
|---|---|
| Hermes Agent + ключ провайдера | https://hermes-agent.nousresearch.com/docs, затем `hermes setup` |
| Qdrant + коллекции Revit API | Qdrant (docker) + индексация; **коллекции не переносятся автоматически** |
| CodeGraph (codegraphcontext) | `docker compose --profile cgc up -d codegraphcontext` в `harness-plugins` |
| `harness-plugins/memory-store` | источник `qdrant-kb` и `memory-store` (Node) |
| `KnowledgeBaseMCP` | venv + `pip install -r requirements.txt` |
| `SSH-MCP` | venv + `servers.yaml` с хостами |
| UiController | `powershell -ExecutionPolicy Bypass -File .kilo/scripts/ui-setup.ps1` |
| Revit R22–R27 + плагин ReVibe | `.kilo/scripts/build-all.ps1`, `.kilo/scripts/deploy-isolated.ps1` |
| Task Manager | внешний сервис `https://atm.apps.rubim.tech` |

## Обновление экспорта

Профили на машине — рабочая копия; если ты правил роль бота, обнови экспорт, чтобы он не «отстал»:

```bash
python agent-team/scripts/export_team.py     # перезаписывает bots/, mcp/, MANIFEST.json
python agent-team/scripts/verify_team.py
git add agent-team && git status             # что закоммитить — видно здесь
```

## Принятые решения (осознанные, не случайные)

- **Ревьюеру не выдан `ssh` и `ui`** — это исполнительные пути, с ними его READ_ONLY-контракт
  держался бы только на дисциплине. Тулсеты `file`/`terminal`/`code_execution` у него отключены.
  Нужно иначе — правь `mcp/mcp-servers.reviewer.yaml`.
- **Модель** `xiaomi/mimo-v2.6-flash` через `routerai`. Перед пиннингом проверь, что она умеет
  tool calling (одна проба с `tools=[...]` — иначе боты «рассуждают», но не вызывают инструменты).
- **Единый каталог скиллов** (`skills-revita`) вместо копий в каждом профиле: дубли по
  frontmatter `name` пропускаются, иначе выбор скилла становится недетерминированным.
- **`EXCEL_FILES_PATH`** для команды указывает на корень репозитория (в общем конфиге машины
  это значение было испорчено бэкслешами).
- **Дефис в имени сервера превращается в подчёркивание в имени тула**: `qdrant-kb` →
  `mcp__qdrant_kb__kb_search`. Ботам это сказано в роли.
