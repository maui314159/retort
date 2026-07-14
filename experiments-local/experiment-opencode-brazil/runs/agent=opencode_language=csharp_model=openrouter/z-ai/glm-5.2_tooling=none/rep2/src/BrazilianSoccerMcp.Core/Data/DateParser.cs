// BrazilianSoccerMcp.Core - Multi-format date parsing.
// The match CSVs mix:
//   * ISO dates with time ("2012-05-19 18:30:00")
//   * ISO date only ("2023-09-24")
//   * Brazilian DD/MM/YYYY ("29/03/2003")
// This parser handles all three (and a few tolerant variants) and falls back
// gracefully so a single malformed row never aborts a whole dataset load.
using System.Globalization;

namespace BrazilianSoccerMcp.Core.Data;

/// <summary>Parses the date formats found across the match CSV files.</summary>
public static class DateParser
{
    private static readonly string[] IsoFormats =
    {
        "yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd H:mm:ss",
        "yyyy-MM-dd HH:mm", "yyyy-MM-dd"
    };

    private static readonly string[] BrFormats =
    {
        "dd/MM/yyyy", "d/M/yyyy", "dd/MM/yyyy HH:mm", "d/M/yyyy HH:mm"
    };

    public static DateTime? Parse(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var s = raw.Trim().Trim('"');

        if (DateTime.TryParseExact(s, IsoFormats, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                out var iso))
            return iso;

        if (DateTime.TryParseExact(s, BrFormats, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                out var br))
            return br;

        // Final fallback: culture-invariant tolerant parse.
        if (DateTime.TryParse(s, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                out var loose))
            return loose;

        return null;
    }

    public static int? SeasonFromYear(string? raw)
    {
        if (int.TryParse(raw?.Trim(), out var y)) return y;
        return null;
    }
}
