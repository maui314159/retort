// BrazilianSoccerMcp.Core / Normalization / DateParser.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. TASK.md "Data Quality Notes -> Date
// Formats" lists three date shapes across the CSVs:
//   1. ISO with time:        "2012-05-19 18:30:00"
//   2. ISO date only:        "2023-09-24"
//   3. Brazilian DD/MM/YYYY: "29/03/2003"
// Purpose: One tolerant parser that returns a nullable DateTime for any of these
// (and an ISO date+time with no seconds). Null on failure so callers can keep
// rows whose date is unparseable instead of dropping them silently.
// Design: CultureInfo.InvariantCulture for the ISO family; the Brazilian format
// needs an explicit culture with "/" separator so MM/DD reads as day-first.
// -----------------------------------------------------------------------------

using System.Globalization;

namespace BrazilianSoccerMcp.Core.Normalization;

/// <summary>
/// Tolerant multi-format date parser for the Brazilian soccer CSVs.
/// </summary>
public static class DateParser
{
    // Ordered most-specific first. "yyyy-MM-dd HH:mm:ss" must precede "yyyy-MM-dd"
    // so a value with a time component doesn't lose precision.
    private static readonly string[] Formats =
    {
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd HH:mm",
        "yyyy-MM-dd",
        "dd/MM/yyyy",
        "dd/MM/yyyy HH:mm:ss",
        "dd/MM/yyyy HH:mm",
        "d/M/yyyy",
        "yyyy-MM-ddTHH:mm:ss"
    };

    /// <summary>
    /// Parses <paramref name="raw"/> trying every known format. Returns null on
    /// failure (never throws).
    /// </summary>
    public static DateTime? Parse(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return null;

        var value = raw.Trim();

        // Fast path for ISO-style values.
        if (DateTime.TryParseExact(value, Formats, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                out var dt))
        {
            return dt;
        }

        // Fall back to culture-aware parse for the Brazilian locale, then invariant.
        if (DateTime.TryParse(value, new CultureInfo("pt-BR"),
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out dt))
            return dt;

        if (DateTime.TryParse(value, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out dt))
            return dt;

        return null;
    }
}
