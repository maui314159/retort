using System.Globalization;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Parses the three date formats found in the datasets:
/// ISO with time ("2012-05-19 18:30:00"), ISO date ("2023-09-24") and
/// Brazilian format ("29/03/2003"). Returns null instead of throwing.
/// </summary>
public static class FlexibleDateParser
{
    private static readonly string[] Formats =
    {
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd HH:mm",
        "yyyy-MM-dd",
        "dd/MM/yyyy HH:mm:ss",
        "dd/MM/yyyy HH:mm",
        "dd/MM/yyyy",
    };

    public static DateTime? Parse(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;
        var s = raw.Trim().Trim('"');
        if (s.Length == 0 || s is "NA" or "NaN" or "null")
            return null;

        if (DateTime.TryParseExact(s, Formats, CultureInfo.InvariantCulture, DateTimeStyles.None, out var exact))
            return exact;

        // Lenient fallback for anything unexpected.
        if (DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.None, out var loose))
            return loose;

        return null;
    }

    /// <summary>Parses a user-supplied date for query filters (ISO or Brazilian formats).</summary>
    public static DateTime? ParseFilter(string? raw) => Parse(raw);
}
