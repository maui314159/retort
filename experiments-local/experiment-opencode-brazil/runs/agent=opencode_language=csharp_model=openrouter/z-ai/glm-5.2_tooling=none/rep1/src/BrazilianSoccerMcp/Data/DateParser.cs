// Context block
// File: Data/DateParser.cs
// Purpose: Parse the date formats found across the Kaggle datasets for the Brazilian
// Soccer MCP server. Three formats appear: ISO with time ("2012-05-19 18:30:00"),
// ISO date only ("2023-09-24"), and Brazilian day-first format ("29/03/2003"). The
// parser tries each format with the invariant culture before falling back to a
// machine-local parse. Invalid dates return DateTime.MinValue so callers can filter
// them out rather than throwing during bulk load.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

namespace BrazilianSoccerMcp.Data;

/// <summary>Parses dates from the bundled CSV files.</summary>
public sealed class DateParser
{
    private static readonly string[] Formats =
    {
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd HH:mm",
        "yyyy-MM-dd",
        "dd/MM/yyyy",
        "dd/MM/yyyy HH:mm:ss",
        "dd/MM/yyyy HH:mm",
        "MM/dd/yyyy",
    };

    /// <summary>Parses a date string using the known formats.</summary>
    public DateTime Parse(string input)
    {
        if (string.IsNullOrWhiteSpace(input))
        {
            return DateTime.MinValue;
        }
        var v = input.Trim().Trim('"');
        if (DateTime.TryParseExact(v, Formats, System.Globalization.CultureInfo.InvariantCulture,
            System.Globalization.DateTimeStyles.AllowWhiteSpaces | System.Globalization.DateTimeStyles.AssumeLocal, out var dt))
        {
            return dt;
        }
        if (DateTime.TryParse(v, System.Globalization.CultureInfo.InvariantCulture,
            System.Globalization.DateTimeStyles.AllowWhiteSpaces, out dt))
        {
            return dt;
        }
        return DateTime.MinValue;
    }

    /// <summary>True when the parsed value is a real date.</summary>
    public bool IsValid(DateTime value) => value != DateTime.MinValue;
}
