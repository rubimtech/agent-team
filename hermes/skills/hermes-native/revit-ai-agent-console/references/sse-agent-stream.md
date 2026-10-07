# SSE-стриминг пайплайна в /api/agent

Живая индикация работы агента вместо спиннера: сервер отдаёт события по мере возникновения,
клиент рисует карточку оркестратора и печатает финальный ответ токен-за-токеном.

## Формат кадров

Ответ: `Content-Type: text/event-stream; charset=utf-8`, кадр = `event: <имя>\ndata: <JSON>\n\n`.

| event  | payload | когда шлётся |
|--------|---------|--------------|
| `event`  | объект `AgentEvent` (id, type, message, toolName…) | в момент добавления в журнал |
| `stage`  | `PipelineStageEvent` (stage, title, status, stepId) | смена этапа конвейера |
| `plan`   | `AgentPlan` целиком | сразу после планировщика (до выполнения шагов) |
| `delta`  | `{ text }` — кусок текста синтеза | каждый чанк `streamText().textStream` |
| `result` | финальный JSON прежнего формата (`text`, `usage`, `toolCalls`, `events`, `needsApproval`…) | пайплайн завершён — источник истины для финализации |
| `error`  | `{ error, text }` | исключение внутри пайплайна (после старта потока) |

Ошибки ДО старта (auth-guard, zod-валидация `existingPlan`, `tools.length === 0`) возвращаются
обычным JSON с `!ok` — клиент ветвится по content-type, а не по коду статуса.

## Серверная врезка

1. `app/api/agent/route.ts` до старта: auth → парс тела → конфиг/llm (ключ только из
   `process.env.LLM_API_KEY`) → zod-валидация плана → проверка MCP-соединения → JSON-ответы на отказ.
2. Далее `new Response(ReadableStream, { headers: text/event-stream, no-cache, no-transform })`;
   в `start()` замыкается `send(name, data)` (enqueue в try: отключившийся клиент не роняет пайплайн),
   `executePipelineRun(..., { onEvent, onStage, onPlan, onSynthesisDelta })` → в `.then` кадр
   `result`, в `.catch` — `error`, в `.finally` — `controller.close()` (обёрнут в try).
3. `signal: req.signal` пробрасывается в опции — отмена запроса доходит до оркестратора.

## Оркестратор (`lib/agent/orchestrator.ts`)

- Опциональные колбэки в options: `onEvent`/`onStage`/`onPlan`/`onSynthesisDelta`.
- Эмиссия через `safeEmit(fn, value)` (try/catch): упавший UI-колбэк или отключившийся клиент
  не должны ронять пайплайн — это инвариант, не оптимизация.
- `addEvent`/`addStage` пушат в свои массивы И эмитят — журнал для финального `result` и live-поток
  не расходятся по содержимому.
- `onPlan` вызывается и при `existingPlan` (возобновление после approval) — клиент заново ставит шаги.
- Синтез: `streamText()` вместо `generateText()`; дельты итерируются из **`stream.textStream`**
  (`.text` в AI SDK v7 — Promise, `for await` по нему — ошибка компиляции); usage — в `onFinish`
  через usageSink. Шаблонный fallback при ошибке LLM остаётся без дельт — это норма.

## Клиент (`lib/agent/stream-client.ts`)

- `runAgentRequest(body, handlers, init?)` — fetch + разбор кадров; `init` прокидывает заголовки
  страницы (local-auth) и `AbortSignal` (отмена отправки).
- Разбор: буфер режется по `\n\n`, строки `event:`/`data:`; JSON собирается из всех `data:`-строк.
  Остаток буфера без завершающего разделителя добрасывается с искусственно добавленным `\n\n`.
- Не-SSE content-type → прежний путь: `response.json()`, `!ok` → throw (JSON-ошибки до старта).
- Хендлеры не должны бросать наружу: ошибка UI-хендлера не должна рвать чтение потока
  (гасится внутри разбора кадра).

## Дедуп live и финального мержа (page.tsx)

События/этапы приходят дважды: live-кадрами и повторно в `result`. Мерж с дедупом:

- события — по `id` (`Set` существующих, добавляем только недостающие);
- этапы — по ключу `` `${timestamp}|${stage}|${title}|${stepId ?? ''}` `` (у `PipelineStageEvent` нет id);
- дельты: локальный аккумулятор `streamedText` накапливается в замыкании и кладётся в сообщение
  целиком (`patch({ content: acc })`), финальный `result.text` перезаписывает — он авторитетен.

## UI-карточка (`components/agent/OrchestratorLiveCard.tsx`)

Рисуется вместо спиннера, пока у сообщения ассистента пустой content и `isAgentRunning`:
- текущий этап = последний `status: 'active'` (иначе последний вообще); иконка/цвет по полю
  `stage` (planner/executor/mcp/validator/repair/synthesis);
- мысль = `message` последнего события, иначе `title` этапа; длинный текст (>~90 симв) —
  бегущая строка (`@keyframes mmd-ticker` в `globals.css`, inline animation);
- таймер elapsed тикает через `setInterval(500)` только пока `running`;
- подстрочный список = последние 4 события с тайм-стемпами.
План показывается отдельно: live-хендлер `onPlan` ставит `msg.plan` → `PlanProgressCard` над контентом.

## Верификация потока (делать до «Готово»)

1. `curl -sN -X POST /api/agent ... -o resp.txt -D resp.headers` (файл, не терминал: кадров сотни).
2. В headers: `content-type: text/event-stream`.
3. Разбор python'ом: сколько кадров каждого имени; норма живого запуска — по одному `plan`
   и `result`, десятки `stage`, сотни/тысячи `delta`; в `result` — `finished:true` и ненулевой
   `usage` (нулевой usage + «детерминированный» rationale = LLM-вызов ушёл в fallback, см. ловушку
   в основном скилле).
4. После деплоя — MCP-переподключение и проверка UI-строк (карточки) в собранном `page-*.js`.

## Ловушки

- **`.text` vs `.textStream`** — единственная типовая ошибка при переходе с generateText.
- **Двойной мерж без дедупа** засоряет таймлайн копиями событий — живые и финальные кадры
  содержательно идентичны, но объекты разные: сравнивать по ключам, не по ссылке.
- **Отмена (`AbortController` страницы)** обрывает чтение потока на клиенте; сервер дорабатывает
  в фоне (send глохнет) — финальный `result` при этом не дойдёт, клиент покажет ветку catch
  (AbortError) — это штатное поведение, не баг.
- **Стрим ломает прежнее предположение «один POST — один JSON»**: любые будущие потребители
  `/api/agent` должны ветвиться по content-type (все — через stream-client, не голым fetch).
