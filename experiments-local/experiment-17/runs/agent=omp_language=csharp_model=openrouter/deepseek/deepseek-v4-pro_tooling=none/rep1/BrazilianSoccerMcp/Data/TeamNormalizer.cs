using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Normalises Brazilian team names across datasets so "Flamengo-RJ",
/// "Flamengo", and "Clube de Regatas do Flamengo" all resolve to the
/// same canonical key.
/// </summary>
public static partial class TeamNormalizer
{
    /// <summary>Map from canonical key to display name.</summary>
    private static readonly Dictionary<string, string> CanonicalToDisplay = new(StringComparer.OrdinalIgnoreCase)
    {
        ["flamengo"] = "Flamengo",
        ["fluminense"] = "Fluminense",
        ["vasco"] = "Vasco da Gama",
        ["botafogo"] = "Botafogo",
        ["palmeiras"] = "Palmeiras",
        ["corinthians"] = "Corinthians",
        ["sao paulo"] = "São Paulo",
        ["santos"] = "Santos",
        ["gremio"] = "Grêmio",
        ["internacional"] = "Internacional",
        ["atletico mg"] = "Atlético-MG",
        ["atletico mineiro"] = "Atlético-MG",
        ["atletico pr"] = "Athletico-PR",
        ["athletico pr"] = "Athletico-PR",
        ["athletico paranaense"] = "Athletico-PR",
        ["cruzeiro"] = "Cruzeiro",
        ["bahia"] = "Bahia",
        ["sport"] = "Sport",
        ["sport recife"] = "Sport",
        ["fortaleza"] = "Fortaleza",
        ["ceara"] = "Ceará",
        ["goias"] = "Goiás",
        ["coritiba"] = "Coritiba",
        ["chapecoense"] = "Chapecoense",
        ["avai"] = "Avaí",
        ["vitoria"] = "Vitória",
        ["ponte preta"] = "Ponte Preta",
        ["figueirense"] = "Figueirense",
        ["nautico"] = "Náutico",
        ["parana"] = "Paraná",
        ["juventude"] = "Juventude",
        ["criciuma"] = "Criciúma",
        ["joinville"] = "Joinville",
        ["santa cruz"] = "Santa Cruz",
        ["america mg"] = "América-MG",
        ["america mineiro"] = "América-MG",
        ["america rn"] = "América-RN",
        ["bragantino"] = "Bragantino",
        ["red bull bragantino"] = "Bragantino",
        ["guarani"] = "Guarani",
        ["portuguesa"] = "Portuguesa",
        ["paysandu"] = "Paysandu",
        ["gama"] = "Gama",
        ["brasiliense"] = "Brasiliense",
        ["sao caetano"] = "São Caetano",
        ["boca juniors"] = "Boca Juniors",
        ["river plate"] = "River Plate",
        ["racing"] = "Racing",
        ["independiente"] = "Independiente",
        ["san lorenzo"] = "San Lorenzo",
        ["estudiantes"] = "Estudiantes",
        ["velez sarsfield"] = "Vélez Sarsfield",
        ["penarol"] = "Peñarol",
        ["nacional"] = "Nacional",
        ["olimpia"] = "Olimpia",
        ["cerro porteno"] = "Cerro Porteño",
        ["libertad"] = "Libertad",
        ["colo colo"] = "Colo-Colo",
        ["universidad de chile"] = "Universidad de Chile",
        ["universidad catolica"] = "Universidad Católica",
        ["barcelona"] = "Barcelona-EQU",
        ["barcelona equ"] = "Barcelona-EQU",
        ["emelec"] = "Emelec",
        ["liga de quito"] = "Liga de Quito",
        ["sporting cristal"] = "Sporting Cristal",
        ["alianza lima"] = "Alianza Lima",
        ["universitario"] = "Universitario",
        ["bolivar"] = "Bolívar",
        ["the strongest"] = "The Strongest",
        ["toluca"] = "Toluca",
        ["tigres"] = "Tigres",
        ["club america"] = "América-MEX",
        ["cruz azul"] = "Cruz Azul",
        ["atletico nacional"] = "Atlético Nacional",
        ["junior"] = "Junior",
        ["independiente medellin"] = "Independiente Medellín",
        ["millonarios"] = "Millonarios",
        ["santa fe"] = "Santa Fe",
        ["deportivo cali"] = "Deportivo Cali",
        ["caracas"] = "Caracas",
        ["deportivo tachira"] = "Deportivo Táchira",
    };

    // Patterns to strip from team names
    [GeneratedRegex(@"\s*-\s*(SP|RJ|MG|RS|PR|SC|BA|PE|CE|GO|DF|RN|AL|PA|AM|MA|PB|SE|ES|MT|MS|PI|RO|TO|AP|AC|RR)$", RegexOptions.IgnoreCase)]
    private static partial Regex StateSuffixPattern();

    [GeneratedRegex(@"\(.*?\)")]
    private static partial Regex ParenthesesPattern();

    [GeneratedRegex(@"\s+")]
    private static partial Regex WhitespacePattern();

    /// <summary>
    /// Returns the canonical key for a raw team name. Strips state suffixes,
    /// parenthesised qualifiers, </summary>
    public static string Normalize(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        var name = raw.Trim();

        // Strip common long-form prefixes/suffixes
        name = StripClubPrefixes(name);

        // Strip state suffix: "Flamengo-RJ" → "Flamengo"
        name = StateSuffixPattern().Replace(name, "");

        // Strip parenthesised qualifiers: "Nacional (URU)" → "Nacional"
        name = ParenthesesPattern().Replace(name, "");

        // Strip " - UF" style (common in Brazilian Cup)
        // e.g., "Gama - DF" → "Gama"
        name = Regex.Replace(name, @"\s*-\s*(SP|RJ|MG|RS|PR|SC|BA|PE|CE|GO|DF|RN|AL|PA|AM|MA|PB|SE|ES|MT|MS|PI|RO|TO|AP|AC|RR)$", "", RegexOptions.IgnoreCase);

        // Normalize whitespace and case
        name = WhitespacePattern().Replace(name, " ").Trim().ToLowerInvariant()
            .Replace("á", "a").Replace("à", "a").Replace("ã", "a").Replace("â", "a")
            .Replace("é", "e").Replace("ê", "e")
            .Replace("í", "i")
            .Replace("ó", "o").Replace("ô", "o").Replace("õ", "o")
            .Replace("ú", "u").Replace("ü", "u")
            .Replace("ç", "c");

        // Try direct lookup in canonical map
        if (CanonicalToDisplay.TryGetValue(name, out var display))
            return display;

        // Try matching without accent-stripped version
        foreach (var kvp in CanonicalToDisplay)
        {
            if (kvp.Key == name)
                return kvp.Value;
        }

        // Return title-cased raw name as fallback
        return CultureAwareTitleCase(name);
    }

    private static string StripClubPrefixes(string name)
    {
        // Strip common prefixes
        var prefixes = new[]
        {
            "sport club", "clube de regatas", "clube atletico", "atletico clube",
            "associacao atletica", "sociedade esportiva", "esporte clube",
            "gremio esportivo", "gremio foot-ball", "foot ball club",
            "sport club do", "clube do", "sport club", "club de regatas",
            "botafogo de futebol e regatas", "sao paulo futebol clube",
            "santos futebol clube",
        };

        var lower = name.ToLowerInvariant().Trim();
        foreach (var prefix in prefixes)
        {
            if (lower.StartsWith(prefix + " "))
                return name[(prefix.Length + 1)..].Trim();
        }
        return name;
    }

    private static string CultureAwareTitleCase(string name)
    {
        // Simple title casing preserving Portuguese conventions
        var words = name.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        for (int i = 0; i < words.Length; i++)
        {
            if (words[i].Length > 0)
            {
                var prepositions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
                { "de", "da", "do", "das", "dos", "e", "a", "o", "no", "na", "em" };
                if (i > 0 && i < words.Length - 1 && prepositions.Contains(words[i]))
                    words[i] = words[i].ToLowerInvariant();
                else
                    words[i] = char.ToUpperInvariant(words[i][0]) + words[i][1..].ToLowerInvariant();
            }
        }
        return string.Join(" ", words);
    }

    /// <summary>Check if the normalised name contains a search term.</summary>
    public static bool Matches(string? teamName, string searchTerm)
    {
        var normalized = Normalize(teamName);
        var search = searchTerm.ToLowerInvariant()
            .Replace("á", "a").Replace("ã", "a").Replace("â", "a")
            .Replace("é", "e").Replace("ê", "e")
            .Replace("í", "i")
            .Replace("ó", "o").Replace("ô", "o").Replace("õ", "o")
            .Replace("ú", "u").Replace("ç", "c");
        return normalized.ToLowerInvariant().Contains(search);
    }
}