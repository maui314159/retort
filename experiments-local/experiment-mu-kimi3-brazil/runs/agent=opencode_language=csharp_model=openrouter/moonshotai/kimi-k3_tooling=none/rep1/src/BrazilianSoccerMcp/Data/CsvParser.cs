using System.Text;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Minimal RFC-4180 style CSV parser: handles quoted fields, escaped quotes (""),
/// commas inside quotes, CRLF line endings and multi-line quoted fields.
/// </summary>
public static class CsvParser
{
    public static IEnumerable<string[]> ReadRows(string path)
    {
        using var reader = new StreamReader(path, Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        foreach (var row in ReadRows(reader))
            yield return row;
    }

    public static IEnumerable<string[]> ReadRows(TextReader reader)
    {
        var field = new StringBuilder();
        var row = new List<string>();
        var inQuotes = false;
        var fieldStarted = false;

        while (true)
        {
            var next = reader.Read();
            if (next == -1)
            {
                if (fieldStarted || field.Length > 0 || row.Count > 0)
                {
                    row.Add(field.ToString());
                    yield return row.ToArray();
                }
                yield break;
            }

            var c = (char)next;

            if (inQuotes)
            {
                if (c == '"')
                {
                    if (reader.Peek() == '"')
                    {
                        reader.Read();
                        field.Append('"');
                    }
                    else
                    {
                        inQuotes = false;
                    }
                }
                else
                {
                    field.Append(c);
                }
                continue;
            }

            switch (c)
            {
                case '"' when !fieldStarted:
                    inQuotes = true;
                    fieldStarted = true;
                    break;
                case ',':
                    row.Add(field.ToString());
                    field.Clear();
                    fieldStarted = false;
                    break;
                case '\r':
                    break; // tolerate CRLF
                case '\n':
                    row.Add(field.ToString());
                    yield return row.ToArray();
                    row = new List<string>();
                    field.Clear();
                    fieldStarted = false;
                    break;
                default:
                    field.Append(c);
                    fieldStarted = true;
                    break;
            }
        }
    }
}
