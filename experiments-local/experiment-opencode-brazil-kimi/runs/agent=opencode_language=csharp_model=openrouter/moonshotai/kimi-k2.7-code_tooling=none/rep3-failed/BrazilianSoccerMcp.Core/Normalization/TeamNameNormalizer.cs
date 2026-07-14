// <copyright file="TeamNameNormalizer.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Normalizes team names across heterogeneous datasets.
//
// Implementation notes:
// The source CSVs use different conventions:
//   - "Palmeiras-SP" (with state suffix)
//   - "Palmeiras"    (without suffix)
//   - "Sport Club Corinthians Paulista" (full legal name)
// This normalize produces a canonical short name (e.g. "Palmeiras") while preserving
// the raw display value for tracing and diagnostics.
// </copyright>
namespace BrazilianSoccerMcp.Core.Normalization;

/// <summary>
/// Provides team name normalization across all included datasets.
/// </summary>
public static class TeamNameNormalizer
{
    private static readonly HashSet<string> StateSuffixes = new(StringComparer.OrdinalIgnoreCase)
    {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO"
    };

    /// <summary>
    /// Mapping from common alternate team names to canonical short names.
    /// </summary>
    private static readonly Dictionary<string, string> Aliases = new(StringComparer.OrdinalIgnoreCase)
    {
        // Major clubs - full legal names -> short names
        ["Sport Club Corinthians Paulista"] = "Corinthians",
        ["São Paulo Futebol Clube"] = "São Paulo",
        ["Sao Paulo Futebol Clube"] = "São Paulo",
        ["Sao Paulo"] = "São Paulo",
        ["Clube de Regatas do Flamengo"] = "Flamengo",
        ["Sociedade Esportiva Palmeiras"] = "Palmeiras",
        ["Santos Futebol Clube"] = "Santos",
        ["Grêmio Foot-Ball Porto Alegrense"] = "Grêmio",
        ["Gremio Foot-Ball Porto Alegrense"] = "Grêmio",
        ["Sport Club Internacional"] = "Internacional",
        ["Cruzeiro Esporte Clube"] = "Cruzeiro",
        ["Club de Regatas Vasco da Gama"] = "Vasco",
        ["Vasco da Gama"] = "Vasco",
        ["Esporte Clube Bahia"] = "Bahia",
        ["Fortaleza Esporte Clube"] = "Fortaleza",
        ["Sport Club do Recife"] = "Sport",
        ["Sport-PE"] = "Sport",
        ["Botafogo de Futebol e Regatas"] = "Botafogo",
        ["Fluminense Football Club"] = "Fluminense",

        // Atlético variants - keep state suffix
        ["Clube Atlético Mineiro"] = "Atlético-MG",
        ["Clube Atletico Mineiro"] = "Atlético-MG",
        ["Atlético Mineiro"] = "Atlético-MG",
        ["Atletico Mineiro"] = "Atlético-MG",
        ["Atlético-MG"] = "Atlético-MG",
        ["Atletico-MG"] = "Atlético-MG",
        ["Atlético - MG"] = "Atlético-MG",
        ["Atletico - MG"] = "Atlético-MG",

        ["Atlético Clube Goianiense"] = "Atlético-GO",
        ["Atletico Clube Goianiense"] = "Atlético-GO",
        ["Atlético-GO"] = "Atlético-GO",
        ["Atletico-GO"] = "Atlético-GO",
        ["Atlético - GO"] = "Atlético-GO",
        ["Atletico - GO"] = "Atlético-GO",

        ["Club Athletico Paranaense"] = "Athletico-PR",
        ["Atlético Paranaense"] = "Athletico-PR",
        ["Atletico Paranaense"] = "Athletico-PR",
        ["Atlético-PR"] = "Athletico-PR",
        ["Atletico-PR"] = "Athletico-PR",
        ["Atlético - PR"] = "Athletico-PR",
        ["Atletico - PR"] = "Athletico-PR",

        // Botafogo state variants
        ["Botafogo-RJ"] = "Botafogo",
        ["Botafogo - RJ"] = "Botafogo",
        ["Botafogo-SP"] = "Botafogo-SP",
        ["Botafogo - SP"] = "Botafogo-SP",
        ["Botafogo-BA"] = "Botafogo-BA",
        ["Botafogo - BA"] = "Botafogo-BA",
        ["Botafogo-PB"] = "Botafogo-PB",
        ["Botafogo - PB"] = "Botafogo-PB",
        ["Botafogo Futebol Clube (BA)"] = "Botafogo-BA",
        ["Botafogo Futebol Clube (PB)"] = "Botafogo-PB",

        // América variants
        ["América Futebol Clube"] = "América-MG",
        ["America Futebol Clube"] = "América-MG",
        ["América-MG"] = "América-MG",
        ["America-MG"] = "América-MG",
        ["América - MG"] = "América-MG",
        ["America - MG"] = "América-MG",

        // Paraná / Paranaense clubs
        ["Paraná Clube"] = "Paraná",
        ["Parana Clube"] = "Paraná",
        ["Ceará Sporting Club"] = "Ceará",
        ["Ceara Sporting Club"] = "Ceará",
        ["Goiás Esporte Clube"] = "Goiás",
        ["Goias Esporte Clube"] = "Goiás",
        ["Avaí Futebol Clube"] = "Avaí",
        ["Avai Futebol Clube"] = "Avaí",
        ["Associação Chapecoense de Futebol"] = "Chapecoense",
        ["Associacao Chapecoense de Futebol"] = "Chapecoense",
        ["Coritiba Foot Ball Club"] = "Coritiba",
        ["Figueirense Futebol Clube"] = "Figueirense",
        ["Esporte Clube Vitória"] = "Vitória",
        ["Esporte Clube Vitoria"] = "Vitória",

        // Other Serie A/B clubs
        ["Red Bull Bragantino"] = "Bragantino",
        ["Clube Atlético Bragantino"] = "Bragantino",
        ["Clube Atletico Bragantino"] = "Bragantino",
        ["Guarani Futebol Clube"] = "Guarani",
        ["Ponte Preta"] = "Ponte Preta",
        ["Esporte Clube Juventude"] = "Juventude",
        ["Cuiabá Esporte Clube"] = "Cuiabá",
        ["Cuiaba Esporte Clube"] = "Cuiabá",
        ["Clube Náutico Capibaribe"] = "Náutico",
        ["Clube Nautico Capibaribe"] = "Náutico",
        ["ABC Futebol Clube"] = "ABC",
        ["Santa Cruz Futebol Clube"] = "Santa Cruz",
        ["Esporte Clube São Bento"] = "São Bento",
        ["Esporte Clube Sao Bento"] = "São Bento",
        ["Londrina Esporte Clube"] = "Londrina",
        ["Sampaio Corrêa Futebol Clube"] = "Sampaio Corrêa",
        ["Sampaio Correa Futebol Clube"] = "Sampaio Corrêa",
        ["Paysandu Sport Club"] = "Paysandu",
        ["Vila Nova Futebol Clube"] = "Vila Nova",
        ["Boa Esporte Clube"] = "Boa Esporte",
        ["Rio Branco Football Club"] = "Rio Branco",
        ["Ypiranga Futebol Clube"] = "Ypiranga",
        ["Brasiliense Futebol Clube"] = "Brasiliense",
        ["Mogi Mirim Esporte Clube"] = "Mogi Mirim",
        ["ASA de Arapiraca"] = "ASA",
        ["Oeste Futebol Clube"] = "Oeste",
        ["Esporte Clube Santo André"] = "Santo André",
        ["Esporte Clube Santo Andre"] = "Santo André",
        ["Portuguesa de Desportos"] = "Portuguesa",
        ["Associação Portuguesa de Desportos"] = "Portuguesa",
        ["Associacao Portuguesa de Desportos"] = "Portuguesa",
        ["Esporte Clube Noroeste"] = "Noroeste",
        ["Marília Atlético Clube"] = "Marília",
        ["Marilia Atletico Clube"] = "Marília",
        ["Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"] = "Boavista-RJ",
        ["Boavista Sport Club - RJ"] = "Boavista-RJ",
        ["Boavista - RJ"] = "Boavista-RJ",

        // Non-Brazilian teams that appear in Libertadores should be preserved
        ["Boca Juniors"] = "Boca Juniors",
        ["River Plate"] = "River Plate",
        ["Nacional (URU)"] = "Nacional (URU)",
        ["Peñarol"] = "Peñarol",
        ["Penarol"] = "Peñarol",
        ["Olimpia (PAR)"] = "Olimpia (PAR)",
        ["Cerro Porteño"] = "Cerro Porteño",
        ["Libertad (PAR)"] = "Libertad (PAR)",
        ["Toluca"] = "Toluca",
        ["Barcelona-EQU"] = "Barcelona-EQU",
    };

    private static readonly HashSet<string> KeepSuffixBaseNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "atletico", "atlético", "athletico",
        "america", "américa",
        "botafogo"
    };

    /// <summary>
    /// Normalizes a raw team name into a canonical short name.
    /// </summary>
    public static string Normalize(string rawName)
    {
        if (string.IsNullOrWhiteSpace(rawName))
            return string.Empty;

        var cleaned = rawName.Trim();

        // Direct alias replacement.
        if (Aliases.TryGetValue(cleaned, out var alias))
            return alias;

        // Strip parenthetical annotations and trailing state suffix.
        cleaned = RemoveAnnotationInParentheses(cleaned);
        cleaned = StripStateSuffix(cleaned);

        if (Aliases.TryGetValue(cleaned, out alias))
            return alias;

        return Capitalize(cleaned);
    }

    /// <summary>
    /// Returns true when the normalized forms of two team names match.
    /// </summary>
    public static bool Matches(string nameA, string nameB)
    {
        if (string.IsNullOrWhiteSpace(nameA) || string.IsNullOrWhiteSpace(nameB))
            return false;

        return Normalize(nameA).Equals(Normalize(nameB), StringComparison.OrdinalIgnoreCase);
    }

    private static string RemoveAnnotationInParentheses(string input)
    {
        if (!input.Contains('('))
            return input;

        // Remove text in parentheses, but keep names like "Nacional (URU)" where the
        // parentheses distinguish international teams. For this demo we strip all.
        var span = input.AsSpan();
        var paren = span.IndexOf('(');
        if (paren > 0)
        {
            return span[..paren].ToString().Trim();
        }

        return input;
    }

    private static string StripStateSuffix(string input)
    {
        var parts = input.Split('-', StringSplitOptions.TrimEntries);
        if (parts.Length > 1)
        {
            var last = parts[^1];
            if (StateSuffixes.Contains(last))
            {
                var baseName = string.Join("-", parts[..^1]).Trim();
                // For ambiguous names (Atlético, América, Botafogo) keep the state discriminator.
                if (KeepSuffixBaseNames.Contains(baseName))
                {
                    return $"{baseName}-{last}";
                }
                return baseName;
            }
        }

        return input;
    }

    private static string Capitalize(string input)
    {
        if (string.IsNullOrEmpty(input))
            return input;

        // Preserve common mixed-case patterns like "São Paulo", "Grêmio", etc.
        // We just trim extra spaces and return as-is when containing diacritics.
        return input.Trim();
    }
}
