# RouterAI (https://routerai.ru) — факты для интеграции и учёта токенов

OpenAI-совместимый LLM-провайдер; baseURL консоли по умолчанию `https://routerai.ru/api/v1`.
Источник — docs провайдера (`/docs/guides`, service-tiers, decisions/overview, MCP-инструменты).

## Ответы API

- Аутентификация: `Authorization: Bearer <API_KEY>`.
- Chat completion: usage в стандартном openai-виде:
  `"usage": {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}`.
  Имя модели — верхнеуровневое поле `model` (формат `author/model`); в `usage` model id НЕТ.
- `/models` существует — через него работает комбобокс моделей консоли
  (`/api/llm/models` → provider `/models`, `{data:[{id}]}` или массив строк).

## Серверный учёт и стоимость

- **REST-баланса/статистики для обычного API-ключа НЕТ**: `/api/v1/balance`,
  `/api/v1/usage` отсутствуют в docs. Баланс — только веб-кабинет `/settings/billing`.
  Не пытайся опрашивать баланс эндпоинтом — его нет.
- **Стоимость генерации в ₽**: из заголовка HTTP-ответа `X-Generation-Id` →
  `GET /api/v1/generation?id=<id>` → поле `total_cost` (рубли). В консоли ещё не
  реализовано — следующий шаг поверх `usage_log`: доставать заголовок из
  `result.response.headers` AI SDK и писать ₽ рядом с токенами.
- `usage.cost` задокументирован для STT/Images/Video; для текстовых chat completions — нет.
- MCP-провайдер `https://routerai.ru/api/v1/mcp`: инструменты `get_balance`,
  `get_statement`, `get_generation` со scope `billing.read`/`history.read` —
  единственный описанный способ получить баланс программно (нужен MCP-токен, не обычный ключ).
- Team API `GET /api/v1/team` (мастер-ключ): `monthly_spending`, `period_spending`.

## Ошибки и лимиты

- `402` = «Недостаточно средств на балансе» — детектить как конец генерации, не ретраить.
- Rate limits `/api/v1` в docs не описаны (ни значений, ни `X-RateLimit-*`, ни формата 429).
  Задокументирован только MCP: 120 req/min → `429`. Для HTTP-вызовов — backoff без опоры
  на заголовки; при первых реальных 429 логировать фактические заголовки.

## Что это значит для консоли

- Основной учёт токенов — из AI SDK (`generateText`/`generateObject` → `result.usage`):
  в `lib/agent/usage.ts` нормализуются все варианты имён полей
  (`promptTokens|inputTokens|prompt_tokens|...`) и пишутся в `usage_log`.
- ₽-стоимость — отдельным асинхронным запросом по `X-Generation-Id` (defensive-парсинг,
  `cost=null` при неудаче); баланс не опрашивать.
