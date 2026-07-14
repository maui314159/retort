// =============================================================================
// Context: Brazilian Soccer MCP Server — team-name normalization.
//
// The datasets use inconsistent team naming: state suffixes ("Palmeiras-SP",
// "Flamengo - RJ"), country suffixes ("Nacional (URU)"), accents ("São Paulo",
// "Grêmio"), and varying case. To match a user's query term ("flamengo") against
// any of these, every name is reduced to a canonical key: accents folded to
// ASCII, trailing " - XX" / "-XX" state and "(XXX)" country suffixes removed,
// punctuation collapsed to single spaces, lower-cased and trimmed.
//
// Matching is substring-based on the key so "sao paulo" matches
// "Sao Paulo" and "São Paulo-SP" alike.
// =============================================================================
using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccer.Core;

public static partial class TeamName
{
    // Trailing state suffix: " - SP", "-SP", " SP" at end (2 upper letters).
    [GeneratedRegex(@"\s*[-–]\s*[A-Z]{2}\s*$")]
    private static partial Regex StateSuffix();

    // Trailing country code in parentheses: "(URU)", "(EQU)".
    [GeneratedRegex(@"\s*\([A-Z]{2,4}\)\s*$")]
    private static partial Regex CountrySuffix();

    [GeneratedRegex(@"\s+")]
    private static partial Regex Whitespace();

    /// <summary>
    /// Produce a canonical lookup key for a team name. Idempotent and culture-invariant.
    /// </summary>
    public static string Key(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        var s = raw.Trim();
        s = CountrySuffix().Replace(s, string.Empty);
        s = StateSuffix().Replace(s, string.Empty);
        s = FoldAccents(s);

        // Drop punctuation that is not part of a word, keep alphanumerics and spaces.
        var sb = new StringBuilder(s.Length);
        foreach (var ch in s)
        {
            if (char.IsLetterOrDigit(ch))
                sb.Append(char.ToLowerInvariant(ch));
            else
                sb.Append(' ');
        }

        var collapsed = Whitespace().Replace(sb.ToString(), " ").Trim();
        return collapsed;
    }

    /// <summary>
    /// Stronger key for *grouping distinct clubs* (standings, per-team aggregation).
    /// Unlike <see cref="Key"/> it keeps the state/country suffix, so "Atletico-MG"
    /// and "Atletico-PR" stay separate. Accents are folded and case normalized.
    /// Safe to group within a single source, where naming is internally consistent.
    /// </summary>
    public static string IdentityKey(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        var s = FoldAccents(raw.Trim());
        var sb = new StringBuilder(s.Length);
        foreach (var ch in s)
        {
            if (char.IsLetterOrDigit(ch))
                sb.Append(char.ToLowerInvariant(ch));
            else
                sb.Append(' ');
        }
        return Whitespace().Replace(sb.ToString(), " ").Trim();
    }

    /// <summary>Strip diacritics, mapping accented Latin characters to ASCII.</summary>
    public static string FoldAccents(string input)
    {
        var normalized = input.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(normalized.Length);
        foreach (var ch in normalized)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(ch) != UnicodeCategory.NonSpacingMark)
                sb.Append(ch);
        }
        return sb.ToString().Normalize(NormalizationForm.FormC);
    }

    /// <summary>True when <paramref name="query"/> matches <paramref name="teamKey"/> as a whole-word-ish substring.</summary>
    public static bool Matches(string teamKey, string queryKey)
    {
        if (queryKey.Length == 0)
            return false;
        if (teamKey == queryKey)
            return true;
        // Substring with word boundaries to avoid "santo" matching "santos" spuriously
        // while still allowing "sao paulo" inside "sao paulo fc".
        return ContainsWord(teamKey, queryKey);
    }

    private static bool ContainsWord(string haystack, string needle)
    {
        int idx = 0;
        while ((idx = haystack.IndexOf(needle, idx, StringComparison.Ordinal)) >= 0)
        {
            bool leftOk = idx == 0 || haystack[idx - 1] == ' ';
            int end = idx + needle.Length;
            bool rightOk = end == haystack.Length || haystack[end] == ' ';
            if (leftOk && rightOk)
                return true;
            idx += 1;
        }
        return false;
    }
}
