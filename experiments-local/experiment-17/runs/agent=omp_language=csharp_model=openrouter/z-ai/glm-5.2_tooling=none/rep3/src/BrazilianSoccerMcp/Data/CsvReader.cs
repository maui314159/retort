// Brazilian Soccer MCP Server - Minimal RFC4180 CSV reader
// Context: The bundled CSVs mix plain comma-delimited fields with quoted fields
// containing embedded commas (e.g. FIFA "Joined","Jul 1, 2004") and BOM-prefixed
// headers. Rather than pull in a dependency, this tiny reader handles quoted
// fields, embedded quotes (""), and CRLF/LF line endings. It yields rows as
// string arrays; callers index by header position.

using System.Text;

namespace BrazilianSoccerMcp.Data;

/// <summary>Minimal comma-separated value reader handling quotes and BOMs.</summary>
public static class CsvReader
{
    /// <summary>Reads every row from <paramref name="path"/> as a string array,
    /// returning a (headers, rows) tuple. UTF-8 with BOM detection.</summary>
    public static (string[] Headers, List<string[]> Rows) Read(string path)
    {
        using var stream = File.OpenRead(path);
        // Skip UTF-8 BOM if present.
        var bom = new byte[3];
        int read = stream.Read(bom, 0, 3);
        if (!(read == 3 && bom[0] == 0xEF && bom[1] == 0xBB && bom[2] == 0xBF))
            stream.Position = 0;

        using var reader = new StreamReader(stream, Encoding.UTF8);
        string? headerLine = reader.ReadLine();
        if (headerLine == null)
            return (Array.Empty<string>(), new List<string[]>());

        var headers = ParseLine(headerLine);
        var rows = new List<string[]>();
        string? line;
        while ((line = reader.ReadLine()) != null)
        {
            if (line.Length == 0)
                continue;
            // Stitch continuation lines when a quoted field spans newlines.
            while (CountUnescapedQuotes(line) % 2 != 0)
            {
                var next = reader.ReadLine();
                if (next == null)
                    break;
                line += "\n" + next;
            }
            rows.Add(ParseLine(line));
        }
        return (headers, rows);
    }

    private static string[] ParseLine(string line)
    {
        var fields = new List<string>();
        var sb = new StringBuilder(line.Length);
        bool inQuotes = false;
        for (int i = 0; i < line.Length; i++)
        {
            char c = line[i];
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

    private static int CountUnescapedQuotes(string line)
    {
        int count = 0;
        bool inQuotes = false;
        for (int i = 0; i < line.Length; i++)
        {
            char c = line[i];
            if (c == '"')
            {
                if (inQuotes && i + 1 < line.Length && line[i + 1] == '"')
                {
                    i++;
                }
                else
                {
                    inQuotes = !inQuotes;
                    count++;
                }
            }
        }
        return count;
    }
}
