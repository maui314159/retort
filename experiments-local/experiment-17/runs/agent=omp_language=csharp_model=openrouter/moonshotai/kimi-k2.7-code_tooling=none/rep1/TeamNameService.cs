using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp;

public sealed class TeamNameService
{
    private readonly IReadOnlySet<string> _knownOriginalNames;
    private readonly Dictionary<string, string> _aliasToCanonical;

    public TeamNameService(IEnumerable<string> names)
    {
        _knownOriginalNames = new HashSet<string>(names.Where(n => !string.IsNullOrWhiteSpace(n)), StringComparer.OrdinalIgnoreCase);

        _aliasToCanonical = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["atletico mineiro"] = "Atlético-MG",
            ["atletico-mg"] = "Atlético-MG",
            ["atletico mg"] = "Atlético-MG",
            ["clube atletico mineiro"] = "Atlético-MG",
            ["athletico paranaense"] = "Athletico-PR",
            ["athletico-pr"] = "Athletico-PR",
            ["atletico paranaense"] = "Athletico-PR",
            ["atletico-pr"] = "Athletico-PR",
            ["clube atletico paranaense"] = "Athletico-PR",
            ["america mineiro"] = "América-MG",
            ["america-mg"] = "América-MG",
            ["america mg"] = "América-MG",
            ["boa esporte"] = "Boa Esporte",
            ["ceara"] = "Ceará",
            ["coritiba"] = "Coritiba",
            ["cruzeiro"] = "Cruzeiro",
            ["flamengo"] = "Flamengo",
            ["fluminense"] = "Fluminense",
            ["fortaleza"] = "Fortaleza",
            ["gremio"] = "Grêmio",
            ["internacional"] = "Internacional",
            ["palmeiras"] = "Palmeiras",
            ["parana"] = "Paraná",
            ["ponte preta"] = "Ponte Preta",
            ["santos"] = "Santos",
            ["sao paulo"] = "São Paulo",
            ["sport"] = "Sport",
            ["vasco"] = "Vasco",
            ["vitoria"] = "Vitória",
            ["chapecoense"] = "Chapecoense",
            ["corinthians"] = "Corinthians",
            ["botafogo"] = "Botafogo",
            ["goias"] = "Goiás",
            ["bahia"] = "Bahia",
            ["juventude"] = "Juventude",
            ["red bull bragantino"] = "Red Bull Bragantino",
        };
    }

    public static string Normalize(string? name)
    {
        if (string.IsNullOrWhiteSpace(name))
            return string.Empty;

        var cleaned = name.Trim();

        // Strip state suffix " - RJ" / "-RJ/SP" and parenthetical suffixes like "(URU)"
        cleaned = Regex.Replace(cleaned, @"\s*\([^)]*\)", string.Empty);
        cleaned = Regex.Replace(cleaned, @"-[A-Z]{2}$", string.Empty);

        cleaned = cleaned.ToLowerInvariant().Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(cleaned.Length);
        foreach (var c in cleaned)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        }
        cleaned = sb.ToString().Normalize(NormalizationForm.FormC);

        cleaned = Regex.Replace(cleaned, @"[^a-z0-9\s]", " ");
        cleaned = Regex.Replace(cleaned, @"\s+", " ").Trim();

        return cleaned;
    }

    public string GetDisplayName(string? name)
    {
        if (string.IsNullOrWhiteSpace(name))
            return string.Empty;

        var normalized = Normalize(name);
        if (_aliasToCanonical.TryGetValue(normalized, out var canonical))
            return canonical;

        var stripped = Regex.Replace(name, @"\s*\([^)]*\)", string.Empty);
        stripped = Regex.Replace(stripped, @"-[A-Z]{2}$", string.Empty).Trim();
        return stripped;
    }

    public IReadOnlyList<string> FindTeams(string query)
    {
        var normalizedQuery = Normalize(query);
        if (string.IsNullOrEmpty(normalizedQuery))
            return Array.Empty<string>();

        var candidates = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var original in _knownOriginalNames)
        {
            var normalizedOriginal = Normalize(original);
            if (normalizedOriginal == normalizedQuery ||
                (normalizedQuery.Length >= 3 && normalizedOriginal.Contains(normalizedQuery)) ||
                (normalizedOriginal.Length >= 3 && normalizedQuery.Contains(normalizedOriginal)))
            {
                candidates.Add(GetDisplayName(original));
            }
        }

        if (candidates.Count == 0 && _aliasToCanonical.TryGetValue(normalizedQuery, out var aliasCanonical))
            candidates.Add(aliasCanonical);

        return candidates.OrderBy(s => s).ToList();
    }

    public bool Matches(string teamName, string query)
    {
        var queryNormal = Normalize(query);
        var teamNormal = Normalize(teamName);
        return teamNormal == queryNormal ||
               (queryNormal.Length >= 3 && teamNormal.Contains(queryNormal)) ||
               (teamNormal.Length >= 3 && queryNormal.Contains(teamNormal));
    }
}
