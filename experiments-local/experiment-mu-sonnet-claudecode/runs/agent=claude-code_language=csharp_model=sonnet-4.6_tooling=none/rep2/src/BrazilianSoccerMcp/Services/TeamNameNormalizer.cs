using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Services;

public static partial class TeamNameNormalizer
{
    private static readonly Dictionary<string, string> _aliases = new(StringComparer.OrdinalIgnoreCase)
    {
        // Brasileirão state-suffix → canonical
        ["Atletico-MG"] = "Atlético Mineiro",
        ["Atletico Mineiro"] = "Atlético Mineiro",
        ["Atletico-GO"] = "Atlético Goianiense",
        ["Atletico-PR"] = "Athletico Paranaense",
        ["Athletico-PR"] = "Athletico Paranaense",
        ["Athletico Paranaense"] = "Athletico Paranaense",
        ["Bragantino-SP"] = "Red Bull Bragantino",
        ["RB Bragantino"] = "Red Bull Bragantino",
        ["Red Bull Bragantino"] = "Red Bull Bragantino",
        ["Gremio"] = "Grêmio",
        ["Fluminense-RJ"] = "Fluminense",
        ["Flamengo-RJ"] = "Flamengo",
        ["Palmeiras-SP"] = "Palmeiras",
        ["Corinthians-SP"] = "Corinthians",
        ["Santos-SP"] = "Santos",
        ["Sao Paulo-SP"] = "São Paulo",
        ["Sao Paulo"] = "São Paulo",
        ["Vasco-RJ"] = "Vasco da Gama",
        ["Vasco"] = "Vasco da Gama",
        ["Vasco da Gama"] = "Vasco da Gama",
        ["Botafogo-RJ"] = "Botafogo",
        ["Cruzeiro-MG"] = "Cruzeiro",
        ["Internacional-RS"] = "Internacional",
        ["Internacional RS"] = "Internacional",
        ["Sport-PE"] = "Sport Recife",
        ["Sport Recife"] = "Sport Recife",
        ["Sport Club do Recife"] = "Sport Recife",
        ["Bahia-BA"] = "Bahia",
        ["Fortaleza-CE"] = "Fortaleza",
        ["Ceara-CE"] = "Ceará",
        ["Ceara"] = "Ceará",
        ["Vitoria-BA"] = "Vitória",
        ["Vitoria"] = "Vitória",
        ["Nautico-PE"] = "Náutico",
        ["Santa Cruz-PE"] = "Santa Cruz",
        ["Portuguesa-SP"] = "Portuguesa",
        ["Goias-GO"] = "Goiás",
        ["Goias"] = "Goiás",
        ["Coritiba-PR"] = "Coritiba",
        ["Avai-SC"] = "Avaí",
        ["Avai"] = "Avaí",
        ["Joinville-SC"] = "Joinville",
        ["Ponte Preta-SP"] = "Ponte Preta",
        ["Chapecoense-SC"] = "Chapecoense",
        ["Gremio-RS"] = "Grêmio",
        ["Parana-PR"] = "Paraná",
        ["Parana"] = "Paraná",
        ["Guarani-SP"] = "Guarani",
        ["Criciuma-SC"] = "Criciúma",
        ["Criciuma"] = "Criciúma",
        ["Figueirense-SC"] = "Figueirense",
        ["Americana-SP"] = "Americana",
        ["Botafogo-PB"] = "Botafogo-PB",
        ["CSA-AL"] = "CSA",
        ["Sampaio Correa-MA"] = "Sampaio Corrêa",
        ["CRB-AL"] = "CRB",
        ["ABC-RN"] = "ABC",
        ["Luverdense-MT"] = "Luverdense",
        ["America-MG"] = "América Mineiro",
        ["América-MG"] = "América Mineiro",
        ["América MG"] = "América Mineiro",
        ["América - MG"] = "América Mineiro",
        ["America - MG"] = "América Mineiro",
        ["Fluminense FC"] = "Fluminense",
        ["Clube de Regatas do Flamengo"] = "Flamengo",
        ["Corinthians Paulista"] = "Corinthians",
        ["Sport Club Corinthians Paulista"] = "Corinthians",
        ["Santos FC"] = "Santos",
        ["Atletico MG"] = "Atlético Mineiro",
    };

    [GeneratedRegex(@"-([A-Z]{2})$")]
    private static partial Regex StateSuffixRegex();

    [GeneratedRegex(@"\s+-\s+[A-Z]{2}$")]
    private static partial Regex StateSuffixWithSpacesRegex();

    public static string Normalize(string? name)
    {
        if (string.IsNullOrWhiteSpace(name)) return "";

        name = name.Trim();

        // Check alias with full original name first
        if (_aliases.TryGetValue(name, out var canonical))
            return canonical;

        // Remove content in parentheses (e.g., "(antigo Esporte Clube Barreira)")
        name = Regex.Replace(name, @"\s*\(.*?\)\s*", " ").Trim();

        // Check alias after removing parenthetical content
        if (_aliases.TryGetValue(name, out canonical))
            return canonical;

        // Remove state suffix with spaces like " - MG" (must check before dash-suffix)
        name = StateSuffixWithSpacesRegex().Replace(name, "").Trim();

        // Check alias after removing spaced state suffix
        if (_aliases.TryGetValue(name, out canonical))
            return canonical;

        // Remove state suffix like "-SP", "-RJ" at end
        name = StateSuffixRegex().Replace(name, "").Trim();

        // Check alias after stripping dash-suffix
        if (_aliases.TryGetValue(name, out canonical))
            return canonical;

        return name;
    }

    public static bool Matches(string? name1, string? searchTerm)
    {
        if (string.IsNullOrWhiteSpace(name1) || string.IsNullOrWhiteSpace(searchTerm))
            return false;

        var normalized1 = Normalize(name1);
        var normalizedSearch = Normalize(searchTerm);

        return normalized1.Equals(normalizedSearch, StringComparison.OrdinalIgnoreCase)
            || normalized1.Contains(normalizedSearch, StringComparison.OrdinalIgnoreCase)
            || normalizedSearch.Contains(normalized1, StringComparison.OrdinalIgnoreCase)
            || name1.Contains(searchTerm, StringComparison.OrdinalIgnoreCase);
    }
}
