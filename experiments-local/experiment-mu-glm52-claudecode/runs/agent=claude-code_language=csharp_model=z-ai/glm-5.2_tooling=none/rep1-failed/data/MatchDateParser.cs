// =============================================================================
// File: Data/MatchDateParser.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   The match CSVs mix date formats:
//     - ISO with time : "2012-05-19 18:30:00"  (Brasileirao/Cup/Libertadores)
//     - ISO date      : "2023-09-24"          (BR-Football-Dataset)
//     - Brazilian     : "29/03/2003"          (novo_campeonato_brasileiro)
//   This parser picks the first format that successfully matches.
// =============================================================================
namespace BrazilianSoccerMcp.Data;

using System;
using System.Globalization;

public static class MatchDateParser
{
    private static readonly string[] Formats =
    {
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd",
        "dd/MM/yyyy",
        "dd/MM/yyyy HH:mm:ss",
        "yyyy-MM-ddTHH:mm:ss",
    };

    /// <summary>Tries to parse a match date string, returning null on failure.</summary>
    public static DateTime? TryParse(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var s = raw.Trim();
        if (DateTime.TryParseExact(s, Formats, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                out var dt))
            return dt;
        if (DateTime.TryParse(s, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                out var loose))
            return loose;
        return null;
    }

    /// <summary>Parses a year integer, returns null if empty/invalid.</summary>
    public static int? TryParseSeason(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        if (int.TryParse(raw.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var y))
            return y;
        // Fallback: try to extract a 4-digit year from a date-ish string.
        if (DateTime.TryParse(raw, CultureInfo.InvariantCulture, DateTimeStyles.None, out var d))
            return d.Year;
        return null;
    }
}
