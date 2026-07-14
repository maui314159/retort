// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    CsvReader.cs
// Project: BrazilianSoccer.Core
// Purpose: Minimal, allocation-conscious RFC 4180 CSV reader used to load the
//          Kaggle Brazilian-soccer datasets. The provided CSVs mix quoted and
//          unquoted fields, embedded commas, UTF-8 accented text (São, Grêmio)
//          and a UTF-8 BOM on fifa_data.csv, so a hand-rolled parser is used to
//          handle quotes/escaping/BOM deterministically without a third-party
//          dependency.
// Notes:   - Fields may be quoted with double quotes; "" inside a quoted field
//            is an escaped quote.
//          - The reader streams rows lazily and yields each record as a
//            Dictionary keyed by the (trimmed) header names.
//          - The leading UTF-8 BOM is stripped from the first header cell.
// =============================================================================

using System.Text;

namespace BrazilianSoccer.Core.Csv;

/// <summary>
/// Streaming RFC 4180 CSV reader. Parses quoted fields, escaped quotes and
/// embedded newlines, and maps each row onto its header columns.
/// </summary>
public static class CsvReader
{
    /// <summary>
    /// Reads a CSV file and yields one dictionary (header -> value) per data row.
    /// </summary>
    public static IEnumerable<IReadOnlyDictionary<string, string>> ReadFile(string path)
    {
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        // detectEncodingFromByteOrderMarks handles the BOM on fifa_data.csv.
        using var reader = new StreamReader(stream, Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        foreach (var row in Read(reader))
            yield return row;
    }

    /// <summary>
    /// Reads CSV content from an arbitrary <see cref="TextReader"/>. Exposed for
    /// testing with in-memory data.
    /// </summary>
    public static IEnumerable<IReadOnlyDictionary<string, string>> Read(TextReader reader)
    {
        string[]? headers = null;
        foreach (var fields in ReadRecords(reader))
        {
            if (headers is null)
            {
                headers = fields;
                // Strip a stray BOM that may survive on the first header cell.
                if (headers.Length > 0)
                    headers[0] = headers[0].TrimStart('\uFEFF');
                for (var i = 0; i < headers.Length; i++)
                    headers[i] = headers[i].Trim();
                continue;
            }

            var record = new Dictionary<string, string>(headers.Length, StringComparer.OrdinalIgnoreCase);
            for (var i = 0; i < headers.Length; i++)
                record[headers[i]] = i < fields.Length ? fields[i] : string.Empty;
            yield return record;
        }
    }

    /// <summary>
    /// Tokenises the stream into raw records (each a list of field strings),
    /// honouring quotes, escaped quotes ("") and newlines embedded in quotes.
    /// </summary>
    private static IEnumerable<string[]> ReadRecords(TextReader reader)
    {
        var fields = new List<string>();
        var field = new StringBuilder();
        var inQuotes = false;
        var fieldStarted = false;
        var recordHasContent = false;

        int read;
        while ((read = reader.Read()) != -1)
        {
            var c = (char)read;

            if (inQuotes)
            {
                if (c == '"')
                {
                    // Peek for an escaped quote.
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
                    recordHasContent = true;
                    break;
                case ',':
                    fields.Add(field.ToString());
                    field.Clear();
                    fieldStarted = false;
                    recordHasContent = true;
                    break;
                case '\r':
                    // Swallow CR; the following LF terminates the record.
                    break;
                case '\n':
                    fields.Add(field.ToString());
                    field.Clear();
                    if (recordHasContent || fields.Count > 1)
                        yield return fields.ToArray();
                    fields.Clear();
                    fieldStarted = false;
                    recordHasContent = false;
                    break;
                default:
                    field.Append(c);
                    fieldStarted = true;
                    recordHasContent = true;
                    break;
            }
        }

        // Flush the trailing record when the file does not end with a newline.
        if (fieldStarted || field.Length > 0 || fields.Count > 0)
        {
            fields.Add(field.ToString());
            if (recordHasContent || fields.Count > 1)
                yield return fields.ToArray();
        }
    }
}
