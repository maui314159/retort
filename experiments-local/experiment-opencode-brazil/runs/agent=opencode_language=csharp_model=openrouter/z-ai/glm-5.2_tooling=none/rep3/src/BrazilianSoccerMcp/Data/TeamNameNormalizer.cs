using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Helpers for normalizing Brazilian soccer team names.
/// Datasets use a mix of "Palmeiras-SP", "Palmeiras", "Sport Club Corinthians Paulista",
/// accented forms ("São Paulo") and parenthesised disambiguators
/// ("América - MG"). We strip state suffixes, punctuation and accents to
/// produce a stable key used for matching across files.
/// </summary>
public static partial class TeamNameNormalizer
{
    /// <summary>Known Brazilian state abbreviations used to strip suffixes.</summary>
    private static readonly HashSet<string> BrazilianStates = new(StringComparer.OrdinalIgnoreCase)
    {
        "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB",
        "PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO",
        // Foreign entries appearing in Libertadores data
        "URU","EQU","ARG","CHI","PAR","BOL","COL","PER","VEN","MEX","ECU"
    };

    /// <summary>
    /// Returns a normalized key suitable for cross-file equality comparison.
    /// Lowercase, ASCII-folded, no punctuation/spaces, no state suffix.
    /// </summary>
    public static string NormalizeKey(string name)
    {
        if (string.IsNullOrWhiteSpace(name)) return string.Empty;
        var stripped = StripStateSuffix(name.Trim());
        var folded = RemoveDiacritics(stripped);
        folded = StripParensRegex().Replace(folded, " ");
        folded = NonAlnumRegex().Replace(folded, "");
        return folded.ToLowerInvariant();
    }

    /// <summary>
    /// Returns a human-readable display name: trimmed, with one trailing
    /// state suffix preserved if the source included it, but otherwise free
    /// of parenthesised noise. This is what we surface to MCP callers.
    /// </summary>
    public static string DisplayName(string name)
    {
        if (string.IsNullOrWhiteSpace(name)) return string.Empty;
        var trimmed = name.Trim();
        // Strip parenthesised "(antigo ...)" style noise but keep the rest.
        trimmed = ParenContentRegex().Replace(trimmed, "");
        // Collapse repeated whitespace.
        trimmed = MultiSpaceRegex().Replace(trimmed, " ").Trim(' ', '-', '/');
        return trimmed;
    }

    private static string StripStateSuffix(string name)
    {
        // Splits on " - " or "-XX" at the end of the string.
        var match = TrailingSuffixRegex().Match(name);
        if (match.Success && BrazilianStates.Contains(match.Groups[1].Value))
        {
            return name.Substring(0, match.Index).Trim(' ', '-');
        }
        return name;
    }

    private static string RemoveDiacritics(string text)
    {
        var normalized = text.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(normalized.Length);
        foreach (var ch in normalized)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(ch) != UnicodeCategory.NonSpacingMark)
                sb.Append(ch);
        }
        return sb.ToString();
    }

    [GeneratedRegex(@"\s*[-–—]\s*([A-Za-z]{2,3})\s*$", RegexOptions.RightToLeft)]
    private static partial Regex TrailingSuffixRegex();

    [GeneratedRegex(@"\([^)]*\)")]
    private static partial Regex StripParensRegex();

    [GeneratedRegex(@"\([^)]*\)")]
    private static partial Regex ParenContentRegex();

    [GeneratedRegex(@"[^A-Za-z0-9]+")]
    private static partial Regex NonAlnumRegex();

    [GeneratedRegex(@"\s+")]
    private static partial Regex MultiSpaceRegex();
}
