using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Normalizes the many team-name spellings used across the five match files and the
/// FIFA player file into stable canonical keys. Handles state suffixes
/// ("Palmeiras-SP", "América - MG", "Audax SP"), accents ("Grêmio", "Avaí"),
/// parenthetical qualifiers, and well-known full-name aliases
/// ("Sport Club Corinthians Paulista" -> "corinthians").
/// </summary>
public static partial class TeamNameNormalizer
{
    private static readonly HashSet<string> BrazilianStates = new(StringComparer.Ordinal)
    {
        "ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms", "mt",
        "pa", "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc", "se", "sp", "to",
    };

    /// <summary>
    /// Base names shared by several distinct clubs — for these the state suffix is
    /// kept as part of the canonical key (e.g. "atletico mg" vs "atletico go").
    /// </summary>
    private static readonly HashSet<string> AmbiguousBases = new(StringComparer.Ordinal)
    {
        "atletico", "athletico", "america", "botafogo", "nacional",
    };

    /// <summary>Well-known cross-file aliases, keyed by normalized full name.</summary>
    private static readonly Dictionary<string, string> Aliases = new(StringComparer.Ordinal)
    {
        ["athletico paranaense"] = "athletico pr",
        ["atletico paranaense"] = "athletico pr",
        ["athletico"] = "athletico pr",
        ["atletico mineiro"] = "atletico mg",
        ["atletico goianiense"] = "atletico go",
        ["america fc"] = "america mg", // FIFA file: "América FC (Minas Gerais)"
        ["america mineiro"] = "america mg",
        ["america fc natal"] = "america rn",
        ["botafogo rj"] = "botafogo",
        ["botafogo de futebol e regatas"] = "botafogo",
        ["vasco"] = "vasco da gama",
        ["sport"] = "sport recife",
        ["sport club do recife"] = "sport recife",
        ["bragantino"] = "red bull bragantino",
        ["ceara sporting club"] = "ceara",
        ["fortaleza esporte clube"] = "fortaleza",
        ["sport club corinthians paulista"] = "corinthians",
        ["sao paulo fc"] = "sao paulo",
        ["parana clube"] = "parana",
        ["boa"] = "boa esporte",
    };

    /// <summary>
    /// Lower-cases, strips accents/diacritics, removes parenthetical segments and
    /// punctuation, and collapses whitespace. Does NOT resolve aliases or states.
    /// </summary>
    public static string Normalize(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        var s = raw.Trim().Trim('"');
        s = ParentheticalRegex().Replace(s, " ");
        s = s.Normalize(NormalizationForm.FormD);

        var sb = new StringBuilder(s.Length);
        foreach (var ch in s)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(ch) == UnicodeCategory.NonSpacingMark)
                continue; // strip diacritic marks (ã -> a, é -> e, ç -> c)
            sb.Append(char.IsLetterOrDigit(ch) ? char.ToLowerInvariant(ch) : ' ');
        }

        return WhitespaceRegex().Replace(sb.ToString(), " ").Trim();
    }

    /// <summary>
    /// The canonical identity key for a team: normalized name with state suffixes
    /// folded away for unambiguous clubs and curated aliases applied.
    /// </summary>
    public static string CanonKey(string? raw)
    {
        var n = Normalize(raw);
        if (n.Length == 0)
            return n;
        if (Aliases.TryGetValue(n, out var aliased))
            return aliased;

        var tokens = n.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        if (tokens.Length > 1 && BrazilianStates.Contains(tokens[^1]))
        {
            var baseName = string.Join(' ', tokens, 0, tokens.Length - 1);
            if (!AmbiguousBases.Contains(baseName))
            {
                n = baseName;
                if (Aliases.TryGetValue(n, out var aliasedBase))
                    return aliasedBase;
            }
        }

        return n;
    }

    [GeneratedRegex(@"\([^)]*\)")]
    private static partial Regex ParentheticalRegex();

    [GeneratedRegex(@"\s+")]
    private static partial Regex WhitespaceRegex();
}
