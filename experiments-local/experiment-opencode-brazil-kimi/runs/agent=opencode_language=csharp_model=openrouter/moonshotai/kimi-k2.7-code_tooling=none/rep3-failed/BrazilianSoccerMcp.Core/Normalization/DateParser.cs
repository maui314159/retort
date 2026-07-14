// <copyright file="DateParser.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Handles the heterogeneous date formats found in the datasets.
//
// Supported formats include:
//   - "2023-09-24 19:00:00"
//   - "2012-05-19 18:30:00"
//   - "29/03/2003" (Brazilian short date)
// </copyright>
namespace BrazilianSoccerMcp.Core.Normalization;

/// <summary>
/// Parses dates from multiple input formats used in the source CSVs.
/// </summary>
public static class DateParser
{
    private static readonly string[] Formats =
    {
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd HH:mm",
        "yyyy-MM-dd",
        "dd/MM/yyyy",
        "dd/MM/yyyy HH:mm",
        "MM/dd/yyyy",
        "yyyy-MM-ddTHH:mm:ss",
        "yyyy-MM-ddTHH:mm:ssZ",
        "yyyy-MM-ddTHH:mm:ss.fffffffZ",
        "yyyy/MM/dd"
    };

    /// <summary>
    /// Attempts to parse a raw date string and time string into a DateTime.
    /// </summary>
    public static DateTime? Parse(string? rawDate, string? rawTime = null)
    {
        var combined = Combine(rawDate, rawTime);
        if (string.IsNullOrWhiteSpace(combined))
            return null;

        if (DateTime.TryParseExact(combined, Formats, System.Globalization.CultureInfo.InvariantCulture,
            System.Globalization.DateTimeStyles.None, out var dt))
        {
            return dt;
        }

        if (DateTime.TryParse(combined, System.Globalization.CultureInfo.InvariantCulture,
            System.Globalization.DateTimeStyles.None, out dt))
        {
            return dt;
        }

        return null;
    }

    /// <summary>
    /// Parses a season value (year). Falls back to extracting the year from a date.
    /// </summary>
    public static int? ParseSeason(string? rawSeason, DateTime? date = null)
    {
        if (int.TryParse(rawSeason, out var season))
            return season;

        return date?.Year;
    }

    private static string Combine(string? rawDate, string? rawTime)
    {
        var datePart = (rawDate ?? string.Empty).Trim();
        var timePart = (rawTime ?? string.Empty).Trim();

        if (string.IsNullOrEmpty(datePart))
            return timePart;

        if (string.IsNullOrEmpty(timePart))
            return datePart;

        return $"{datePart} {timePart}";
    }
}
