using System.Globalization;
using System.Text.RegularExpressions;
using System.Text;

namespace BrazilianSoccerMCP.Services;

/// <summary>
/// Normalizes team names from different data sources for consistent matching.
/// Handles state suffixes, special characters, and common variations.
/// </summary>
public static partial class TeamNameNormalizer
{
    // Known mappings from full/official names to short names
    private static readonly Dictionary<string, string> KnownMappings = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Sport Club Corinthians Paulista"] = "Corinthians",
        ["Sao Paulo"] = "São Paulo",
        ["America MG"] = "América-MG",
        ["America RN"] = "América-RN",
        ["Atletico MG"] = "Atlético-MG",
        ["Atletico GO"] = "Atlético-GO",
        ["Atletico PR"] = "Athletico-PR",
        ["Athletico PR"] = "Athletico-PR",
        ["Avai"] = "Avaí",
        ["Botafogo RJ"] = "Botafogo",
        ["Chapecoense SC"] = "Chapecoense",
        ["Cruzeiro MG"] = "Cruzeiro",
        ["Cuiaba"] = "Cuiabá",
        ["Ceara"] = "Ceará",
        ["Fortaleza EC"] = "Fortaleza",
        ["Goias"] = "Goiás",
        ["Gremio"] = "Grêmio",
        ["Guarani"] = "Guarani",
        ["Internacional RS"] = "Internacional",
        ["Londrina"] = "Londrina",
        ["Nautico"] = "Náutico",
        ["Parana"] = "Paraná",
        ["Ponte Preta SP"] = "Ponte Preta",
        ["Portuguesa SP"] = "Portuguesa",
        ["Santa Cruz PE"] = "Santa Cruz",
        ["Santos SP"] = "Santos",
        ["Sport PE"] = "Sport",
        ["Vasco da Gama"] = "Vasco",
        ["Vitoria"] = "Vitória",
        ["Bahia BA"] = "Bahia",
        ["Figueirense SC"] = "Figueirense",
        ["Coritiba PR"] = "Coritiba",
        ["Juventude RS"] = "Juventude",
        ["Criciuma"] = "Criciúma",
        ["Criciúma SC"] = "Criciúma",
        ["Bragantino SP"] = "Bragantino",
        ["Red Bull Bragantino"] = "Bragantino",
        ["RB Bragantino"] = "Bragantino",
    };

    // Brazilian state suffixes to strip
    [GeneratedRegex(@"\s*-\s*(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)$")]
    private static partial Regex StateSuffixRegex();

    // Strip parenthetical or bracketed content like "(URU)" or "(antigo ...)"
    [GeneratedRegex(@"\s*[\(\[].*?[\)\]]")]
    private static partial Regex ParentheticalRegex();

    // Normalize whitespace
    [GeneratedRegex(@"\s+")]
    private static partial Regex WhitespaceRegex();

    /// <summary>
    /// Normalize a team name to its canonical short form.
    /// Removes state suffixes, parentheticals, normalizes accents.
    /// </summary>
    public static string Normalize(string name)
    {
        if (string.IsNullOrWhiteSpace(name))
            return "";

        var result = name.Trim();

        // Remove parenthetical content like "(URU)", "(antigo Esporte Clube Barreira)"
        result = ParentheticalRegex().Replace(result, "");

        // Remove state suffix like "-SP", "-RJ", etc.
        result = StateSuffixRegex().Replace(result, "");

        // Strip trailing state prefix like " SP", " RJ" if it looks like a state after city/club
        result = Regex.Replace(result.Trim(), @"\s+(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)$", "",
            RegexOptions.IgnoreCase);

        // Normalize whitespace
        result = WhitespaceRegex().Replace(result, " ").Trim();

        // Check known mappings
        if (KnownMappings.TryGetValue(result, out var mapped))
            return mapped;

        return result;
    }

    /// <summary>
    /// Check if a team name matches a query (case-insensitive, accent-insensitive, fuzzy).
    /// </summary>
    public static bool Matches(string teamName, string query)
    {
        var normalizedTeam = Normalize(teamName);
        var normalizedQuery = Normalize(query);

        if (string.IsNullOrEmpty(normalizedTeam) || string.IsNullOrEmpty(normalizedQuery))
            return false;

        // Direct match
        if (string.Equals(normalizedTeam, normalizedQuery, StringComparison.OrdinalIgnoreCase))
            return true;

        // Remove accents for comparison
        var teamNoAccent = RemoveAccents(normalizedTeam);
        var queryNoAccent = RemoveAccents(normalizedQuery);

        if (string.Equals(teamNoAccent, queryNoAccent, StringComparison.OrdinalIgnoreCase))
            return true;

        // Contains match (e.g., "Corinthians" matches "Sport Club Corinthians Paulista")
        if (teamNoAccent.Contains(queryNoAccent, StringComparison.OrdinalIgnoreCase) ||
            queryNoAccent.Contains(teamNoAccent, StringComparison.OrdinalIgnoreCase))
            return true;

        return false;
    }

    private static string RemoveAccents(string text)
    {
        var normalized = text.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder();
        foreach (var c in normalized)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        }
        return sb.ToString().Normalize(NormalizationForm.FormC);
    }
}
