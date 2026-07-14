using System.Globalization;
using System.Text;

namespace BrazilianSoccerCore.Data;

/// <summary>
/// Minimal RFC-4180-style CSV reader. Handles quoted fields, embedded commas,
/// and UTF-8 encoding. Returns rows as string arrays keyed by header lookup.
/// </summary>
public static class CsvReader
{
    public static List<string[]> ReadAll(string path)
    {
        var rows = new List<string[]>();
        foreach (var row in ReadRows(path))
            rows.Add(row);
        return rows;
    }

    public static IEnumerable<string[]> ReadRows(string path)
    {
        using var reader = new StreamReader(path, Encoding.UTF8);
        string? line;
        while ((line = reader.ReadLine()) is not null)
        {
            if (line.Length == 0)
                continue;
            yield return ParseLine(line);
        }
    }

    /// <summary>Parses a single CSV line into fields, honoring double-quoted values.</summary>
    public static string[] ParseLine(string line)
    {
        var fields = new List<string>();
        var sb = new StringBuilder();
        var inQuotes = false;
        for (var i = 0; i < line.Length; i++)
        {
            var c = line[i];
            if (inQuotes)
            {
                if (c == '"')
                {
                    if (i + 1 < line.Length && line[i + 1] == '"')
                    {
                        sb.Append('"');
                        i++;
                    }
                    else
                    {
                        inQuotes = false;
                    }
                }
                else
                {
                    sb.Append(c);
                }
            }
            else
            {
                if (c == '"')
                {
                    inQuotes = true;
                }
                else if (c == ',')
                {
                    fields.Add(sb.ToString());
                    sb.Clear();
                }
                else
                {
                    sb.Append(c);
                }
            }
        }
        fields.Add(sb.ToString());
        return fields.ToArray();
    }
}

/// <summary>Maps header names to column indices, case-insensitively.</summary>
public sealed class CsvHeader
{
    private readonly Dictionary<string, int> _lookup;

    public CsvHeader(string[] headers)
    {
        _lookup = new Dictionary<string, int>(headers.Length, StringComparer.OrdinalIgnoreCase);
        for (var i = 0; i < headers.Length; i++)
        {
            // Strip a possible UTF-8 BOM from the first header.
            var h = headers[i].Trim('\uFEFF', ' ', '"');
            if (!_lookup.ContainsKey(h))
                _lookup[h] = i;
        }
    }

    public int? IndexOf(params string[] names)
    {
        foreach (var n in names)
            if (_lookup.TryGetValue(n, out var idx))
                return idx;
        return null;
    }
}