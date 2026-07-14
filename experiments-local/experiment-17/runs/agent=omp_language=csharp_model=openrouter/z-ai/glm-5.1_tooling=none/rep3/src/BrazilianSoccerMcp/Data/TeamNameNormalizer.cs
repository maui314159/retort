namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Normalizes Brazilian soccer team names across different naming conventions
/// found in the datasets (with/without state suffix, full names, etc.).
/// </summary>
public static class TeamNameNormalizer
{
    private static readonly char[] StatePrefix = ['-'];

    private static readonly HashSet<string> BrazilianStates = new(StringComparer.OrdinalIgnoreCase)
    {
        "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
        "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
        "RO", "RR", "RS", "SC", "SE", "SP", "TO"
    };

    /// <summary>
    /// Normalizes a team name by removing state suffixes and standardizing
    /// common naming variations.
    /// </summary>
    public static string Normalize(string name)
    {
        if (string.IsNullOrWhiteSpace(name))
            return string.Empty;

        var trimmed = name.Trim().Trim('"');

        // First check: if the name (as-is) maps to a known canonical form, return immediately.
        // This prevents stripping state suffixes from names like "Athletico-PR" that are canonical.
        var mapped = MapKnownName(trimmed);
        if (mapped is not null) return mapped;

        // Remove state suffix like "-SP", "-RJ" from names like "Palmeiras-SP"
        var dashIndex = trimmed.LastIndexOfAny(StatePrefix);
        if (dashIndex > 0)
        {
            var suffix = trimmed[(dashIndex + 1)..].Trim();
            if (BrazilianStates.Contains(suffix))
            {
                trimmed = trimmed[..dashIndex].Trim();
            }
        }

        // Check again after stripping
        mapped = MapKnownName(trimmed);
        if (mapped is not null) return mapped;

        return trimmed;
    }

    private static string? MapKnownName(string name) => name switch
    {
        "Sport Club Corinthians Paulista" => "Corinthians",
        "São Paulo Futebol Clube" => "São Paulo",
        "Sociedade Esportiva Palmeiras" => "Palmeiras",
        "Clube de Regatas do Flamengo" => "Flamengo",
        "Clube de Regatas Vasco da Gama" => "Vasco",
        "Club de Regatas Vasco da Gama" => "Vasco",
        "Fluminense Football Club" => "Fluminense",
        "Botafogo de Futebol e Regatas" => "Botafogo",
        "Grêmio Foot-Ball Porto Alegrense" => "Grêmio",
        "Sport Club Internacional" => "Internacional",
        "Athletico Paranaense" => "Athletico-PR",
        "Atlético Paranaense" => "Athletico-PR",
        "Athletico-PR" => "Athletico-PR",
        "Atlético-MG" => "Atlético-MG",
        "Atletico-MG" => "Atlético-MG",
        "América-MG" => "América-MG",
        "Ceará Sporting Club" => "Ceará",
        "Ceara" => "Ceará",
        "Fortaleza Esporte Clube" => "Fortaleza",
        "Esporte Clube Bahia" => "Bahia",
        "EC Bahia" => "Bahia",
        "EC Vitória" => "Vitória",
        "Vitória-BA" => "Vitória",
        "Red Bull Bragantino" => "Bragantino",
        "RB Bragantino" => "Bragantino",
        "Boavista Sport Club (antigo Esporte Clube Barreira)" => "Boavista",
        "Sao Paulo" => "São Paulo",
        "Gremio" => "Grêmio",
        "Atletico Goianiense" => "Atlético-GO",
        "Atlético Goianiense" => "Atlético-GO",
        "Atletico-GO" => "Atlético-GO",
        "Avaí" => "Avaí",
        "Avai" => "Avaí",
        "Paraná Clube" => "Paraná",
        "Parana" => "Paraná",
        "Figueirense" => "Figueirense",
        "Chapecoense" => "Chapecoense",
        "Criciúma" => "Criciúma",
        "Criciuma" => "Criciúma",
        "Operário-PR" => "Operário-PR",
        "Operario-PR" => "Operário-PR",
        "Ponte Preta" => "Ponte Preta",
        _ => null
    };

    /// <summary>
    /// Checks if a team name matches a query after normalization.
    /// Uses case-insensitive, accent-insensitive comparison.
    /// </summary>
    public static bool Matches(string teamName, string query)
    {
        var normalizedTeam = Normalize(teamName);
        var normalizedQuery = Normalize(query);

        if (string.Equals(normalizedTeam, normalizedQuery, StringComparison.OrdinalIgnoreCase))
            return true;

        if (normalizedTeam.Contains(normalizedQuery, StringComparison.OrdinalIgnoreCase))
            return true;

        return RemoveDiacritics(normalizedTeam).Contains(RemoveDiacritics(normalizedQuery), StringComparison.OrdinalIgnoreCase);
    }

    private static string RemoveDiacritics(string text)
    {
        var normalizedString = text.Normalize(System.Text.NormalizationForm.FormD);
        var sb = new System.Text.StringBuilder(normalizedString.Length);
        foreach (var c in normalizedString)
        {
            if (System.Globalization.CharUnicodeInfo.GetUnicodeCategory(c) != System.Globalization.UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        }
        return sb.ToString();
    }
}
