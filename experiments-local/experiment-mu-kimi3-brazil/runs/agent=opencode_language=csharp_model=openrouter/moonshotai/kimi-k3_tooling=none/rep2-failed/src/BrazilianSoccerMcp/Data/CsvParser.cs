// Context: Brazilian Soccer MCP Server.
// Minimal, allocation-conscious CSV parser that handles RFC-4180 style quoting
// (quoted fields, embedded commas, embedded quotes via double-quote escaping).
// Written instead of taking a dependency so the server stays self-contained.
namespace BrazilianSoccerMcp.Data;

using System.Text;

/// <summary>Streams rows of a CSV file as arrays of fields. Handles UTF-8 and quoted fields.</summary>
public static class CsvParser
{
    /// <summary>Parses the whole file. First row is returned as well (caller decides if it is a header).</summary>
    public static List<string[]> ParseFile(string path)
    {
        using var reader = new StreamReader(path, detectEncodingFromByteOrderMarks: true);
        return Parse(reader);
    }

    public static List<string[]> Parse(TextReader reader)
    {
        var rows = new List<string[]>();
        var fields = new List<string>();
        var field = new StringBuilder();
        var inQuotes = false;
        var hasData = false;

        while (true)
        {
            var i = reader.Read();
            if (i == -1)
            {
                if (inQuotes) throw new InvalidDataException("Unterminated quoted field in CSV.");
                if (hasData || field.Length > 0 || fields.Count > 0)
                {
                    fields.Add(field.ToString());
                    rows.Add(fields.ToArray());
                }
                break;
            }

            var c = (char)i;
            if (inQuotes)
            {
                if (c == '"')
                {
                    // Double quote inside quotes = escaped quote; otherwise closes the quoted field.
                    if (reader.Peek() == '"') { field.Append('"'); reader.Read(); }
                    else inQuotes = false;
                }
                else field.Append(c);
            }
            else
            {
                switch (c)
                {
                    case '"' when field.Length == 0 && !hasData:
                        inQuotes = true;
                        hasData = true;
                        break;
                    case ',':
                        fields.Add(field.ToString());
                        field.Clear();
                        hasData = false;
                        break;
                    case '\r':
                        break; // swallow; '\n' terminates the row
                    case '\n':
                        fields.Add(field.ToString());
                        field.Clear();
                        hasData = false;
                        rows.Add(fields.ToArray());
                        fields.Clear();
                        break;
                    default:
                        field.Append(c);
                        hasData = true;
                        break;
                }
            }
        }
        return rows;
    }
}
