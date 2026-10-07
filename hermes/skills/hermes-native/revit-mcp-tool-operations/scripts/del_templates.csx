// Удаляет оставшиеся шаблоны видов (IsTemplate). Отдельная транзакция обязательна.
var sb = new System.Text.StringBuilder();
var templates = new FilteredElementCollector(Doc)
    .OfClass(typeof(View))
    .Cast<View>()
    .Where(v => v.IsTemplate)
    .ToList();
sb.AppendLine("templates: " + templates.Count);

int del = 0;
var errs = new List<string>();
using (var t = new Transaction(Doc, "Delete view templates"))
{
    t.Start();
    foreach (var v in templates)
    {
        var id = v.Id;
        try { if (Doc.Delete(id) != null) del++; else errs.Add(id.Value + " returned null"); }
        catch (Exception e) { errs.Add(id.Value + " " + v.Name + " -> " + e.GetType().Name); }
    }
    sb.AppendLine("deleted: " + del + " errors=" + errs.Count);
    t.Commit();
}

var after = new FilteredElementCollector(Doc).OfClass(typeof(View)).Cast<View>().ToList();
sb.AppendLine("views after: " + after.Count);
foreach (var v in after) sb.AppendLine("  " + v.Id + " " + v.Name + " [" + v.ViewType + "]"
    + (v.IsTemplate ? " TEMPLATE" : "") + (v is ViewSheet ? " SHEET" : ""));
if (errs.Count > 0) sb.AppendLine("errs: " + string.Join(" | ", errs.ToArray()));
return sb.ToString();