// -----------------------------------------------------------------------------
// File: TeamName.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Team-name normalisation. The five match CSVs use three incompatible naming
//   conventions for the same club:
//     - state suffix, dash form:  "Palmeiras-SP", "Flamengo-RJ"
//     - state suffix, spaced form: "América - MG", "Bahia de Feira - BA"
//     - bare / full names:         "Flamengo", "Sport Club Corinthians Paulista"
//     - continental codes:         "Nacional (URU)", "Barcelona-EQU"
//   plus Portuguese accents ("São Paulo" vs "Sao Paulo", "Grêmio").
//
//   Two operations are exposed:
//     - Canonicalize: cleans a raw name for *display* while preserving the
//       state suffix (so "Atletico-MG" and "Atletico-PR" stay distinct) and the
//       original accents (UTF-8 requirement). Idempotent.
//     - MatchKey: an aggressive fold used for *searching and grouping*. It strips
//       accents, lowercases, removes the trailing state/country suffix and all
//       punctuation, and collapses whitespace. Matching is substring-based on the
//       key so "corinthians" finds "Sport Club Corinthians Paulista" and
//       "sao paulo" finds "São Paulo".
//
//   No allocations beyond the unavoidable string transforms; both methods are
//   pure and safe to call on the hot query path.
// -----------------------------------------------------------------------------

using System.Globalization;
using System.Text;

namespace BrazilianSoccer.Core;

/// <summary>Normalises club names across the differing source conventions.</summary>
public static class TeamName
{
    /// <summary>
    /// Produce a stable display name: trims, collapses internal whitespace, and
    /// rewrites a spaced state suffix ("América - MG") to the dash form
    /// ("América-MG"). Accents and the state suffix are preserved so that
    /// distinct clubs remain distinguishable.
    /// </summary>
    public static string Canonicalize(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        var s = CollapseWhitespace(raw.Trim());

        // " - MG" / " - BA" spaced suffix -> "-MG". Only when the tail is a short
        // all-letter token (state abbreviation or country code), never a real word.
        int dash = s.LastIndexOf(" - ", StringComparison.Ordinal);
        if (dash > 0)
        {
            var tail = s[(dash + 3)..];
            if (IsSuffixToken(tail))
                s = string.Concat(s.AsSpan(0, dash), "-", tail);
        }

        return s;
    }

    /// <summary>
    /// Produce the case- and accent-insensitive matching key: lowercase ASCII,
    /// state/country suffix removed, punctuation stripped, whitespace collapsed.
    /// Returns empty for blank input.
    /// </summary>
    public static string MatchKey(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        var s = StripAccents(raw.Trim().ToLowerInvariant());

        // Drop a trailing continental code in parentheses: "nacional (uru)".
        int paren = s.LastIndexOf('(');
        if (paren > 0)
            s = s[..paren].TrimEnd();

        // Drop a trailing state/country suffix in either "name - mg" or "name-mg" form.
        int spaced = s.LastIndexOf(" - ", StringComparison.Ordinal);
        if (spaced > 0 && IsSuffixToken(s[(spaced + 3)..]))
        {
            s = s[..spaced];
        }
        else
        {
            int hyphen = s.LastIndexOf('-');
            if (hyphen > 0 && IsSuffixToken(s[(hyphen + 1)..]))
                s = s[..hyphen];
        }

        // Replace any remaining punctuation with spaces, then collapse.
        var sb = new StringBuilder(s.Length);
        foreach (var c in s)
            sb.Append(char.IsLetterOrDigit(c) ? c : ' ');

        return CollapseWhitespace(sb.ToString()).Trim();
    }

    /// <summary>
    /// True when <paramref name="query"/> matches <paramref name="teamRaw"/> by
    /// substring on their match keys (case/accent/suffix insensitive). An empty
    /// query never matches.
    /// </summary>
    public static bool Matches(string teamRaw, string query)
    {
        var key = MatchKey(query);
        if (key.Length == 0)
            return false;
        return MatchKey(teamRaw).Contains(key, StringComparison.Ordinal);
    }

    // A short (2-3 char) all-letter token is treated as a state/country suffix.
    private static bool IsSuffixToken(string tail)
    {
        if (tail.Length is < 2 or > 3)
            return false;
        foreach (var c in tail)
            if (!char.IsLetter(c))
                return false;
        return true;
    }

    private static string StripAccents(string s)
    {
        var decomposed = s.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(decomposed.Length);
        foreach (var c in decomposed)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        }
        return sb.ToString().Normalize(NormalizationForm.FormC);
    }

    private static string CollapseWhitespace(string s)
    {
        if (!ContainsRun(s))
            return s;

        var sb = new StringBuilder(s.Length);
        bool prevSpace = false;
        foreach (var c in s)
        {
            bool isSpace = char.IsWhiteSpace(c);
            if (isSpace)
            {
                if (!prevSpace)
                    sb.Append(' ');
            }
            else
            {
                sb.Append(c);
            }
            prevSpace = isSpace;
        }
        return sb.ToString();

        static bool ContainsRun(string text)
        {
            bool prev = false;
            foreach (var c in text)
            {
                bool sp = char.IsWhiteSpace(c);
                if ((sp && prev) || (sp && c != ' '))
                    return true;
                prev = sp;
            }
            return false;
        }
    }
}
