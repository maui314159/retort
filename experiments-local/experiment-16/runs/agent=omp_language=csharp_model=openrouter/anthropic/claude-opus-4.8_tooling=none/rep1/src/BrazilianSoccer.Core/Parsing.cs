// =============================================================================
// Context: Brazilian Soccer MCP Server — value parsing helpers.
//
// Centralizes tolerant parsing of the messy cell values found across the CSVs:
// goals stored as "NA" / "2" / "2.0", dates in ISO ("2023-09-24"),
// ISO-with-time ("2012-05-19 18:30:00"), Brazilian ("29/03/2003"), and dotted
// ("2003.01.0001" ids notwithstanding). Returns null on anything unparseable so
// callers can decide whether a missing value disqualifies a row.
// =============================================================================
using System.Globalization;

namespace BrazilianSoccer.Core;

public static class Parsing
{
    private static readonly string[] DateFormats =
    {
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd",
        "dd/MM/yyyy",
        "yyyy/MM/dd",
        "dd/MM/yyyy HH:mm:ss",
        "MM/dd/yyyy",
    };

    /// <summary>Parse a goal count tolerating "NA", blanks, and decimal forms like "2.0".</summary>
    public static int? Goal(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;
        var s = raw.Trim();
        if (s.Equals("NA", StringComparison.OrdinalIgnoreCase) || s == "-")
            return null;
        if (int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i))
            return i;
        if (double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
            return (int)Math.Round(d);
        return null;
    }

    /// <summary>Parse an integer (season, age, etc.) tolerating decimals and blanks.</summary>
    public static int? Int(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;
        var s = raw.Trim();
        if (int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i))
            return i;
        if (double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
            return (int)Math.Round(d);
        return null;
    }

    /// <summary>Parse a date from any of the formats present in the datasets; null when absent/invalid.</summary>
    public static DateOnly? Date(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;
        var s = raw.Trim();

        // Fast path: take the date portion before any space (drops the time).
        if (DateTime.TryParseExact(s, DateFormats, CultureInfo.InvariantCulture,
                DateTimeStyles.AllowWhiteSpaces, out var dt))
            return DateOnly.FromDateTime(dt);

        if (DateTime.TryParse(s, CultureInfo.InvariantCulture,
                DateTimeStyles.AllowWhiteSpaces, out dt))
            return DateOnly.FromDateTime(dt);

        return null;
    }
}
