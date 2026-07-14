// ============================================================================
// File: Data/TeamNameNormalizer.cs
// ----------------------------------------------------------------------------
// Context: The six source datasets use wildly inconsistent team naming:
//   - "Palmeiras-SP" / "Flamengo-RJ"        (state suffix with hyphen)
//   - "América - MG" / "Bahia de Feira - BA" (state suffix with " - ")
//   - "Nacional (URU)" / "Barcelona-EQU"     (country code, paren or hyphen)
//   - "Sao Paulo" / "Gremio" / "Corinthians" (ASCII, no accents, no suffix)
//   - "São Paulo" / "Grêmio"                 (full Portuguese accents)
//
// To answer cross-file queries ("all Palmeiras matches") we parse each name
// into a TeamKey(Bare, Suffix):
//   1. Drop parenthetical notes   "(antigo Esporte Clube Barreira)"
//   2. Split on " - " and keep the left half (handles "América - MG")
//   3. Fold accents (FormD, strip non-spacing marks) -> ASCII
//   4. Strip a trailing 2-3 letter state/country code preceded by space/hyphen
//   5. Lowercase, replace spaces with hyphens, collapse repeats
//
// Two teams match when their Bare keys are equal AND, when both carry a
// suffix, the suffixes agree (so "América-MG" does NOT match "América-RN",
// but a bare query "Flamengo" DOES match "Flamengo-RJ").
//
// A curated canonical display map gives human-friendly names for the common
// Brazilian clubs; unknown teams fall back to the first raw spelling seen.
// ============================================================================

using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Data;

public static class TeamNameNormalizer
{
    private static readonly Regex ParenRegex = new(@"\([^)]*\)", RegexOptions.Compiled);
    private static readonly Regex DashSplitRegex = new(@"\s+-\s+", RegexOptions.Compiled);
    // Trailing 2-3 letter code, separated by a hyphen or space: "-SP", " MG", "-EQU".
    private static readonly Regex SuffixRegex = new(@"[\s\-]([A-Za-z]{2,3})$", RegexOptions.Compiled);
    private static readonly Regex CollapseRegex = new(@"[-\s]+", RegexOptions.Compiled);

    /// <summary>Curated canonical display names keyed by the Bare key.</summary>
    private static readonly Dictionary<string, string> CanonicalDisplay = new(StringComparer.Ordinal)
    {
        ["flamengo"] = "Flamengo",
        ["fluminense"] = "Fluminense",
        ["palmeiras"] = "Palmeiras",
        ["santos"] = "Santos",
        ["corinthians"] = "Corinthians",
        ["sao-paulo"] = "São Paulo",
        ["gremio"] = "Grêmio",
        ["internacional"] = "Internacional",
        ["botafogo"] = "Botafogo",
        ["vasco"] = "Vasco",
        ["cruzeiro"] = "Cruzeiro",
        ["atletico"] = "Atlético",     // suffix disambiguates -MG / -GO
        ["athletico"] = "Athletico",   // -PR
        ["bahia"] = "Bahia",
        ["bahia-de-feira"] = "Bahia de Feira",
        ["fortaleza"] = "Fortaleza",
        ["ceara"] = "Ceará",
        ["sport"] = "Sport",
        ["coritiba"] = "Coritiba",
        ["nautico"] = "Náutico",
        ["ponte-preta"] = "Ponte Preta",
        ["figueirense"] = "Figueirense",
        ["goias"] = "Goiás",
        ["paysandu"] = "Paysandu",
        ["criciuma"] = "Criciúma",
        ["juventude"] = "Juventude",
        ["america"] = "América",       // suffix disambiguates -MG / -RN
        ["vitoria"] = "Vitória",
        ["avai"] = "Avaí",
        ["chapecoense"] = "Chapecoense",
        ["cuiaba"] = "Cuiabá",
        ["atletico-goianiense"] = "Atlético Goianiense",
        ["bragantino"] = "Bragantino",
        ["red-bull-bragantino"] = "Red Bull Bragantino",
        ["gama"] = "Gama",
        ["vila-nova"] = "Vila Nova",
        ["operario"] = "Operário",
        ["sao-jose"] = "São José",
        ["nova-iguacu"] = "Nova Iguaçu",
        ["boa"] = "Boa",
        ["londrina"] = "Londrina",
        ["parana"] = "Paraná",
        ["joinville"] = "Joinville",
        ["santa-cruz"] = "Santa Cruz",
        ["novo-hamburgo"] = "Novo Hamburgo",
        ["ypiranga"] = "Ypiranga",
        ["juazeirense"] = "Juazeirense",
        ["confianca"] = "Confiança",
        ["crb"] = "CRB",
        ["csa"] = "CSA",
        ["abc"] = "ABC",
        ["remo"] = "Remo",
        ["tombense"] = "Tombense",
        ["barueri"] = "Barueri",
        ["oueste"] = "Oeste",
        ["portuguesa"] = "Portuguesa",
    };

    /// <summary>Parse a raw team name into a normalized key.</summary>
    public static TeamKey Parse(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return new TeamKey(string.Empty, null);

        var name = raw.Trim();

        // 1. Drop parenthetical notes (e.g. "(antigo Esporte Clube Barreira)", "(URU)").
        name = ParenRegex.Replace(name, " ");

        // 2. "América - MG" -> keep left half "América".
        var dashSplit = DashSplitRegex.Split(name);
        name = dashSplit[0].Trim();

        // 3. Fold accents to ASCII.
        name = FoldAccents(name);

        // 4. Strip trailing 2-3 letter state/country code.
        string? suffix = null;
        var suffixMatch = SuffixRegex.Match(name);
        if (suffixMatch.Success)
        {
            suffix = suffixMatch.Groups[1].Value.ToUpperInvariant();
            name = name[..suffixMatch.Index].Trim();
        }

        // 5. Lowercase, spaces -> hyphens, collapse repeats.
        name = CollapseRegex.Replace(name.ToLowerInvariant(), "-").Trim('-');

        return new TeamKey(name, string.IsNullOrEmpty(name) ? null : suffix);
    }

    /// <summary>Bare key only (convenience for queries that ignore suffix).</summary>
    public static string BareKey(string? raw) => Parse(raw).Bare;

    /// <summary>
    /// True when a query team <paramref name="query"/> matches a stored team
    /// <paramref name="stored"/>. Bare keys must be equal; if both carry a
    /// suffix the suffixes must also agree (disambiguates América-MG vs -RN).
    /// </summary>
    public static bool Matches(TeamKey query, TeamKey stored)
    {
        if (!string.Equals(query.Bare, stored.Bare, StringComparison.Ordinal))
            return false;
        if (query.HasSuffix && stored.HasSuffix &&
            !string.Equals(query.Suffix, stored.Suffix, StringComparison.Ordinal))
            return false;
        return true;
    }

    /// <summary>
    /// Resolve a human-friendly display name. Prefers the curated map; otherwise
    /// uses <paramref name="fallbackRaw"/> (the raw spelling from the dataset).
    /// </summary>
    public static string DisplayName(TeamKey key, string fallbackRaw)
    {
        if (CanonicalDisplay.TryGetValue(key.Bare, out var canonical))
        {
            return key.HasSuffix ? $"{canonical}-{key.Suffix}" : canonical;
        }
        return fallbackRaw;
    }

    private static string FoldAccents(string s)
    {
        var normalized = s.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(s.Length);
        foreach (var ch in normalized)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(ch) != UnicodeCategory.NonSpacingMark)
                sb.Append(ch);
        }
        return sb.ToString();
    }
}
