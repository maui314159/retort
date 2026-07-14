// BrazilianSoccerMcp.Core - Minimal RFC-4180-ish CSV reader.
// We avoid a third-party dependency by hand-rolling a small parser that
// supports quoted fields, embedded commas, doubled-quote escaping and CRLF/LF
// line endings. UTF-8 is enforced on input so Portuguese accents (São Paulo,
// Grêmio, Avaí) are preserved.
using System.Globalization;
using System.Text;

namespace BrazilianSoccerMcp.Core.Data.Csv;

/// <summary>
/// Reads a CSV file into rows of string fields using the first row as header.
/// Throws <see cref="InvalidDataException"/> for malformed quoting.
/// </summary>
public static class SimpleCsvReader
{
    public static IReadOnlyList<CsvRow> Read(string path)
    {
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        using var reader = new StreamReader(stream, Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        return Read(reader);
    }

    public static IReadOnlyList<CsvRow> Read(TextReader reader)
    {
        var rows = new List<CsvRow>();
        string[]? headers = null;

        foreach (var line in EnumerateRecords(reader))
        {
            var fields = ParseLine(line);
            if (headers is null)
            {
                headers = fields;
                continue;
            }
            rows.Add(new CsvRow(headers, fields));
        }
        return rows;
    }

    private static IEnumerable<string> EnumerateRecords(TextReader reader)
    {
        var sb = new StringBuilder();
        bool inQuotes = false;
        int c;
        while ((c = reader.Read()) != -1)
        {
            var ch = (char)c;
            if (ch == '"')
            {
                inQuotes = !inQuotes;
                sb.Append(ch);
                continue;
            }
            if ((ch == '\n' || ch == '\r') && !inQuotes)
            {
                // Handle CRLF.
                if (ch == '\r' && reader.Peek() == '\n') reader.Read();
                var line = sb.ToString();
                sb.Clear();
                if (line.Length == 0) continue; // skip blank lines
                yield return line;
                continue;
            }
            sb.Append(ch);
        }
        if (sb.Length > 0)
            yield return sb.ToString();
    }

    private static string[] ParseLine(string line)
    {
        var fields = new List<string>();
        var sb = new StringBuilder();
        bool inQuotes = false;
        for (int i = 0; i < line.Length; i++)
        {
            var ch = line[i];
            if (ch == '"')
            {
                if (inQuotes && i + 1 < line.Length && line[i + 1] == '"')
                {
                    sb.Append('"');
                    i++;
                }
                else
                {
                    inQuotes = !inQuotes;
                }
                continue;
            }
            if (ch == ',' && !inQuotes)
            {
                fields.Add(sb.ToString().Trim());
                sb.Clear();
                continue;
            }
            sb.Append(ch);
        }
        fields.Add(sb.ToString().Trim());
        return fields.ToArray();
    }
}

/// <summary>A single CSV row providing case-insensitive header lookup.</summary>
public sealed class CsvRow
{
    private readonly Dictionary<string, string> _map;
    private readonly string[] _headers;

    public CsvRow(string[] headers, string[] fields)
    {
        _headers = headers;
        _map = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        for (int i = 0; i < headers.Length; i++)
        {
            var value = i < fields.Length ? fields[i] : "";
            _map[headers[i]] = value;
        }
    }

    public string Get(string header) =>
        _map.TryGetValue(header, out var v) ? v : "";

    public string? GetOrNull(string header) =>
        _map.TryGetValue(header, out var v) && !string.IsNullOrWhiteSpace(v) ? v : null;

    public int GetInt(string header, int fallback = 0)
    {
        var raw = Get(header).Trim().Trim('"');
        if (int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var v)) return v;
        if (double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var d)) return (int)d;
        return fallback;
    }

    public double? GetDouble(string header)
    {
        var raw = Get(header).Trim().Trim('"');
        if (double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var d)) return d;
        return null;
    }

    public IReadOnlyDictionary<string, string> All => _map;
    public IReadOnlyList<string> Headers => _headers;
}
