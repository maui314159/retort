// -----------------------------------------------------------------------------
// File: Data/CsvFields.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Tolerant scalar parsers shared by every CSV loader. The source files are
//   inconsistent: goals appear as "2" (int) in some files and "1.0" (float) in
//   BR-Football; dates are ISO ("2023-09-24"), Brazilian ("29/03/2003"), or ISO
//   with time ("2012-05-19 18:30:00"); a handful of fields are "NA" or blank.
//
//   These helpers never throw on malformed input — they return null so a single
//   bad cell degrades to "unknown" instead of aborting the whole load. All
//   parsing is culture-invariant (the projects set InvariantGlobalization).
// -----------------------------------------------------------------------------

using System.Globalization;

namespace BrazilianSoccer.Core.Data;

/// <summary>Forgiving primitive parsers for heterogeneous CSV cells.</summary>
internal static class CsvFields
{
    private static readonly string[] DateFormats =
    {
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd",
        "dd/MM/yyyy",
        "dd/MM/yyyy HH:mm:ss",
        "yyyy-MM-ddTHH:mm:ss",
    };

    /// <summary>Parses an integer that may be written as a float ("3.0") or blank/"NA".</summary>
    public static int? ParseInt(string? raw)
    {
        if (IsBlank(raw))
            return null;

        var s = raw!.Trim();
        if (int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i))
            return i;

        // Tolerate float-formatted integers like "2.0".
        if (double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var d)
            && !double.IsNaN(d))
            return (int)Math.Round(d);

        return null;
    }

    /// <summary>Parses a date in any of the formats the datasets use; null on failure.</summary>
    public static DateTime? ParseDate(string? raw)
    {
        if (IsBlank(raw))
            return null;

        var s = raw!.Trim();
        if (DateTime.TryParseExact(s, DateFormats, CultureInfo.InvariantCulture,
                DateTimeStyles.None, out var exact))
            return exact;

        // Last resort: invariant general parse (handles odd-but-valid variants).
        if (DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.None, out var any))
            return any;

        return null;
    }

    /// <summary>Returns the trimmed string, or null when blank or the sentinel "NA".</summary>
    public static string? Clean(string? raw)
        => IsBlank(raw) ? null : raw!.Trim();

    private static bool IsBlank(string? raw)
        => string.IsNullOrWhiteSpace(raw)
           || raw!.Trim().Equals("NA", StringComparison.OrdinalIgnoreCase);
}
