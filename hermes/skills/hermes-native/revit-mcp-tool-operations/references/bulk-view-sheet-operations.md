# Массовые операции над видами и листами

Проверено на Revit 2026.4, документ с 29 листами / 64 видами → 1 лист + 1 вид.
Сценарий «оставить один лист и один вид» выполняется ТОЛЬКО через CSX
(`code_runner_compile` → `code_runner_execute`), тремя отдельными транзакциями.

## Почему не одной транзакцией

Попытка удалить листы и виды в одной транзакции (даже в `TransactionGroup` c `Assimilate`)
роняет Revit: `InvalidObjectException: The referenced object is not valid` — падает либо весь
скрипт, либо транзакция молча откатывается при внешнем виде `success: true`. Причина — в
наборе удаляемых элементов оказывается активный вид или участвующий в иерархии видов.
Разбивка по стадиям работает стабильно.

## Порядок стадий

1. Активировать сохраняемый вид: `UIDoc.ActiveView = Doc.GetElement(keepView) as View;`
2. Транзакция «Delete sheets» — все `ViewSheet`, кроме `keepSheet`.
3. Транзакция «Delete views» — все `View`, кроме `keepView` и шаблонов.
4. Транзакция «Delete view templates» — оставшиеся `View` c `IsTemplate == true`.

Шаблоны обязательно отдельным проходом: в общем цикле часть удаляется, часть падает, и
диагностика вводит в заблуждение. Отдельным проходом — 10 из 10 без ошибок.

## Сбор элементов

```csharp
// листы — только так; ViewSheet-наследники View, но IsTemplate/OST_Sheets фильтры их иначе теряют
var sheets = new FilteredElementCollector(Doc)
    .OfCategory(BuiltInCategory.OST_Sheets)
    .WhereElementIsNotElementType()
    .Cast<ViewSheet>()
    .ToList();

// виды — БЕЗ WhereElementIsElementType(): он отбрасывает всё, включая листы => views=0
var views = new FilteredElementCollector(Doc)
    .OfClass(typeof(View))
    .Cast<View>()
    .ToList();
```

`WhereElementIsElementType()` даёт пустой результат по видам — это молчаливое «ничего не
сделал», а не пустой документ.

## Что удалить нельзя

`ProjectBrowser` («Проекционный вид») и `SystemBrowser` («Диспетчер инженерных систем») —
`Doc.Delete` бросает `ArgumentException`. Они остаются в модели всегда, в интерфейсе не
отображаются. Остаток из этих двух — ожидаемое состояние, а не недоделка.

## Обязательные проверки в цикле

```csharp
foreach (var id in ids)
{
    if (!t.HasStarted()) { sb.AppendLine("TX CLOSED at " + id); break; }
    var el = Doc.GetElement(id) as View;   // перечитывать по Id, не держать ссылки из коллектора
    if (el == null || el.IsTemplate) continue;
    try { if (Doc.Delete(id) != null) del++; }
    catch (Exception e) { errIds.Add(id.Value + " " + e.GetType().Name); }
}
```

Ссылки на элементы, собранные до начала транзакции, инвалидируются по мере удаления —
отсюда и `InvalidObjectException`. Перечитывай элемент по Id на каждой итерации.

## Read-back

Возврат скрипта не доказательство. После прог��на заново читай документ:

```
get_all_sheets '{}'   → sheetCount
get_all_views  '{}'   → count + список остатков
```

Ожидаемый результат для «оставить один»: `sheetCount: 1`, `count: 4`
(2 служебных браузера + лист + вид).

## Скрипты

Рабочие скрипты этой операции — `scripts/` этого навыка (`del_sheets.csx`,
`del_views.csx`, `del_templates.csx`), запуск — `scripts/runcsx.py <файл> compile|execute`.