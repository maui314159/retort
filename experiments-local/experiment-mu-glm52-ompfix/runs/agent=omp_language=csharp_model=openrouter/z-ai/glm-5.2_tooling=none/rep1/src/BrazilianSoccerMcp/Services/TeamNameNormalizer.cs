// Brazilian Soccer MCP Server - Team name normalization
//
// Context: The five match datasets spell the same team in many ways:
//   - With a Brazilian state suffix:        "Palmeiras-SP", "América - MG"
//   - With a country in parentheses:        "Nacional (URU)", "Barcelona-EQU"
//   - Accented vs. plain:                   "Atlético-MG" vs "Atletico-MG"
//   - Dotted/abbreviated forms:             "A.b.c. - RN" vs "Abc - RN"
//   - With extra parenthetical notes:        "Boavista Sport Club (antigo ...)"
//   - Full vs. short:                       "Sport Club Corinthians Paulista"
// To answer cross-dataset questions (e.g. "all Palmeiras matches") we derive a
// canonical key that is lowercase, accent-free, punctuation-free, and stripped
// of state suffixes, so differently-spelled variants collapse to one key.
// The display name keeps accents but drops the noisy state/country suffix.

using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Services;

/// <summary>
/// Normalizes Brazilian soccer team names across the heterogeneous datasets.
/// </summary>
public static class TeamNameNormalizer
{
    // Trailing " - XX" or "-XXX" where XX is 2-3 uppercase letters (Brazilian
    // state code like SP, or a 3-letter country code like EQU for Ecuador).
    private static readonly Regex StateSuffix =
        new(@"\s*-\s*[A-Z]{2,3}\s*$", RegexOptions.Compiled);

    // Parenthetical content, e.g. "(URU)", "(antigo Esporte Clube Barreira)".
    private static readonly Regex Parenthetical =
        new(@"\s*\([^)]*\)", RegexOptions.Compiled);

    // Strips the trailing 2-letter Brazilian state suffix from a display name.
    public static string StripSuffix(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return string.Empty;
        var name = raw.Trim();
        // Remove parenthetical qualifiers from the display form but keep the
        // base name; "Nacional (URU)" -> "Nacional".
        name = Parenthetical.Replace(name, "").Trim();
        name = StateSuffix.Replace(name, "").Trim();
        return name;
    }

    /// <summary>
    /// Canonical, match-friendly key: lowercase, accent-free, punctuation-free,
    /// whitespace-collapsed, state suffix removed. Two teams that refer to the
    /// same entity produce identical keys.
    /// </summary>
    public static string CanonicalKey(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return string.Empty;

        var name = StripSuffix(raw);

        // Decompose accented characters into base + combining marks, then drop
        // the combining marks so "Atlético" and "Atletico" become equal.
        var normalized = name.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(normalized.Length);
        foreach (var ch in normalized)
        {
            var category = CharUnicodeInfo.GetUnicodeCategory(ch);
            if (category != UnicodeCategory.NonSpacingMark)
                sb.Append(ch);
        }
        name = sb.ToString();

        // Lowercase, remove dots/apostrophes used in abbreviations ("A.b.c." ->
        // "abc"), replace hyphens with spaces, collapse whitespace.
        name = name.ToLowerInvariant();
        name = name.Replace(".", "").Replace("'", "").Replace("-", " ");
        name = Regex.Replace(name, @"\s+", " ").Trim();

        return name;
    }
}
