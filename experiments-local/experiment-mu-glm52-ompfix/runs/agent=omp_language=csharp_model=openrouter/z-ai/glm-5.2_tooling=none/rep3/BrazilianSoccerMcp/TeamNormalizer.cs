// =============================================================================
// BrazilianSoccerMcp - Team Name Normalization
// -----------------------------------------------------------------------------
// Context: The six source files use wildly different team-name conventions:
//   * state suffix, hyphenated:  "Palmeiras-SP", "Athletico-PR"
//   * state suffix, spaced:      "Botafogo RJ", "EC Internacional SC"
//   * parenthetical country:     "Nacional (URU)", "Guarani (PAR)"
//   * full formal names:         "Atletico Mineiro", "Athletico Paranaense"
//   * with/without accents:      "São Paulo" vs "Sao Paulo", "Grêmio" vs "Gremio"
//   * short vs long:             "Vasco" vs "Vasco da Gama-RJ"
// To answer cross-file questions ("all Palmeiras matches across every file") we
// reduce every raw name to one canonical KEY used for equality, while keeping a
// nicely accented DISPLAY name for human-readable output.
//
// Strategy:
//   1. Strip parenthetical annotations ((URU), (PAR), (antigo ...)).
//   2. Strip a trailing 2-letter state code, hyphenated OR spaced, validated
//      against the 27 official Brazilian UF codes (avoids stripping real words).
//   3. Strip diacritics + lowercase + collapse whitespace => base key.
//   4. Apply explicit overrides:
//        - The "Atlético" cluster is genuinely ambiguous (MG/PR/GO/... are
//          distinct famous clubs), so it keeps the state in the key. The two
//          historic spellings (Atletico-PR / Athletico-PR) and the full names
//          (Atletico Mineiro, Athletico Paranaense, ...) all collapse to the
//          state-bearing canonical key.
//        - A few short/prefixed forms (vasco, ec bahia, sport recife, ...) map
//          to their well-known canonical base.
//   5. Everything else uses the plain base key (state-independent) so the same
//          club is matched across files even when one file omits the state.
//
// Display names are chosen at load time, preferring the variant carrying the
// most accented characters (so "São Paulo" wins over "Sao Paulo"), with an
// explicit override table for the Atlético cluster.
// =============================================================================

using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Data;

public static partial class TeamNormalizer
{
    /// <summary>The 27 official Brazilian state (UF) abbreviations.</summary>
    public static readonly HashSet<string> UfCodes = new(StringComparer.Ordinal)
    {
        "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
        "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"
    };

    private static readonly Regex ParenRe = CreateParenRegex();
    private static readonly Regex StateSuffixRe = CreateStateSuffixRegex();
    private static readonly Regex SpaceCollapseRe = CreateSpaceCollapseRegex();

    /// <summary>
    /// Canonical display overrides for the Atlético cluster (the only clubs that
    /// keep their state in the key). Keys here are the canonical match keys.
    /// </summary>
    public static readonly Dictionary<string, string> DisplayOverride = new(StringComparer.Ordinal)
    {
        ["atletico mg"] = "Atlético-MG",
        ["atletico pr"] = "Athletico-PR",
        ["atletico go"] = "Atlético-GO",
        ["atletico ac"] = "Atlético-AC",
        ["atletico ba"] = "Atlético-BA",
        ["atletico ce"] = "Atlético-CE",
    };

    /// <summary>Full-name / prefixed forms that collapse to a canonical base key.</summary>
    private static readonly Dictionary<string, string> BaseOverride = new(StringComparer.Ordinal)
    {
        // Atlético cluster full names -> state-bearing canonical key
        ["atletico mineiro"]      = "atletico mg",
        ["atletico goianiense"]   = "atletico go",
        ["atletico paranaense"]   = "atletico pr",
        ["athletico paranaense"]  = "atletico pr",
        ["atletico acreano"]      = "atletico ac",
        ["atletico alagoinhas"]   = "atletico ba",
        ["fc atletico cearense"]  = "atletico ce",
        // short / prefixed forms of well-known clubs
        ["vasco"]                 = "vasco da gama",
        ["ec internacional"]      = "internacional",
        ["ec bahia"]              = "bahia",
        ["fortaleza ec"]          = "fortaleza",
        ["fortaleza fc"]          = "fortaleza",
        ["sport recife"]          = "sport",
    };

    /// <summary>Compute the canonical match key for a raw team name.</summary>
    public static string NormalizeKey(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return "";
        var name = ParenRe.Replace(raw, " ").Trim();

        // Strip a trailing 2-letter state code, hyphenated ("Palmeiras-SP") or
        // spaced ("Botafogo RJ"), but only if it is a real Brazilian UF.
        var state = "";
        var m = StateSuffixRe.Match(name);
        if (m.Success && UfCodes.Contains(m.Groups[1].Value.ToUpperInvariant()))
        {
            state = m.Groups[1].Value.ToUpperInvariant();
            name = name[..m.Index].Trim();
        }

        var key = StripDiacritics(name).ToLowerInvariant();
        key = SpaceCollapseRe.Replace(key, " ").Trim();

        if (BaseOverride.TryGetValue(key, out var overridden))
            return overridden;

        // The bare "atlético/athletico" + state => keep state to disambiguate.
        if (key == "atletico" || key == "athletico")
        {
            // "Athletico" only ever refers to the Paraná club.
            if (key == "athletico" && state.Length == 0) state = "PR";
            return state.Length == 2 ? $"atletico {state.ToLowerInvariant()}" : "atletico";
        }

        return key;
    }

    /// <summary>
    /// Clean a raw name into a display candidate: drop parentheticals and the
    /// state suffix but keep accents. The repository picks the best candidate
    /// per canonical key.
    /// </summary>
    public static string CleanDisplay(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return "";
        var name = ParenRe.Replace(raw, " ").Trim();
        var m = StateSuffixRe.Match(name);
        if (m.Success && UfCodes.Contains(m.Groups[1].Value.ToUpperInvariant()))
            name = name[..m.Index].Trim();
        return SpaceCollapseRe.Replace(name, " ").Trim();
    }

    /// <summary>Count accented (non-ASCII) characters, used to pick display names.</summary>
    public static int AccentCount(string s)
    {
        var acc = 0;
        foreach (var c in s)
            if (c > 127) acc++;
        return acc;
    }

    /// <summary>Remove combining diacritical marks (é -> e, ã -> a, ç -> c).</summary>
    public static string StripDiacritics(string s)
    {
        var normalized = s.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(s.Length);
        foreach (var c in normalized)
            if (CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        return sb.ToString();
    }

    [GeneratedRegex(@"\s*\([^)]*\)\s*", RegexOptions.Compiled)]
    private static partial Regex CreateParenRegex();

    // Matches a trailing 2-letter code preceded by hyphen and/or whitespace.
    [GeneratedRegex(@"[\s\-]+([A-Za-z]{2})\s*$", RegexOptions.Compiled)]
    private static partial Regex CreateStateSuffixRegex();

    [GeneratedRegex(@"\s+", RegexOptions.Compiled)]
    private static partial Regex CreateSpaceCollapseRegex();
}
