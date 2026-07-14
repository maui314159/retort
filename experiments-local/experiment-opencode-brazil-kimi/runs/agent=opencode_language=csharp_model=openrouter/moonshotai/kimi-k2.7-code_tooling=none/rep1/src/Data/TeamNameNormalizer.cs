/*
 * Brazilian Soccer MCP Server - Team Name Normalization
 *
 * The datasets use different naming conventions for the same team:
 *   - "Palmeiras-SP" vs "Palmeiras"
 *   - "Sport Club Corinthians Paulista" vs "Corinthians"
 *   - State suffixes and accented characters vary by source.
 *
 * This class normalizes team names to a canonical form so queries match
 * records across all CSV files.
 */
using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Data;

public static class TeamNameNormalizer
{
    /// <summary>
    /// Returns a canonical team name suitable for cross-dataset comparison.
    /// </summary>
    public static string Normalize(string name)
    {
        if (string.IsNullOrWhiteSpace(name))
            return string.Empty;

        var normalized = name.Trim();

        // Remove parenthetical region codes like "Nacional (URU)".
        normalized = Regex.Replace(normalized, @"\s*\([^)]*\)\s*", " ");

        // Strip common suffixes added by some datasets: "-SP", "-RJ", etc.
        normalized = Regex.Replace(normalized, @"-\s*[A-Z]{2}\s*$", string.Empty);

        // Remove known prefixes/full-name noise.
        normalized = Regex.Replace(normalized, @"^Boavista Sport Club \(antigo Esporte Clube Barreira\)\s*-?\s*", "Boavista ");

        // Remove accents and diacritics.
        normalized = RemoveDiacritics(normalized);

        // Remove non-alphanumeric characters and collapse whitespace.
        normalized = Regex.Replace(normalized, @"[^a-zA-Z0-9\s]", " ");
        normalized = Regex.Replace(normalized, @"\s+", " ").Trim();

        return normalized.ToLowerInvariant();
    }

    /// <summary>
    /// Checks whether two team names refer to the same team after normalization.
    /// </summary>
    public static bool AreSame(string? a, string? b)
        => Normalize(a ?? string.Empty) == Normalize(b ?? string.Empty);

    private static string RemoveDiacritics(string text)
    {
        var normalized = text.Normalize(NormalizationForm.FormD);
        var builder = new StringBuilder();
        foreach (var c in normalized)
        {
            var category = CharUnicodeInfo.GetUnicodeCategory(c);
            if (category != UnicodeCategory.NonSpacingMark)
                builder.Append(c);
        }
        return builder.ToString().Normalize(NormalizationForm.FormC);
    }
}
