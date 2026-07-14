using System.Globalization;
using System.Text;

namespace BrazilianSoccerMCP.Data;

public static class TeamNormalizer
{
    private static readonly Dictionary<string, string> NormalizedNames = new(StringComparer.OrdinalIgnoreCase)
    {
        // Atlético variants
        ["Atlético-MG"] = "Atlético Mineiro",
        ["Atletico-MG"] = "Atlético Mineiro",
        ["Atlético Mineiro"] = "Atlético Mineiro",
        ["Atletico Mineiro"] = "Atlético Mineiro",

        ["Atlético-PR"] = "Athletico Paranaense",
        ["Atletico-PR"] = "Athletico Paranaense",
        ["Atlético Paranaense"] = "Athletico Paranaense",
        ["Atletico Paranaense"] = "Athletico Paranaense",
        ["Athletico-PR"] = "Athletico Paranaense",
        ["Athletico Paranaense"] = "Athletico Paranaense",

        ["Atlético-GO"] = "Atlético Goianiense",
        ["Atletico-GO"] = "Atlético Goianiense",
        ["Atlético Goianiense"] = "Atlético Goianiense",
        ["Atletico Goianiense"] = "Atlético Goianiense",

        // Common abbreviated forms
        ["A.b.c."] = "ABC",
        ["A.s.a."] = "ASA",
        ["C.r.b."] = "CRB",
        ["C.s.a."] = "CSA",
        ["C.r.a.c."] = "CRAC",

        // São Paulo variants
        ["Sao Paulo"] = "São Paulo",
        ["Sao Paulo-SP"] = "São Paulo",

        // Other common variants
        ["América - MG"] = "América Mineiro",
        ["América-MG"] = "América Mineiro",
        ["America-MG"] = "América Mineiro",
        ["América Mineiro"] = "América Mineiro",
        ["America Mineiro"] = "América Mineiro",

        ["América - RN"] = "América de Natal",
        ["América-RN"] = "América de Natal",
        ["America-RN"] = "América de Natal",

        ["Grêmio - RS"] = "Grêmio",
        ["Gremio - RS"] = "Grêmio",
        ["Gremio"] = "Grêmio",

        ["Náutico - PE"] = "Náutico",
        ["Nautico - PE"] = "Náutico",
        ["Nautico"] = "Náutico",
    };

    private static readonly CompareInfo CompareInfo = CultureInfo.InvariantCulture.CompareInfo;

    public static string Normalize(string name)
    {
        if (string.IsNullOrWhiteSpace(name))
            return "";

        name = name.Trim();

        // Strip dots: "A.b.c." -> "ABC"
        if (name.Contains('.'))
        {
            name = name.Replace(".", "");
        }

        // Strip state suffix: anything after last "-" if it looks like a 2-letter state code
        var lastDash = name.LastIndexOf('-');
        if (lastDash > 0 && lastDash == name.Length - 3)
        {
            var suffix = name[(lastDash + 1)..];
            if (suffix.Length == 2 && suffix.All(char.IsUpper))
            {
                name = name[..lastDash].Trim();
            }
        }

        // Strip trailing " - XX" pattern (e.g., "América - MG")
        var spaceDashSpace = name.LastIndexOf(" - ");
        if (spaceDashSpace > 0 && spaceDashSpace == name.Length - 5)
        {
            var suffix = name[(spaceDashSpace + 3)..];
            if (suffix.Length == 2 && suffix.All(char.IsUpper))
            {
                name = name[..spaceDashSpace].Trim();
            }
        }

        // Look up in normalization dictionary
        if (NormalizedNames.TryGetValue(name, out var normalized))
            return normalized;

        return name;
    }

    public static bool Matches(string name1, string name2)
    {
        var n1 = Normalize(name1);
        var n2 = Normalize(name2);

        return CompareInfo.Compare(n1, n2, CompareOptions.IgnoreNonSpace | CompareOptions.IgnoreCase) == 0;
    }
}