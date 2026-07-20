// BrazilianSoccerMcp.Core / Data / ParseHelpers.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. The CSVs are messy: goals appear as "2",
// "1.0", "" (Libertadores blanks), and "2\n"; season sometimes has stray spaces;
// fifa ratings appear as "88+2". These helpers give the loaders a uniform, throw-
// free path from raw CSV strings into the nullable typed model fields.
// -----------------------------------------------------------------------------

using System.Globalization;

namespace BrazilianSoccerMcp.Core.Data;

/// <summary>Throw-free primitive parsers used by the CSV loaders.</summary>
internal static class ParseHelpers
{
    /// <summary>
    /// Parses a goal cell. Accepts int ("2"), float ("1.0"), and blank/null.
    /// Returns null for blank/unparseable values so a missing score is never
    /// misreported as a 0-0.
    /// </summary>
    public static int? ParseGoal(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var v = raw.Trim();
        if (v.Contains('+')) v = v.Split('+')[0];
        if (int.TryParse(v, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i))
            return i;
        if (double.TryParse(v, NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
            return (int)d;
        return null;
    }

    /// <summary>
    /// Parses a FIFA-style rating cell that may be "88" or "88+2". Returns the base
    /// value before the plus sign, or null when blank/unparseable.
    /// </summary>
    public static int? ParseRating(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var v = raw.Trim();
        if (v.Contains('+')) v = v.Split('+')[0];
        return int.TryParse(v, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i) ? i : null;
    }

    /// <summary>Trims and int-parses; null when blank/unparseable.</summary>
    public static int? ParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        return int.TryParse(raw.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var i) ? i : null;
    }

    /// <summary>Trims the cell; returns null when blank.</summary>
    public static string? ParseText(string? raw) =>
        string.IsNullOrWhiteSpace(raw) ? null : raw.Trim();
}
