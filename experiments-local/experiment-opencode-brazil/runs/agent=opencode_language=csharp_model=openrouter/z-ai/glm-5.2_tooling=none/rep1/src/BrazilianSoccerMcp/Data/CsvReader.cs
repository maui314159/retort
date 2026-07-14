// Context block
// File: Data/CsvReader.cs
// Purpose: Lightweight RFC4180-style CSV parser used by the Brazilian Soccer MCP server.
// We avoid third-party CSV dependencies so the project builds offline. The reader
// supports UTF-8 encoded files, quoted fields that may contain commas and newlines,
// doubled double-quotes ("") as an escape for a literal quote inside a quoted field,
// and an optional header row. It returns rows as string arrays so callers can map
// columns by header name without re-parsing the file.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

using System.Text;
using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Data;

/// <summary>A minimal CSV reader that handles quoted fields and escaped quotes.</summary>
public static class CsvReader
{
    /// <summary>Reads a CSV file from disk with UTF-8 encoding.</summary>
    /// <param name="path">Absolute path to the CSV file.</param>
    /// <param name="hasHeader">When true, the first row is returned separately.</param>
    /// <returns>A tuple containing the optional header and the data rows.</returns>
    public static (string[]? Header, List<string[]> Rows) ReadFile(string path, bool hasHeader = true)
    {
        if (!File.Exists(path))
        {
            throw new FileNotFoundException("CSV file not found: " + path, path);
        }

        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        using var reader = new StreamReader(stream, System.Text.Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        return Read(reader, hasHeader);
    }

    /// <summary>Reads CSV content from any text reader.</summary>
    public static (string[]? Header, List<string[]> Rows) Read(TextReader reader, bool hasHeader)
    {
        string[]? header = null;
        var rows = new List<string[]>();
        var field = new StringBuilder();
        var fields = new List<string>();
        var inQuotes = false;
        var fieldStarted = false;
        var rowHasData = false;
        int ch;

        while ((ch = reader.Read()) != -1)
        {
            rowHasData = true;
            char c = (char)ch;

            if (inQuotes)
            {
                if (c == '"')
                {
                    var next = reader.Peek();
                    if (next == '"')
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
                    // Swallow; the following \n (or EOF) ends the row.
                    var peek = reader.Peek();
                    if (peek == '\n')
                    {
                        reader.Read();
                    }
                    goto case '\n';
                case '\n':
                    fields.Add(field.ToString());
                    field.Clear();
                    fieldStarted = false;
                    FinalizeRow();
                    break;
                default:
                    field.Append(c);
                    fieldStarted = true;
                    break;
            }
        }

        if (rowHasData || field.Length > 0 || fields.Count > 0 || fieldStarted)
        {
            fields.Add(field.ToString());
            field.Clear();
            FinalizeRow();
        }

        return (header, rows);

        void FinalizeRow()
        {
            var row = fields.ToArray();
            fields.Clear();
            if (row.Length == 0)
            {
                return;
            }
            if (row.Length == 1 && string.IsNullOrWhiteSpace(row[0]))
            {
                return;
            }
            if (hasHeader && header is null)
            {
                header = row;
            }
            else
            {
                rows.Add(row);
            }
            rowHasData = false;
        }
    }

    /// <summary>Looks up a column index by header name (case-insensitive, trimmed).</summary>
    public static int IndexOf(string[]? header, string name)
    {
        if (header is null)
        {
            return -1;
        }
        for (int i = 0; i < header.Length; i++)
        {
            if (string.Equals(header[i].Trim(), name, StringComparison.OrdinalIgnoreCase))
            {
                return i;
            }
        }
        return -1;
    }

    /// <summary>Returns the value at the given column, or null when the column is missing.</summary>
    public static string? At(string[] row, int index)
    {
        if (index < 0 || index >= row.Length)
        {
            return null;
        }
        var v = row[index];
        return v;
    }
}
