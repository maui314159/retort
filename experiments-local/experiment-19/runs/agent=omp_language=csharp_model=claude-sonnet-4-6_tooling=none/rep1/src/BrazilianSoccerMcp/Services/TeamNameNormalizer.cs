using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Services;

/// <summary>
/// Normalises team names for matching and grouping.
///
/// Two key concepts:
/// - <see cref="Normalize"/>          → accent-stripped, lowercased; state suffix KEPT.
///                                       Use as the grouping key in standings so teams with
///                                       the same root but different states stay separate
///                                       (e.g. "atletico-mg" ≠ "atletico-pr").
/// - <see cref="NormalizeForSearch"/> → state suffix ALSO stripped.
///                                       Use for user query matching and dedup across datasets.
/// </summary>
public static partial class TeamNameNormalizer
{
    // "-SP", "-MG" etc — matches BEFORE lowercasing (original case)
    [GeneratedRegex(@"-[A-Z]{2}$")]
    private static partial Regex UpperStateSuffixRegex();

    // "-sp", "-mg" etc — matches AFTER lowercasing
    [GeneratedRegex(@"-[a-z]{2}$")]
    private static partial Regex LowerStateSuffixRegex();

    // Parenthesised qualifiers like "(antigo Esporte Clube Barreira)"
    [GeneratedRegex(@"\s*\(.*?\)\s*")]
    private static partial Regex ParenthesisRegex();

    // "- RJ" style suffix with surrounding spaces (before lowercasing)
    [GeneratedRegex(@"\s+-\s+[A-Z]{2}\s*$")]
    private static partial Regex SpacedUpperStateSuffixRegex();

    // "- rj" style suffix with surrounding spaces (after lowercasing)
    [GeneratedRegex(@"\s+-\s+[a-z]{2}\s*$")]
    private static partial Regex SpacedLowerStateSuffixRegex();

    /// <summary>
    /// Normalise to lowercase ASCII, stripping parenthetical qualifiers and
    /// accent marks — but KEEPING the state suffix (e.g. "-mg", "-rj").
    /// Use this as the team key for standings grouping.
    /// </summary>
    public static string Normalize(string name)
    {
        if (string.IsNullOrWhiteSpace(name)) return "";
        name = ParenthesisRegex().Replace(name, " ").Trim();
        name = SpacedUpperStateSuffixRegex().Replace(name, "").Trim();  // strip "- RJ" before lowercase
        name = RemoveDiacritics(name);
        return name.ToLowerInvariant().Trim();
        // Note: "-SP" suffix is preserved as "-sp" in the output
    }

    /// <summary>
    /// Like <see cref="Normalize"/> but also strips the state suffix.
    /// Use for user-facing search queries and cross-dataset deduplication.
    /// </summary>
    public static string NormalizeForSearch(string name)
    {
        var n = Normalize(name);
        // Strip lowercase state suffix (since Normalize already lowercased)
        n = LowerStateSuffixRegex().Replace(n, "").Trim();
        // Also strip spaced lowercase suffix if any survived
        n = SpacedLowerStateSuffixRegex().Replace(n, "").Trim();
        return n;
    }

    /// <summary>
    /// Returns true if the <paramref name="query"/> (search-normalized) is a
    /// substring of <paramref name="groupingKey"/> (full-normalized).
    /// </summary>
    public static bool Matches(string query, string groupingKey)
    {
        var q = NormalizeForSearch(query);
        // Strip state from groupingKey too before comparing
        var k = LowerStateSuffixRegex().Replace(groupingKey, "").Trim();
        return k == q || k.Contains(q, StringComparison.OrdinalIgnoreCase);
    }

    private static string RemoveDiacritics(string text)
    {
        var normalized = text.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(normalized.Length);
        foreach (var c in normalized)
        {
            var cat = CharUnicodeInfo.GetUnicodeCategory(c);
            if (cat != UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        }
        return sb.ToString().Normalize(NormalizationForm.FormC);
    }
}
