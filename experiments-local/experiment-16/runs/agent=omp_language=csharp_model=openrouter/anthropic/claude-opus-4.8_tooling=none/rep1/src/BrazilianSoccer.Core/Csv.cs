// =============================================================================
// Context: Brazilian Soccer MCP Server — minimal RFC 4180 CSV reader.
//
// The source CSVs are quoted inconsistently: some fields are double-quoted
// (Brasileirao), some are bare (novo_campeonato), team names contain embedded
// commas and parentheses ("Boavista Sport Club (antigo ...) - RJ"), and one file
// is UTF-8 BOM-prefixed (fifa_data). A dependency-free streaming parser keeps the
// loader honest about quoting and embedded delimiters without pulling in a CSV
// package. Returns rows as string arrays; the header row is exposed separately so
// loaders can index by column name.
// =============================================================================
using System.Text;

namespace BrazilianSoccer.Core;

public sealed class CsvTable
{
    private readonly Dictionary<string, int> _index;

    public IReadOnlyList<string> Header { get; }
    public IReadOnlyList<string[]> Rows { get; }

    public CsvTable(IReadOnlyList<string> header, IReadOnlyList<string[]> rows)
    {
        Header = header;
        Rows = rows;
        _index = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        for (int i = 0; i < header.Count; i++)
            _index[header[i].Trim()] = i; // last-wins is fine; headers are unique here
    }

    /// <summary>Column ordinal for a header name, or -1 when absent.</summary>
    public int Col(string name) => _index.TryGetValue(name, out var i) ? i : -1;

    /// <summary>Cell value by column name, or null when the column/cell is missing or empty.</summary>
    public static string? Cell(string[] row, int col)
    {
        if (col < 0 || col >= row.Length)
            return null;
        var v = row[col];
        return string.IsNullOrWhiteSpace(v) ? null : v;
    }
}

public static class Csv
{
    /// <summary>Parse a CSV file from disk (UTF-8, BOM-tolerant) into a header + rows table.</summary>
    public static CsvTable Load(string path)
    {
        using var reader = new StreamReader(path, Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        var records = Parse(reader);
        if (records.Count == 0)
            return new CsvTable(Array.Empty<string>(), Array.Empty<string[]>());

        var header = records[0];
        // Strip a stray BOM that survived on the first header cell.
        if (header.Length > 0)
            header[0] = header[0].TrimStart('\uFEFF');

        var rows = new List<string[]>(records.Count - 1);
        for (int i = 1; i < records.Count; i++)
        {
            // Skip fully blank trailing lines.
            var r = records[i];
            if (r.Length == 1 && r[0].Length == 0)
                continue;
            rows.Add(r);
        }
        return new CsvTable(header, rows);
    }

    /// <summary>Streaming RFC 4180 parse honoring quotes, escaped quotes, and embedded newlines.</summary>
    private static List<string[]> Parse(TextReader reader)
    {
        var records = new List<string[]>();
        var fields = new List<string>();
        var field = new StringBuilder();
        bool inQuotes = false;
        bool fieldStarted = false;

        int ci;
        while ((ci = reader.Read()) >= 0)
        {
            char c = (char)ci;
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
                case '"':
                    inQuotes = true;
                    fieldStarted = true;
                    break;
                case ',':
                    fields.Add(field.ToString());
                    field.Clear();
                    fieldStarted = false;
                    break;
                case '\r':
                    break; // handled with \n
                case '\n':
                    fields.Add(field.ToString());
                    field.Clear();
                    records.Add(fields.ToArray());
                    fields.Clear();
                    fieldStarted = false;
                    break;
                default:
                    field.Append(c);
                    fieldStarted = true;
                    break;
            }
        }

        // Flush trailing field/record if the file does not end with a newline.
        if (fieldStarted || field.Length > 0 || fields.Count > 0)
        {
            fields.Add(field.ToString());
            records.Add(fields.ToArray());
        }

        return records;
    }
}
