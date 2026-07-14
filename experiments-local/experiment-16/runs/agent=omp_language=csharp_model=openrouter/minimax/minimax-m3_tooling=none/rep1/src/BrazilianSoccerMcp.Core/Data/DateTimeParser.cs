// =============================================================================
// Brazilian Soccer MCP Server
// File: DateTimeParser.cs
// Purpose: Robust parsing for the multiple date formats found across the
//          bundled datasets (ISO, Brazilian DD/MM/YYYY, with optional time,
//          some with extra quotes from CsvHelper).
// Context: Every loader funnels dates through ParseDate so that null is
//          returned for unparseable values instead of throwing -- this keeps
//          a single bad row from aborting a 10k-row import.
// =============================================================================

using System.Globalization;

namespace BrazilianSoccerMcp.Core.Data;

internal static class DateTimeParser
{
    // Try the most specific formats first. Each tuple is (format, provider).
    private static readonly (string Format, IFormatProvider Provider)[] Formats =
    {
        ("yyyy-MM-dd HH:mm:ss",  CultureInfo.InvariantCulture),
        ("yyyy-MM-dd",           CultureInfo.InvariantCulture),
        ("dd/MM/yyyy",           CultureInfo.InvariantCulture),
        ("dd/MM/yyyy HH:mm:ss",  CultureInfo.InvariantCulture),
        ("MM/dd/yyyy",           CultureInfo.InvariantCulture),
        ("yyyy/MM/dd",           CultureInfo.InvariantCulture),
    };

    /// <summary>
    /// Try to parse a free-form date string. Returns false on failure.
    /// </summary>
    public static bool TryParse(string? raw, out DateTime result)
    {
        result = default;
        if (string.IsNullOrWhiteSpace(raw))
            return false;

        var s = raw.Trim().Trim('"');

        if (DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.AssumeLocal, out result))
            return true;

        foreach (var (fmt, prov) in Formats)
        {
            if (DateTime.TryParseExact(s, fmt, prov, DateTimeStyles.AssumeLocal, out result))
                return true;
        }

        return false;
    }

    /// <summary>
    /// Convenience: parse and fall back to <paramref name="fallback"/> on
    /// failure. Used when a date is best-effort metadata, not load-bearing.
    /// </summary>
    public static DateTime ParseOrDefault(string? raw, DateTime fallback) =>
        TryParse(raw, out var v) ? v : fallback;
}
