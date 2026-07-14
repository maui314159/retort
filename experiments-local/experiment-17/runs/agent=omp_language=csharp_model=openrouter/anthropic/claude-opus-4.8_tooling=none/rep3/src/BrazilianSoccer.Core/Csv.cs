// =============================================================================
// File:    Csv.cs
// Project: BrazilianSoccer.Core
// Purpose: Minimal, allocation-conscious RFC-4180 CSV reader. Streams a file
//          line by line and yields field arrays, honoring double-quoted fields
//          (including embedded commas, escaped "" quotes, and newlines inside
//          quotes).
// Context: The provided CSVs mix quoting styles — Brasileirao_Matches.csv
//          quotes every field, BR-Football-Dataset.csv quotes none, and
//          Brazilian_Cup_Matches.csv quotes only some. A dependency-free
//          parser keeps the Core library free of third-party CSV packages and
//          handles all three. fifa_data.csv carries a UTF-8 BOM on the first
//          (empty) header cell, which the header mapper tolerates.
// =============================================================================

namespace BrazilianSoccer.Core;

public static class Csv
{
    /// <summary>Streams records (each a string[] of fields) from a UTF-8 CSV file.</summary>
    public static IEnumerable<string[]> ReadRecords(string path)
    {
        using var reader = new StreamReader(path);
        var fields = new List<string>();
        var field = new System.Text.StringBuilder();
        bool inQuotes = false;
        bool sawAny = false;
        int ch;

        while ((ch = reader.Read()) != -1)
        {
            char c = (char)ch;
            if (inQuotes)
            {
                if (c == '"')
                {
                    if (reader.Peek() == '"') { reader.Read(); field.Append('"'); }
                    else inQuotes = false;
                }
                else field.Append(c);
            }
            else
            {
                switch (c)
                {
                    case '"':
                        inQuotes = true;
                        sawAny = true;
                        break;
                    case ',':
                        fields.Add(field.ToString());
                        field.Clear();
                        sawAny = true;
                        break;
                    case '\r':
                        break;
                    case '\n':
                        fields.Add(field.ToString());
                        field.Clear();
                        if (sawAny || fields.Count > 1)
                            yield return fields.ToArray();
                        fields.Clear();
                        sawAny = false;
                        break;
                    default:
                        field.Append(c);
                        sawAny = true;
                        break;
                }
            }
        }

        if (sawAny || field.Length > 0 || fields.Count > 0)
        {
            fields.Add(field.ToString());
            yield return fields.ToArray();
        }
    }

    /// <summary>Maps a header row to a case-insensitive name→index lookup, BOM-tolerant.</summary>
    public static Dictionary<string, int> HeaderIndex(string[] header)
    {
        var map = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        for (int i = 0; i < header.Length; i++)
        {
            var name = header[i].Trim().TrimStart('\uFEFF');
            if (name.Length > 0 && !map.ContainsKey(name))
                map[name] = i;
        }
        return map;
    }
}
