namespace BrazilianSoccerMcp.Data;

/// <summary>
/// A quote-aware CSV parser (RFC 4180 style) that handles UTF-8 BOMs,
/// embedded commas/newlines inside quoted fields, and doubled quotes.
/// Dependency-free by design so the server has zero external packages.
/// </summary>
public static class CsvParser
{
    public sealed class CsvTable
    {
        public required IReadOnlyList<string> Headers { get; init; }
        public required IReadOnlyList<string[]> Rows { get; init; }

        public int ColumnIndex(string name)
        {
            for (var i = 0; i < Headers.Count; i++)
                if (string.Equals(Headers[i], name, StringComparison.OrdinalIgnoreCase))
                    return i;
            return -1;
        }
    }

    public static CsvTable Load(string path)
    {
        using var stream = File.OpenRead(path);
        return Parse(stream);
    }

    public static CsvTable Parse(Stream stream)
    {
        // StreamReader with BOM detection (detectEncodingFromByteOrderMarks: true).
        using var reader = new StreamReader(stream, System.Text.Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        var records = new List<string[]>();
        var field = new System.Text.StringBuilder();
        var record = new List<string>();
        var inQuotes = false;
        var fieldStarted = false;

        while (true)
        {
            var ch = reader.Read();
            if (ch == -1)
            {
                if (inQuotes)
                    throw new InvalidDataException("CSV ended while inside a quoted field.");
                break;
            }

            var c = (char)ch;
            if (inQuotes)
            {
                if (c == '"')
                {
                    if (reader.Peek() == '"')
                    {
                        field.Append('"');
                        reader.Read();
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
                case '"':
                    inQuotes = true;
                    fieldStarted = true;
                    break;
                case ',':
                    record.Add(field.ToString());
                    field.Clear();
                    fieldStarted = false;
                    break;
                case '\r':
                    // swallow; '\n' terminates the record
                    break;
                case '\n':
                    record.Add(field.ToString());
                    field.Clear();
                    fieldStarted = false;
                    records.Add(record.ToArray());
                    record.Clear();
                    break;
                default:
                    field.Append(c);
                    fieldStarted = true;
                    break;
            }
        }

        // Flush trailing record (file may not end with newline).
        if (record.Count > 0 || field.Length > 0 || fieldStarted)
        {
            record.Add(field.ToString());
            records.Add(record.ToArray());
        }

        // Drop fully empty trailing lines.
        records.RemoveAll(r => r.Length == 1 && string.IsNullOrWhiteSpace(r[0]));

        if (records.Count == 0)
            return new CsvTable { Headers = Array.Empty<string>(), Rows = Array.Empty<string[]>() };

        var headers = records[0].Select(h => h.Trim().TrimStart('﻿')).ToArray();
        return new CsvTable { Headers = headers, Rows = records.Skip(1).ToArray() };
    }

    public static string Get(string[] row, int index) =>
        index >= 0 && index < row.Length ? row[index].Trim() : string.Empty;
}
