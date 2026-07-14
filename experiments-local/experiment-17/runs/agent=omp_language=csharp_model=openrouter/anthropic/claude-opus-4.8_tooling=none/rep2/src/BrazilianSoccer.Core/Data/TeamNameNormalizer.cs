// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    TeamNameNormalizer.cs
// Project: BrazilianSoccer.Core
// Purpose: Normalise the many spellings of Brazilian club names across the
//          datasets so the same club matches regardless of source file.
// Why:     The datasets use inconsistent conventions:
//            - State suffixes: "Palmeiras-SP", "Flamengo-RJ", "América - MG"
//            - Country suffixes: "Nacional (URU)", "Barcelona-EQU"
//            - Full legal names: "Sport Club Corinthians Paulista"
//            - Accents/cedilla: "São Paulo", "Grêmio", "Avaí", "Atlético-MG"
//          Matching must be accent-insensitive and suffix-insensitive while
//          still letting a user type "flamengo", "Flamengo-RJ" or "FLAMENGO".
// Strategy:
//            1. Strip trailing "-XX" / " - XX" state codes and "(XXX)" country
//               codes.
//            2. Fold accents to ASCII, lower-case, collapse whitespace.
//            3. Apply a small alias table for well-known full/legal names.
// =============================================================================

using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccer.Core.Data;

/// <summary>
/// Produces a canonical key for a team name and a clean display name, so the
/// same club matches consistently across datasets.
/// </summary>
public static partial class TeamNameNormalizer
{
    // Trailing " - SP", "-SP", "(URU)" style location suffixes.
    [GeneratedRegex(@"\s*[-–]\s*[A-Za-z]{2,3}\s*$", RegexOptions.CultureInvariant)]
    private static partial Regex StateSuffix();

    [GeneratedRegex(@"\s*\([A-Za-z]{2,4}\)\s*$", RegexOptions.CultureInvariant)]
    private static partial Regex CountrySuffix();

    [GeneratedRegex(@"\s+", RegexOptions.CultureInvariant)]
    private static partial Regex Whitespace();

    // Canonical-key -> canonical-key aliases for full/legal names.
    private static readonly Dictionary<string, string> Aliases = new(StringComparer.Ordinal)
    {
        ["sport club corinthians paulista"] = "corinthians",
        ["sociedade esportiva palmeiras"] = "palmeiras",
        ["clube de regatas do flamengo"] = "flamengo",
        ["fluminense football club"] = "fluminense",
        ["sao paulo futebol clube"] = "sao paulo",
        ["santos futebol clube"] = "santos",
        ["gremio foot-ball porto alegrense"] = "gremio",
        ["fortaleza esporte clube"] = "fortaleza",
        ["botafogo de futebol e regatas"] = "botafogo",
        ["cruzeiro esporte clube"] = "cruzeiro",
        ["clube atletico mineiro"] = "atletico mineiro",
        ["atletico-mg"] = "atletico mineiro",
        ["atletico mg"] = "atletico mineiro",
        ["athletico-pr"] = "athletico paranaense",
        ["atletico-pr"] = "athletico paranaense",
        ["atletico paranaense"] = "athletico paranaense",
    };

    /// <summary>
    /// Returns a canonical, accent- and suffix-insensitive key for matching.
    /// </summary>
    public static string Canonical(string? name)
    {
        if (string.IsNullOrWhiteSpace(name))
            return string.Empty;

        // Fold accents/case first so suffix-bearing aliases (e.g. "atletico-mg"
        // vs "atletico-pr", which both strip to "atletico") can be resolved
        // BEFORE the generic suffix stripper would collapse them together.
        var folded = FoldAccents(name.Trim()).ToLowerInvariant();
        folded = Whitespace().Replace(folded, " ").Trim();
        if (Aliases.TryGetValue(folded, out var direct))
            return direct;

        var stripped = CountrySuffix().Replace(folded, string.Empty);
        stripped = StateSuffix().Replace(stripped, string.Empty);
        stripped = Whitespace().Replace(stripped, " ").Trim();

        return Aliases.TryGetValue(stripped, out var canonical) ? canonical : stripped;
    }

    /// <summary>
    /// Returns a clean display name: original text with location suffixes
    /// stripped but accents preserved.
    /// </summary>
    public static string Display(string? name)
    {
        if (string.IsNullOrWhiteSpace(name))
            return string.Empty;

        var trimmed = name.Trim();
        trimmed = CountrySuffix().Replace(trimmed, string.Empty);
        trimmed = StateSuffix().Replace(trimmed, string.Empty);
        return Whitespace().Replace(trimmed, " ").Trim();
    }

    /// <summary>
    /// True when two raw team names refer to the same club.
    /// </summary>
    public static bool Matches(string? a, string? b)
        => Canonical(a) == Canonical(b) && Canonical(a).Length > 0;

    /// <summary>
    /// True when <paramref name="candidate"/>'s canonical form contains the
    /// canonical query as a token-aware substring (for partial searches).
    /// </summary>
    public static bool Contains(string? candidate, string? query)
    {
        var c = Canonical(candidate);
        var q = Canonical(query);
        if (q.Length == 0)
            return false;
        return c == q || c.Contains(q, StringComparison.Ordinal);
    }

    private static string FoldAccents(string text)
    {
        var normalized = text.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(normalized.Length);
        foreach (var ch in normalized)
        {
            var category = CharUnicodeInfo.GetUnicodeCategory(ch);
            if (category != UnicodeCategory.NonSpacingMark)
                sb.Append(ch);
        }
        return sb.ToString().Normalize(NormalizationForm.FormC);
    }
}
