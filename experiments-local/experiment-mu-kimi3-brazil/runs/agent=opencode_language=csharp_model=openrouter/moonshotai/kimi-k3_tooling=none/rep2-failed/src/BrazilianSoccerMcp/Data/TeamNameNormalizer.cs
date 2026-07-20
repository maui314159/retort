// Context: Brazilian Soccer MCP Server.
// Team name normalization. The six datasets use different conventions:
//   "Palmeiras-SP", "América - MG", "Corinthians", "Vasco da Gama-RJ",
//   "Nacional (URU)", "Barcelona-EQU", "Boavista Sport Club (antigo ...) - RJ"
// Identity key = fold(baseName) + "|" + region where region is a Brazilian
// state code, a foreign country tag, or "" when unknown. Diacritics and case
// are folded so "America-MG" == "América-MG" == "América - MG".
// Different clubs sharing a base name stay distinct: "atletico|MG" (Atlético
// Mineiro) vs "atletico|GO" (Atlético Goianiense) vs "atletico|PR" (Athletico PR).
namespace BrazilianSoccerMcp.Data;

using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

public static partial class TeamNameNormalizer
{
    private static readonly HashSet<string> BrazilianStates =
    [
        "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
        "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"
    ];

    /// <summary>Well-known clubs that appear without a state suffix in some files.</summary>
    private static readonly Dictionary<string, string> StatelessDefaults = new()
    {
        ["vasco"] = "RJ", ["flamengo"] = "RJ", ["fluminense"] = "RJ", ["botafogo"] = "RJ",
        ["palmeiras"] = "SP", ["corinthians"] = "SP", ["sao paulo"] = "SP", ["santos"] = "SP",
        ["ponte preta"] = "SP", ["portuguesa"] = "SP", ["guarani"] = "SP",
        ["santo andre"] = "SP", ["sao caetano"] = "SP", ["barueri"] = "SP",
        ["gremio"] = "RS", ["gremio prudente"] = "SP", ["gremio barueri"] = "SP",
        ["internacional"] = "RS", ["juventude"] = "RS",
        ["cruzeiro"] = "MG", ["ipatinga"] = "MG",
        ["coritiba"] = "PR", ["parana"] = "PR",
        ["figueirense"] = "SC", ["avai"] = "SC", ["criciuma"] = "SC",
        ["joinville"] = "SC", ["chapecoense"] = "SC",
        ["bahia"] = "BA", ["vitoria"] = "BA",
        ["sport"] = "PE", ["santa cruz"] = "PE", ["nautico"] = "PE",
        ["ceara"] = "CE", ["fortaleza"] = "CE",
        ["goias"] = "GO", ["cuiaba"] = "MT", ["csa"] = "AL",
        ["paysandu"] = "PA", ["brasiliense"] = "DF",
        ["red bull bragantino"] = "SP", ["bragantino"] = "SP",
        ["atletico paranaense"] = "PR", ["athletico paranaense"] = "PR",
    };

    /// <summary>Base-name aliases folded before identity computation.</summary>
    private static readonly Dictionary<string, string> BaseAliases = new()
    {
        ["athletico"] = "atletico",        // Athletico-PR == Atletico-PR (same club, renamed 2018)
        ["vasco da gama"] = "vasco",
        ["bragantino"] = "red bull bragantino",
    };

    /// <summary>Official display names per identity key.</summary>
    private static readonly Dictionary<string, string> DisplayNames = new()
    {
        ["vasco|RJ"] = "Vasco da Gama",
        ["atletico|MG"] = "Atlético Mineiro",
        ["atletico|GO"] = "Atlético Goianiense",
        ["atletico|PR"] = "Athletico Paranaense",
        ["america|MG"] = "América Mineiro",
        ["america|RN"] = "América de Natal",
        ["america|RJ"] = "América-RJ",
        ["sport|PE"] = "Sport Recife",
        ["red bull bragantino|SP"] = "Red Bull Bragantino",
        ["gremio|RS"] = "Grêmio",
        ["botafogo|RJ"] = "Botafogo",
        ["ceara|CE"] = "Ceará",
        ["goias|GO"] = "Goiás",
        ["vitoria|BA"] = "Vitória",
        ["cuiaba|MT"] = "Cuiabá",
        ["nautico|PE"] = "Náutico",
        ["criciuma|SC"] = "Criciúma",
        ["avai|SC"] = "Avaí",
        ["parana|PR"] = "Paraná Clube",
    };

    /// <summary>Removes diacritics, lowercases, collapses whitespace.</summary>
    public static string Fold(string? text)
    {
        if (string.IsNullOrWhiteSpace(text)) return string.Empty;
        var normalized = text.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(normalized.Length);
        foreach (var c in normalized)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
                sb.Append(char.ToLowerInvariant(c));
        }
        return WhitespaceRegex().Replace(sb.ToString(), " ").Trim();
    }

    /// <summary>
    /// Splits a raw team name into (base, region) where region is a Brazilian state
    /// code, a foreign country tag (URU, EQU...), or null. Parenthetical annotations
    /// like "(antigo Esporte Clube Barreira)" are dropped; country tags are kept.
    /// </summary>
    public static (string Base, string? Region) Parse(string raw)
    {
        var name = raw.Trim();
        string? region = null;

        var paren = TrailingParenRegex().Match(name);
        if (paren.Success)
        {
            var content = paren.Groups[1].Value.Trim();
            if (content.StartsWith("antigo", StringComparison.OrdinalIgnoreCase))
                name = name[..paren.Index].Trim();                    // historical annotation: drop
            else if (CountryTagRegex().IsMatch(content))
            { region = content.ToUpperInvariant(); name = name[..paren.Index].Trim(); }
        }

        var dash = TrailingDashSuffixRegex().Match(name);
        if (dash.Success)
        {
            var suffix = dash.Groups[1].Value.ToUpperInvariant();
            if (suffix.Length == 2 && BrazilianStates.Contains(suffix))
            { region = suffix; name = name[..dash.Index].Trim(); }
            else if (suffix.Length == 3)
            { region ??= suffix; name = name[..dash.Index].Trim(); }
        }

        return (WhitespaceRegex().Replace(name, " ").Trim(), region);
    }

    /// <summary>Canonical identity key for a raw team name from any dataset.</summary>
    public static string IdentityKey(string raw)
    {
        var (baseName, region) = Parse(raw);
        var folded = Fold(baseName);
        if (BaseAliases.TryGetValue(folded, out var alias)) folded = alias;
        region ??= StatelessDefaults.GetValueOrDefault(folded);
        return string.IsNullOrEmpty(region) ? folded : $"{folded}|{region}";
    }

    /// <summary>Official display name for an identity key (falls back to the key's base part).</summary>
    public static string DisplayFor(string identityKey)
    {
        if (DisplayNames.TryGetValue(identityKey, out var display)) return display;
        var pipe = identityKey.IndexOf('|');
        var basePart = pipe < 0 ? identityKey : identityKey[..pipe];
        var region = pipe < 0 ? null : identityKey[(pipe + 1)..];
        var pretty = CultureInfo.InvariantCulture.TextInfo.ToTitleCase(basePart);
        return region is null ? pretty : $"{pretty}-{region}";
    }

    [GeneratedRegex(@"\s+")] private static partial Regex WhitespaceRegex();
    [GeneratedRegex(@"\(([^)]*)\)\s*$")] private static partial Regex TrailingParenRegex();
    [GeneratedRegex(@"^[A-Za-z]{2,3}$")] private static partial Regex CountryTagRegex();
    [GeneratedRegex(@"\s*-\s*([A-Za-z]{2,3})\s*$")] private static partial Regex TrailingDashSuffixRegex();
}
