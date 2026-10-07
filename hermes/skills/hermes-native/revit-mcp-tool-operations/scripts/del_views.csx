// Удаляет все нешаблонные виды кроме keepView. Шаблоны — отдельным проходом (del_templates.csx).
var keepView = new ElementId(1687988);

var all = new FilteredElementCollector(Doc).OfClass(typeof(View)).Cast<View>().ToList();
var sb = new System.Text.StringBuilder();
sb.AppendLine("views before: " + all.Count);

var ids = new List<ElementId>();
foreach (var v in all) { if (v.Id != keepView && !(v is ViewSheet)) ids.Add(v.Id); }
sb.AppendLine("to delete: " + ids.Count);

int del = 0, skipTemplate = 0, err = 0;
var errIds = new List<string>();
using (var t = new Transaction(Doc, "Delete views"))
{
    t.Start();
    foreach (var id in ids)
    {
        if (!t.HasStarted()) { sb.AppendLine("TX CLOSED at " + id); break; }
        var el = Doc.GetElement(id) as View;   // перечитывать: ссылки из коллектора инвалидируются
        if (el == null) continue;
        if (el.IsTemplate) { skipTemplate++; continue; }
        try { if (Doc.Delete(id) != null) del++; }
        catch (Exception e) { err++; errIds.Add(id.Value + " " + e.GetType().Name); }
    }
    sb.AppendLine("deleted=" + del + " templates=" + skipTemplate + " errors=" + err);
    t.Commit();
}

var after = new FilteredElementCollector(Doc).OfClass(typeof(View)).Cast<View>().ToList();
sb.AppendLine("views after: " + after.Count);
foreach (var v in after) sb.AppendLine("  " + v.Id + " " + v.Name + " [" + v.ViewType + "]"
    + (v.IsTemplate ? " TEMPLATE" : "") + (v is ViewSheet ? " SHEET" : ""));
if (errIds.Count > 0) sb.AppendLine("err: " + string.Join(", ", errIds.ToArray()));
return sb.ToString();