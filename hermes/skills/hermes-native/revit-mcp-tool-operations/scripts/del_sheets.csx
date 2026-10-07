// Удаляет все листы кроме keepSheet. Запуск: Transaction изнутри обязателен.
var keepSheet = new ElementId(1687761);
var sheets = new FilteredElementCollector(Doc)
    .OfCategory(BuiltInCategory.OST_Sheets)
    .WhereElementIsNotElementType()
    .Cast<ViewSheet>()
    .ToList();

var sb = new System.Text.StringBuilder();
sb.AppendLine("sheets found: " + sheets.Count);
sb.AppendLine("active view before: " + UIDoc.ActiveView.Name + " id=" + UIDoc.ActiveView.Id.Value);

using (var t = new Transaction(Doc, "Delete sheets"))
{
    t.Start();
    int del = 0;
    foreach (var s in sheets)
    {
        if (s.Id == keepSheet) continue;
        if (!t.HasStarted()) { sb.AppendLine("TX CLOSED at sheet " + s.Id); break; }
        try { if (Doc.Delete(s.Id) != null) del++; }
        catch (Exception e) { sb.AppendLine("sheet " + s.Id + " " + s.Name + " -> " + e.GetType().Name); }
    }
    sb.AppendLine("deleted: " + del + " status=" + t.GetStatus());
    t.Commit();
}

var after = new FilteredElementCollector(Doc)
    .OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().Cast<ViewSheet>().ToList();
sb.AppendLine("after: " + after.Count);
foreach (var s in after) sb.AppendLine("  " + s.Id + " #" + s.SheetNumber + " " + s.Name);
return sb.ToString();