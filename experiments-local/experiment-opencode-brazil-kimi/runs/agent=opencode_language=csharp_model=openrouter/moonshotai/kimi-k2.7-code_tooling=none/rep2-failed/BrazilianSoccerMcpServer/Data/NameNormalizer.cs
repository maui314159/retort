using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcpServer.Data;

public static partial class NameNormalizer
{
    private static readonly Dictionary<string, string[]> Synonyms = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Palmeiras"] = ["Palmeiras-SP", "Sociedade Esportiva Palmeiras", "SE Palmeiras"],
        ["Flamengo"] = ["Flamengo-RJ", "Clube de Regatas do Flamengo", "CR Flamengo"],
        ["Corinthians"] = ["Corinthians-SP", "Sport Club Corinthians Paulista", "SC Corinthians Paulista"],
        ["Sao Paulo"] = ["Sao Paulo FC", "São Paulo", "São Paulo FC", "SPFC", "Sao Paulo-SP"],
        ["Santos"] = ["Santos FC", "Santos-SP"],
        ["Vasco"] = ["Vasco da Gama", "CR Vasco da Gama", "Vasco-RJ"],
        ["Fluminense"] = ["Fluminense-RJ", "Fluminense FC"],
        ["Gremio"] = ["Grêmio", "Grêmio-RS", "Gremio-RS", "Grêmio FBPA"],
        ["Internacional"] = ["Internacional-RS", "Sport Club Internacional", "SC Internacional"],
        ["Atletico Mineiro"] = ["Atlético-MG", "Atletico-MG", "Clube Atlético Mineiro"],
        ["Cruzeiro"] = ["Cruzeiro-RS", "Cruzeiro-MG", "Cruzeiro EC"],
        ["Athletico Paranaense"] = ["Athletico-PR", "Atlético-PR", "Atletico-PR", "Club Athletico Paranaense"],
        ["Botafogo"] = ["Botafogo-RJ", "Botafogo FR"],
        ["Bahia"] = ["Bahia-BA", "Esporte Clube Bahia", "EC Bahia"],
        ["Fortaleza"] = ["Fortaleza-CE", "Fortaleza EC"],
        ["Ceara"] = ["Ceará", "Ceará SC", "Ceara-CE"],
        ["Sport"] = ["Sport-PE", "Sport Club do Recife", "Sport Recife"],
        ["Vitoria"] = ["Vitória", "Vitória-BA", "Vitoria-BA", "EC Vitória"],
        ["Goias"] = ["Goiás", "Goiás-ES", "Goiás-GO", "Goias-GO"],
        ["Coritiba"] = ["Coritiba-PR", "Coritiba FC"],
        ["America Mineiro"] = ["América-MG", "America-MG", "América Mineiro"],
        ["America"] = ["América-RJ", "America-RJ"],
        ["Ponte Preta"] = ["Ponte Preta-SP"],
        ["Chapecoense"] = ["Chapecoense-SC", "Associação Chapecoense"],
        ["Figueirense"] = ["Figueirense-SC", "Figueirense FC"],
        ["Joinville"] = ["Joinville-SC"],
        ["Criciuma"] = ["Criciúma", "Criciúma-SC", "Criciuma-SC"],
        ["Avai"] = ["Avaí", "Avaí-SC", "Avai-SC"],
        ["Atletico Goianiense"] = ["Atlético-GO", "Atletico-GO", "AC Goianiense"],
        ["Red Bull Bragantino"] = ["Bragantino", "Bragantino-SP", "RB Bragantino"],
        ["Portuguesa"] = ["Portuguesa-SP"],
        ["Guarani"] = ["Guarani-SP", "Guarani FC"],
        ["Paysandu"] = ["Paysandu-PA", "Paysandu SC"],
        ["Remo"] = ["Remo-PA", "Clube do Remo"],
        ["Nautico"] = ["Náutico", "Náutico-PE", "Nautico-PE"],
        ["Santa Cruz"] = ["Santa Cruz-PE"],
        ["Juventude"] = ["Juventude-RS", "EC Juventude"],
        ["Cuiaba"] = ["Cuiabá", "Cuiabá-MT", "Cuiaba-MT"],
    };

    private static readonly Dictionary<string, string> SynonymLookup = BuildReverseLookup();

    private static Dictionary<string, string> BuildReverseLookup()
    {
        var lookup = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var pair in Synonyms)
        {
            lookup[pair.Key] = pair.Key;
            foreach (var synonym in pair.Value)
            {
                lookup[synonym] = pair.Key;
            }
        }
        return lookup;
    }

    public static string Normalize(string? name)
    {
        if (string.IsNullOrWhiteSpace(name))
            return string.Empty;

        var cleaned = CleanRawName(name);

        if (SynonymLookup.TryGetValue(cleaned, out var normalized))
            return normalized;

        return cleaned;
    }

    public static bool Matches(string? candidate, string? target)
    {
        var normalizedCandidate = Normalize(candidate);
        var normalizedTarget = Normalize(target);
        return normalizedCandidate.Equals(normalizedTarget, StringComparison.OrdinalIgnoreCase);
    }

    private static string CleanRawName(string name)
    {
        var trimmed = name.Trim();

        // Remove common suffixes like (antigo ...)
        trimmed = ParenthesesSuffixRegex().Replace(trimmed, string.Empty);

        // Remove trailing state suffix " - RJ", "-SP", etc.
        trimmed = StateSuffixRegex().Replace(trimmed, string.Empty);

        trimmed = trimmed.Trim();

        // Remove accents for normalization key while preserving original display names
        var noAccents = RemoveAccents(trimmed);

        // Collapse whitespace
        var collapsed = WhitespaceRegex().Replace(noAccents, " ");

        return collapsed.Trim();
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

    [GeneratedRegex(@"\s*\([^)]*\)\s*", RegexOptions.Compiled)]
    private static partial Regex ParenthesesSuffixRegex();

    [GeneratedRegex(@"\s*-\s*[A-Z]{2}$", RegexOptions.Compiled)]
    private static partial Regex StateSuffixRegex();

    [GeneratedRegex(@"\s+", RegexOptions.Compiled)]
    private static partial Regex WhitespaceRegex();
}
