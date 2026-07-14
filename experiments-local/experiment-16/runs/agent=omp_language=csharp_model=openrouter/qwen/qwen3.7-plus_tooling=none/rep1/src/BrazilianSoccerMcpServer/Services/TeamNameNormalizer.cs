using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcpServer.Services;

public partial class TeamNameNormalizer
{
    private static readonly Dictionary<string, string> TeamAliases = new(StringComparer.OrdinalIgnoreCase)
    {
        // Full names to short names
        { "Sport Club Corinthians Paulista", "Corinthians" },
        { "Sociedade Esportiva Palmeiras", "Palmeiras" },
        { "Clube de Regatas do Flamengo", "Flamengo" },
        { "Fluminense Football Club", "Fluminense" },
        { "São Paulo Futebol Clube", "São Paulo" },
        { "Santos Futebol Clube", "Santos" },
        { "Grêmio Foot-Ball Porto Alegrense", "Grêmio" },
        { "Sport Club do Recife", "Sport" },
        { "Clube Atlético Mineiro", "Atlético-MG" },
        { "Cruzeiro Esporte Clube", "Cruzeiro" },
        { "Club de Regatas Vasco da Gama", "Vasco" },
        { "Botafogo de Futebol e Regatas", "Botafogo" },
        { "Associação Portuguesa de Desportos", "Portuguesa" },
        { "Goiás Esporte Clube", "Goiás" },
        { "Esporte Clube Bahia", "Bahia" },
        { "Esporte Clube Vitória", "Vitória" },
        { "Ceará Sporting Club", "Ceará" },
        { "Fortaleza Esporte Clube", "Fortaleza" },
        { "Sport Club Internacional", "Internacional" },
        { "Figueirense Futebol Clube", "Figueirense" },
        { "Clube Náutico Capibaribe", "Náutico" },
        { "Associação Chapecoense de Futebol", "Chapecoense" },
        { "América Futebol Clube", "América-MG" },
        { "Paysandu Sport Club", "Paysandu" },
        { "Clube do Remo", "Remo" },
        { "Centro Sportivo Alagoano", "CSA" },
        { "Guarani Futebol Clube", "Guarani" },
        { "Ponte Preta", "Ponte Preta" },
        { "Athletico Paranaense", "Athletico-PR" },
        { "Club Athletico Paranaense", "Athletico-PR" },
        { "Atlético Paranaense", "Athletico-PR" },
        { "Joinville Esporte Clube", "Joinville" },
        { "Avaí Futebol Clube", "Avaí" },
        { "Criciúma Esporte Clube", "Criciúma" },
        { "Red Bull Bragantino", "Bragantino" },
        { "Red Bull Brasil", "RB Brasil" },
        { "Esporte Clube Juventude", "Juventude" },
        { "Operário Ferroviário Esporte Clube", "Operário-PR" },
        { "Vila Nova Futebol Clube", "Vila Nova" },
        { "Londrina Esporte Clube", "Londrina" },
        { "Cuiabá Esporte Clube", "Cuiabá" },
        { "Novorizontino", "Novorizontino" },
        { "Mirassol Futebol Clube", "Mirassol" },
        { "América - MG", "América-MG" },
        { "Bahia de Feira - BA", "Bahia de Feira" },
        { "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "Boavista-RJ" },
        { "Nacional (URU)", "Nacional-URU" },
        { "Barcelona-EQU", "Barcelona-ECU" }
    };

    [GeneratedRegex(@"-[A-Z]{2}$")]
    private static partial Regex StateSuffixRegex();

    public static string Normalize(string teamName)
    {
        if (string.IsNullOrWhiteSpace(teamName))
            return string.Empty;

        var name = teamName.Trim();

        if (TeamAliases.TryGetValue(name, out var alias))
            return alias;

        name = StateSuffixRegex().Replace(name, "").Trim();

        if (TeamAliases.TryGetValue(name, out var alias2))
            return alias2;

        return name;
    }

    public static string RemoveAccents(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return string.Empty;

        var normalizedString = text.Normalize(NormalizationForm.FormD);
        var stringBuilder = new StringBuilder();

        foreach (var c in normalizedString)
        {
            var unicodeCategory = CharUnicodeInfo.GetUnicodeCategory(c);
            if (unicodeCategory != UnicodeCategory.NonSpacingMark)
            {
                stringBuilder.Append(c);
            }
        }

        return stringBuilder.ToString().Normalize(NormalizationForm.FormC).ToLowerInvariant();
    }

    public static bool Matches(string team1, string team2)
    {
        var norm1 = RemoveAccents(Normalize(team1));
        var norm2 = RemoveAccents(Normalize(team2));
        return norm1 == norm2 || norm1.Contains(norm2) || norm2.Contains(norm1);
    }
}
