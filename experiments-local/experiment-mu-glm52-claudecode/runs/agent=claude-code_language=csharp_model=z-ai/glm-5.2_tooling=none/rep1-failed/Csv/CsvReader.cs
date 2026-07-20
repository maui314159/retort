// =============================================================================
// File: Csv/CsvReader.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server (demo / non-commercial).
//   A minimal, allocation-friendly CSV reader used to ingest the six Kaggle
//   datasets that back this MCP server (5 match CSV files + 1 FIFA player CSV).
//
// Why a hand-rolled reader instead of CsvHelper?
//   - Zero extra NuGet dependencies for the core data layer.
//   - The FIFA dataset ships with a BOM and an unnamed leading index column,
//     which trips up naïve header-based mapping; reading positional columns
//     avoids that entirely.
//   - All source CSVs are well-formed RFC-4180 style (quoted fields, doubled
//     quotes for escaping, CRLF/LF line endings).
//
// Behaviour:
//   - Strips a leading UTF-8 / UTF-16 BOM.
//   - Honours double-quoted fields; a "" inside a quoted field is a literal ".
//   - Treats \r\n, \n, and \r as record separators.
//   - Returns rows as string[] arrays (positional access by callers).
// =============================================================================
namespace BrazilianSoccerMcp.Csv;

using System.Collections.Generic;
using System.IO;
using System.Text;

/// <summary>Reads RFC-4180-style CSV files into positional string arrays.</summary>
public static class CsvReader
{
    /// <summary>Reads every record from <paramref name="path"/> as a positional array.</summary>
    public static List<string[]> ReadAll(string path)
    {
        var rows = new List<string[]>(64);
        var bytes = File.ReadAllBytes(path);
        var text = DecodeText(bytes);
        ParseInto(text, rows);
        return rows;
    }

    private static string DecodeText(byte[] bytes)
    {
        // Strip BOM.
        if (bytes.Length >= 3 && bytes[0] == 0xEF && bytes[1] == 0xBB && bytes[2] == 0xBF)
            return Encoding.UTF8.GetString(bytes, 3, bytes.Length - 3);
        if (bytes.Length >= 2 && bytes[0] == 0xFF && bytes[1] == 0xFE)
            return Encoding.Unicode.GetString(bytes, 2, bytes.Length - 2);
        if (bytes.Length >= 2 && bytes[0] == 0xFE && bytes[1] == 0xFF)
            return Encoding.BigEndianUnicode.GetString(bytes, 2, bytes.Length - 2);
        return Encoding.UTF8.GetString(bytes);
    }

    private static void ParseInto(string text, List<string[]> rows)
    {
        var field = new StringBuilder(64);
        var record = new List<string>(32);
        var inQuotes = false;
        var fieldStarted = false;
        var hasContent = false;

        for (int i = 0; i < text.Length; i++)
        {
            char c = text[i];

            if (inQuotes)
            {
                if (c == '"')
                {
                    // Doubled quote == literal " inside a quoted field.
                    if (i + 1 < text.Length && text[i + 1] == '"')
                    {
                        field.Append('"');
                        i++;
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
            else if (c == '"')
            {
                inQuotes = true;
                fieldStarted = true;
                hasContent = true;
            }
            else if (c == ',')
            {
                record.Add(field.ToString());
                field.Clear();
                fieldStarted = false;
                hasContent = true;
            }
            else if (c == '\r' || c == '\n')
            {
                // Normalise CRLF / CR / LF to a single record end.
                if (c == '\r' && i + 1 < text.Length && text[i + 1] == '\n')
                    i++;
                FlushRecord(record, field, fieldStarted, rows, ref hasContent);
            }
            else
            {
                field.Append(c);
                fieldStarted = true;
                hasContent = true;
            }
        }

        // Flush trailing record if the file did not end with a newline.
        if (hasContent || fieldStarted)
            FlushRecord(record, field, fieldStarted, rows, ref hasContent);
    }

    private static void FlushRecord(
        List<string> record, StringBuilder field, bool fieldStarted,
        List<string[]> rows, ref bool hasContent)
    {
        record.Add(field.ToString());
        field.Clear();
        if (hasContent)
        {
            // Skip completely empty trailing lines without fieldStarted.
            rows.Add(record.ToArray());
        }
        record.Clear();
        hasContent = false;
        fieldStarted = false;
    }
}
