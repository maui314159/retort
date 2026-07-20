namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Minimal RFC-4180 CSV reader: handles quoted fields, escaped quotes (""),
/// commas inside quotes and embedded newlines. Streams rows as string arrays.
/// </summary>
public static class CsvReader
{
    public static IEnumerable<string[]> ReadRows(string path)
    {
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        using var reader = new StreamReader(stream, System.Text.Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        return ReadRows(reader).ToList(); // materialize so the file handle is released
    }

    public static IEnumerable<string[]> ReadRows(TextReader reader)
    {
        var row = new List<string>();
        var field = new System.Text.StringBuilder();
        var inQuotes = false;
        var fieldStarted = false;
        var pending = new Queue<int>(); // small lookahead buffer

        int Read()
        {
            if (pending.Count > 0) return pending.Dequeue();
            return reader.Read();
        }

        int Peek()
        {
            if (pending.Count > 0) return pending.Peek();
            var c = reader.Read();
            if (c >= 0) pending.Enqueue(c);
            return c;
        }

        while (true)
        {
            var ci = Read();
            if (ci < 0)
            {
                // EOF
                if (fieldStarted || field.Length > 0 || row.Count > 0)
                {
                    row.Add(field.ToString());
                    yield return row.ToArray();
                }
                yield break;
            }

            var c = (char)ci;

            if (inQuotes)
            {
                if (c == '"')
                {
                    if (Peek() == '"')
                    {
                        Read(); // consume escaped quote
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
            }
            else
            {
                switch (c)
                {
                    case '"' when field.Length == 0 && !fieldStarted:
                        inQuotes = true;
                        fieldStarted = true;
                        break;
                    case ',':
                        row.Add(field.ToString());
                        field.Clear();
                        fieldStarted = false;
                        break;
                    case '\r':
                        // skip; handle \n next (or lone \r ends the row)
                        if (Peek() == '\n') { Read(); }
                        row.Add(field.ToString());
                        yield return row.ToArray();
                        row = new List<string>();
                        field.Clear();
                        fieldStarted = false;
                        break;
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
}
