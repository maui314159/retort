using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Data;

public static class TeamNormalizer
{
    private static readonly Dictionary<string, string> TeamAliases = new(StringComparer.OrdinalIgnoreCase)
    {
        { "flamengo", "flamengo" },
        { "crf", "flamengo" },
        { "fluminense", "fluminense" },
        { "frf", "fluminense" },
        { "palmeiras", "palmeiras" },
        { "sep", "palmeiras" },
        { "corinthians", "corinthians" },
        { "sccp", "corinthians" },
        { "são paulo", "são paulo" },
        { "sao paulo", "são paulo" },
        { "spfc", "são paulo" },
        { "santos", "santos" },
        { "santos fc", "santos" },
        { "grêmio", "grêmio" },
        { "gremio", "grêmio" },
        { "gremio fbpa", "grêmio" },
        { "internacional", "internacional" },
        { "inter", "internacional" },
        { "sc internacional", "internacional" },
        { "atlético mineiro", "atlético mineiro" },
        { "atletico mineiro", "atlético mineiro" },
        { "atletico-mg", "atlético mineiro" },
        { "atlético-mg", "atlético mineiro" },
        { "cam", "atlético mineiro" },
        { "cruzeiro", "cruzeiro" },
        { "cecr", "cruzeiro" },
        { "botafogo", "botafogo" },
        { "botafogo-rj", "botafogo" },
        { "brf", "botafogo" },
        { "vasco", "vasco da gama" },
        { "vasco da gama", "vasco da gama" },
        { "vasco da gama-rj", "vasco da gama" },
        { "crvasco", "vasco da gama" },
        { "coritiba", "coritiba" },
        { "cfc", "coritiba" },
        { "athletico paranaense", "athletico paranaense" },
        { "athletico-pr", "athletico paranaense" },
        { "cap", "athletico paranaense" },
        { "bahia", "bahia" },
        { "ec bahia", "bahia" },
        { "fortaleza", "fortaleza" },
        { "fortaleza ec", "fortaleza" },
        { "goiás", "goiás" },
        { "goias", "goiás" },
        { "ec vitória", "vitória" },
        { "vitoria", "vitória" },
        { "cuiabá", "cuiabá" },
        { "cuiaba", "cuiabá" },
        { "bragantino", "bragantino" },
        { "red bull bragantino", "bragantino" },
        { "america mineiro", "américa mineiro" },
        { "américa-mg", "américa mineiro" },
        { "atletico goianiense", "atlético goianiense" },
        { "atletico-go", "atlético goianiense" },
        { "acg", "atlético goianiense" }
    };

    public static string Normalize(string teamName)
    {
        if (string.IsNullOrWhiteSpace(teamName)) return "";

        var normalized = teamName.Trim().ToLowerInvariant();

        // Remove state suffixes like "-SP", "-RJ", etc.
        normalized = Regex.Replace(normalized, @"-\w{2}$", "");

        // Remove some common suffixes
        normalized = Regex.Replace(normalized, @"\s+(ec|esporte clube|futebol clube|fc|sport club|sc)\b.*", "");
        normalized = Regex.Replace(normalized, @"\(antigo.*\)", "").Trim();

        // Look up in aliases
        if (TeamAliases.TryGetValue(normalized, out var alias))
        {
            return alias;
        }

        // Check if any alias is contained in the normalized name
        foreach (var kvp in TeamAliases)
        {
            if (normalized.Contains(kvp.Key, StringComparison.OrdinalIgnoreCase))
            {
                return kvp.Value;
            }
        }

        return normalized;
    }
}
