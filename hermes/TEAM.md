# Команда ботов RevitAiTools — состав и правила

Экспорт команды Hermes-ботов, которая работает в этом репозитории. Каталог самодостаточен:
разворачивается скриптом на любой машине (`scripts/apply_team.py`), боты общаются между собой
через Hermes (`message_agent` / `delegate_task`), состояние проекта живёт в репозитории
(`tasks/`, `.kilo/plans/`, `GATES.md`, `.kilo/rules/`).

## Орг-схема

```
Revit Project Orchestrator  (revit-orchestrator)
├─ Revit Architect / требования   (revit-pm)
│    └─ субагенты: requirements-clarifier · reuse-scout · risk-analyst · revit-api-researcher
├─ C# Developer                    (revit-ai-dev)
│    └─ субагенты: codebase-researcher · implementation-drafter · test-writer · revit-api-researcher
├─ Test Engineer                   (revit-qa-tester)
│    └─ субагенты: coverage-analyst · failing-test-triage · smoke-checklist · negative-case-designer
└─ Reviewer                        (revit-code-reviewer)
     └─ субагенты: diff-reviewer · security-reviewer · revit-api-pattern-reviewer
```

Дополнительные профили, которых оркестратор зовёт по необходимости (в этот экспорт не входят,
живут в репозитории как `.kilo/agent/revit-*.md`): `revit-mcp-security`, `revit-build-master`,
`revit-tech-writer`, `revit-architect` (строитель моделей), `revit-ai-operator`,
`revit-family-creator`, `revit-eval-observer`, `revit-porting-lead`, `revit-cli-fleet`,
`revit-ai-contributor`, `revit-plan-analyst`.

## Кто за что отвечает

| Бот | Профиль | Делает | Не делает |
|---|---|---|---|
| Оркестратор | `revit-orchestrator` | принимает хотелку, TRIAGE «MCP-тул или модуль с UI», задаёт вопросы через `clarify`, собирает план, раздаёт работу, принимает результат | не пишет код, не правит модель Revit, не ревьюит сам |
| Архитектор требований | `revit-pm` | требования, поиск похожих/существующих команд, риск-анализ, dev-ready задача (`tasks/todo/NN-*.md` + Task Manager) | не пишет код, не ходит в живой Revit |
| C# Developer | `revit-ai-dev` | код плагина и MCP-тулов, сборка R22–R27, деплой, горячая подмена DLL | не мёржит `main`, не правит тесты ради зелёного |
| Test Engineer | `revit-qa-tester` | независимая верификация: xUnit net48, TUnit+Revit, runtime через MCP; bug-задачи | не правит бизнес-логику, не коммитит за разработчика |
| Reviewer | `revit-code-reviewer` | diff / security / Revit API-паттерны; вердикт PASS / FAIL / BLOCKED | не применяет фиксы (READ_ONLY) |

## Конвейер (гейты)

1. **TRIAGE** — класс работы и обоснование попадают в план (это не «догадка», а решение с критериями).
2. **INTERVIEW** — вопросы пользователю, пока требования не станут наблюдаемыми.
3. **RECON** — лестница переиспользования (`.kilo/skills/revit-reuse-ladder`) + `mcp__cgc__*`;
   нет Reuse-блока — код не начинается.
4. **PLAN** — `tasks/todo/NN-name.md` (шаблон в `.kilo/agent/revit-pm.md`), строка в `tasks/README.md`,
   задача в Task Manager.
5. **DISPATCH** — задача уходит `revit-ai-dev`; исследовательские вопросы — субагентам.
6. **GATE** — QA (evidence: команда + настоящий вывод) и Reviewer (diff) принимают/отклоняют.
   FAIL — это список дефектов с `file:line`, пригодный к исполнению.
7. **ACCEPT** — отчёт пользователю: что сделано, где, чем проверено, что осталось.

## Матрица MCP по ролям

| Сервер | orchestrator | pm | ai-dev | qa-tester | code-reviewer |
|---|---|---|---|---|---|
| `cgc` (CodeGraph) | ✓ | ✓ | ✓ | ✓ | ✓ |
| `qdrant-kb` (Revit API KB) | ✓ | ✓ | ✓ | ✓ | ✓ |
| `knowledgebase` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `memory-store` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `task_manager` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `revit` (мост к живому Revit) | ✓ | ✓ | ✓ | ✓ | ✓ |
| `excel` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ui` (UiController) | ✓ | ✓ | ✓ | ✓ | — |
| `ssh` | ✓ | ✓ | ✓ | ✓ | — |

У ревьюера сознательно нет `ui` и `ssh`: это исполнительные пути (клики и шелл), с ними
READ_ONLY-контракт держался бы только на дисциплине. Тулсеты `file`, `terminal`,
`code_execution` у него отключены в `config.yaml` — `write_file` в сессии отсутствует.

## Матрица скиллов по ролям (ключевое)

| Тема | Скиллы |
|---|---|
| Требования и план | `interview-me`, `spec-driven-development`, `task-specification`, `completion-gates` |
| Переиспользование и код | `revit-reuse-ladder`, `revit-mcp-tool-operations`, `mcp-tool-design`, `mcp-tool-rules` |
| Revit API и версии | `revit-*` из `.kilo/skills` (103 скилла репозитория), `revit-testing` |
| Поиск | `qdrant-kb-and-cgc-mcp`, `rvtdocs-search`, `codebase-onboarding` |
| Верификация | `verification-dod`, `self-eval`, `ship-gate`, `human-gate` |
| Организация | `agent-org-orchestration`, `cli-agent-orchestration`, `task-manager`, `task-manager-insights` |

Полный список и правило отбора дублей — `skills/SKILLS-MANIFEST.md`.

## Внешние контуры (без них часть цикла не работает)

| Контур | Нужен для | Без него |
|---|---|---|
| Qdrant + коллекции Revit API | `qdrant-kb` | семантический поиск по Revit API недоступен |
| CodeGraph (docker, 8104) | `cgc` | нет `find_code` / callers / impact |
| Запущенный Revit + плагин ReVibe | `revit` (мост) | runtime-полоса тестирования и `dll_load/dll_reload` |
| UiController (демон + MCP) | `ui` | автотесты интерфейса и `revit_api` через UIA |
| Task Manager (atm.apps.rubim.tech) | `task_manager` | очередь задач команды |
| harness-plugins (memory-store, qdrant-kb) | оба сервера | нет семантического поиска и памяти сессий |

Подробно — `mcp/MCP-MAP.md`.
