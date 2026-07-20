using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Normalizes Brazilian soccer team names across the datasets:
/// "Palmeiras-SP", "Palmeiras", "São Paulo", "sao paulo fc" should all match.
/// </summary>
public static partial class TeamNameNormalizer
{
    // "-SP", "-RJ", " - MG", "(SP)" style suffixes
    [GeneratedRegex(@"\s*[-–(]\s*[A-Z]{2,3}\s*\)?\s*$", RegexOptions.Compiled)]
    private static partial Regex StateSuffixRegex();

    // Long-form suffixes like "Sport Club", "Esporte Clube", "Futebol Clube" — stripped for matching.
    // NOTE: deliberately excludes single tokens like "club" or "atletico" — stripping those
    // would destroy identity ("Moto Club" -> "moto", "Atletico Mineiro" -> "mineiro").
    [GeneratedRegex(@"\b(sport club|esporte clube|futebol clube|football club|clube de regatas|sociedade esportiva|grêmio foot[ -]ball|atletico clube|esporte clube|futebol clube)\b", RegexOptions.Compiled)]
    private static partial Regex LegalFormRegex();

    [GeneratedRegex(@"\s+", RegexOptions.Compiled)]
    private static partial Regex WhitespaceRegex();

    /// <summary>
    /// Normalizes a name but KEEPS any trailing state token: lowercase,
    /// diacritics removed, punctuation collapsed to spaces.
    /// Used by <see cref="TeamCanon"/> so aliases can see "botafogo pb"
    /// before the state is stripped.
    /// </summary>
    public static string NormalizeKeepState(string? name)
    {
        if (string.IsNullOrWhiteSpace(name)) return string.Empty;
        var s = RemoveDiacritics(name.Trim()).ToLowerInvariant();
        s = s.Replace(".", " ").Replace("-", " ").Replace("/", " ")
             .Replace("(", " ").Replace(")", " ");
        s = WhitespaceRegex().Replace(s, " ").Trim();
        return s;
    }

    /// <summary>
    /// Returns a canonical matching key: lowercase, diacritics removed,
    /// state suffix removed, punctuation collapsed.
    /// </summary>
    public static string NormalizeKey(string? name)
    {
        if (string.IsNullOrWhiteSpace(name)) return string.Empty;

        var s = name.Trim();
        s = StateSuffixRegex().Replace(s, "");
        s = RemoveDiacritics(s);
        s = s.ToLowerInvariant();
        // drop punctuation commonly found in long names
        s = s.Replace(".", " ").Replace("-", " ").Replace("/", " ");
        s = WhitespaceRegex().Replace(s, " ").Trim();
        return s;
    }

    /// <summary>
    /// Aggressive key that also removes legal-form words ("sport club", "esporte clube", ...)
    /// so "Sport Club Corinthians Paulista" ≈ "corinthians paulista".
    /// Built on the state-preserving normalization.
    /// </summary>
    public static string LooseKey(string? name)
    {
        var key = NormalizeKeepState(name);
        if (key.Length == 0) return key;
        key = LegalFormRegex().Replace(key, " ");
        key = WhitespaceRegex().Replace(key, " ").Trim();
        return key;
    }

    /// <summary>
    /// True when the two names plausibly refer to the same team.
    /// Exact normalized match, loose match, or one name containing the other
    /// (handles "São Paulo FC" vs "São Paulo").
    /// </summary>
    public static bool IsSameTeam(string? a, string? b)
    {
        var ka = NormalizeKey(a);
        var kb = NormalizeKey(b);
        if (ka.Length == 0 || kb.Length == 0) return false;
        if (ka == kb) return true;

        var la = LooseKey(a);
        var lb = LooseKey(b);
        if (la.Length > 0 && la == lb) return true;

        // Containment both ways on the strict key (e.g. "sao paulo" vs "sao paulo fc")
        if (ka.Length >= 4 && kb.Contains(ka, StringComparison.Ordinal)) return true;
        if (kb.Length >= 4 && ka.Contains(kb, StringComparison.Ordinal)) return true;

        return false;
    }

    public static string RemoveDiacritics(string text)
    {
        var normalized = text.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(normalized.Length);
        foreach (var c in normalized)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        }
        return sb.ToString().Normalize(NormalizationForm.FormC);
    }
}
