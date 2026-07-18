// ============================================================================
// BrazilianSoccerMcp - Data/TeamNameNormalizer.cs
//
// Context block:
//   Brazilian club names appear in wildly inconsistent forms across the six
//   datasets: "Palmeiras-SP", "Palmeiras", "São Paulo-SP", "São Caetano",
//   "Athletico Paranaense", "Arapongas Esporte Clube - PR",
//   "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", etc.
//
//   To answer cross-dataset questions ("all Palmeiras matches") every team
//   label is reduced to a canonical key via NormalizeTeam. The rule set,
//   in order:
//     1. Strip parentheticals "(...)"        — long obsolete-name annotations.
//     2. Strip a trailing state suffix:
//          "-XX", " - XX", "- XX", " XX"     where XX is a 2-3 letter state.
//     3. Lowercase + remove diacritics.
//     4. Strip common club-form tokens
//          ("futebol clube","sport club","esporte clube","ec","fc","sc",
//           "clube","sa","ac","athletic club","atletico club").
//     5. Collapse whitespace.
//
//   Matching is then canonical-key containment (TeamMatches): a query for
//   "palmeiras" matches "Palmeiras-SP" and "Palmeiras", and also the full
//   official "Sociedade Esportiva Palmeiras" because the canonical form of
//   the latter still contains "palmeiras". Known collisions (e.g. "Botafogo
//   SP" vs "Botafogo RJ" both -> "botafogo") are accepted for this demo and
//   documented in README; disambiguating them would need a curated alias map.
//
//   NormalizeText (no suffix stripping) is the diacritics/case helper reused
//   for player names, clubs and nationalities.
// ============================================================================

using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Data;

/// <summary>Reduces Brazilian team labels to a canonical comparable key.</summary>
public static partial class TeamNameNormalizer
{
    // Two-letter Brazilian state codes (UF) + a few extras seen in Libertadores.
    private static readonly HashSet<string> StateCodes = new(StringComparer.OrdinalIgnoreCase)
    {
        "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA",
        "PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO",
        // non-BR seen in Libertadores club labels (kept so suffix stripping is safe)
        "URU","EQU","ARG","CHI","COL","PAR","BOL","PER","VEN","MEX","ECU",
    };

    // Tokens removed from the canonical form after suffix/diacritics handling.
    // Longer phrases first so "esporte clube" is stripped before bare "clube".
    private static readonly string[] ClubFormTokens =
    {
        "futebol clube", "sport club", "athletic club", "atletico club",
        "clube de regatas", "grêmio de esportes", "esporte clube",
        "clube", "ec", "fc", "sc", "sa", "ac",
    };

    /// <summary>
    /// Canonical key for a team label: parentheticals dropped, trailing
    /// state suffix dropped, diacritics removed, lowercased, club-form tokens
    /// removed, whitespace collapsed.
    /// </summary>
    public static string NormalizeTeam(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        var s = raw.Trim();

        // 1. Drop parenthetical annotations e.g. "(antigo Esporte Clube Barreira)".
        s = ParenRegex().Replace(s, " ");

        // 2. Drop a trailing state suffix. Try "-XX" / " - XX" first (most common),
        //    then a bare trailing " XX" two-letter code.
        s = StateDashSuffixRegex().Replace(s, "");
        if (BareTrailingStateRegex().IsMatch(s))
            s = BareTrailingStateRegex().Replace(s, "");

        // 3. Lowercase + strip diacritics.
        s = NormalizeText(s);

        // 4. Drop club-form tokens (whole-word only).
        foreach (var token in ClubFormTokens)
            s = WordTokenRegex(token).Replace(s, " ");

        // 5. Collapse whitespace.
        s = WhitespaceRegex().Replace(s, " ").Trim();
        return s;
    }

    /// <summary>
    /// Lowercases and removes diacritics. Does NOT strip state suffixes or
    /// club tokens — used for player names, clubs, nationalities.
    /// </summary>
    public static string NormalizeText(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        var s = raw.Trim().ToLowerInvariant();
        var normalized = s.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(s.Length);
        foreach (var ch in normalized)
        {
            var cat = CharUnicodeInfo.GetUnicodeCategory(ch);
            if (cat != UnicodeCategory.NonSpacingMark)
                sb.Append(ch);
        }
        return sb.ToString().Normalize(NormalizationForm.FormC);
    }

    /// <summary>
    /// True if <paramref name="candidate"/> team label matches <paramref name="query"/>,
    /// using canonical-key containment either way (so either side can be the
    /// longer official name).
    /// </summary>
    public static bool TeamMatches(string? candidate, string? query)
    {
        var c = NormalizeTeam(candidate);
        var q = NormalizeTeam(query);
        if (q.Length == 0 || c.Length == 0)
            return false;
        return c.Contains(q, StringComparison.Ordinal) ||
               q.Contains(c, StringComparison.Ordinal) ||
               string.Equals(c, q, StringComparison.Ordinal);
    }

    // --- Compiled regexes (source-generated for net10) ---
    [GeneratedRegex(@"\(.*?\)")]
    private static partial Regex ParenRegex();

    [GeneratedRegex(@"\s*-\s*[A-Za-z]{2,3}\s*$")]
    private static partial Regex StateDashSuffixRegex();

    [GeneratedRegex(@"\s+[A-Za-z]{2}$")]
    private static partial Regex BareTrailingStateRegex();

    private static Regex WordTokenRegex(string token) =>
        new(@"\b" + Regex.Escape(token) + @"\b", RegexOptions.None, TimeSpan.FromSeconds(1));

    [GeneratedRegex(@"\s+")]
    private static partial Regex WhitespaceRegex();
}
