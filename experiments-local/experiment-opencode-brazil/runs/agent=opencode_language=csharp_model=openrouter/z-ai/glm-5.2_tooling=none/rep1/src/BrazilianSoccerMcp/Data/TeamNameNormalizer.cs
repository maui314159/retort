// Context block
// File: Data/TeamNameNormalizer.cs
// Purpose: Normalize Brazilian soccer team names from multiple Kaggle datasets so that
// queries can match teams regardless of the spelling convention used by each file.
// Datasets use names with state suffixes ("Palmeiras-SP"), parenthetical notes
// ("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"), full official names
// ("Sport Club Corinthians Paulista"), or accented characters ("América - MG").
// This module strips suffixes/parentheticals and applies an alias map of well-known
// Brazilian clubs, while preserving UTF-8 accented characters in the canonical form.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

using System.Text;
using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Data;

/// <summary>Normalizes team names across the bundled datasets.</summary>
public sealed class TeamNameNormalizer
{
    /// <summary>Canonical short names mapped from common long or suffixed spellings.</summary>
    private static readonly Dictionary<string, string> Aliases = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Sport Club Corinthians Paulista"] = "Corinthians",
        ["Sport Club Corinthians Paulista - SP"] = "Corinthians",
        ["Sao Paulo Football Club"] = "Sao Paulo",
        ["São Paulo Futebol Clube"] = "Sao Paulo",
        ["Clube de Regatas do Flamengo"] = "Flamengo",
        ["Fluminense Football Club"] = "Fluminense",
        ["Club de Regatas Vasco da Gama"] = "Vasco",
        ["Vasco da Gama"] = "Vasco",
        ["Santos Futebol Clube"] = "Santos",
        ["Santos FC"] = "Santos",
        ["Sociedade Esportiva Palmeiras"] = "Palmeiras",
        ["Palmeiras Sociadade Esportiva"] = "Palmeiras",
        ["Grêmio Foot-Ball Porto Alegrense"] = "Gremio",
        ["Grêmio"] = "Gremio",
        ["Internacional"] = "Internacional",
        ["Sport Club Internacional"] = "Internacional",
        ["Botafogo de Futebol e Regatas"] = "Botafogo",
        ["Botafogo R.J."] = "Botafogo",
        ["Botafogo-RJ"] = "Botafogo",
        ["Club Athletico Paranaense"] = "Athletico-PR",
        ["Athletico Paranaense"] = "Athletico-PR",
        ["Athletico-PR"] = "Athletico-PR",
        ["Atlético Clube Goianiense"] = "Atletico-GO",
        ["Atlético Goianiense"] = "Atletico-GO",
        ["Atletico-GO"] = "Atletico-GO",
        ["Atlético Mineiro"] = "Atletico-MG",
        ["Atletico-MG"] = "Atletico-MG",
        ["Atlético Mineiro - MG"] = "Atletico-MG",
        ["America Futebol Clube MG"] = "America-MG",
        ["América Futebol Clube"] = "America-MG",
        ["América Mineiro"] = "America-MG",
        ["América - MG"] = "America-MG",
        ["América-RJ"] = "America-RJ",
        ["América-SP"] = "America-SP",
        ["Fortaleza Esporte Clube"] = "Fortaleza",
        ["Fortaleza E.C."] = "Fortaleza",
        ["Esporte Clube Bahia"] = "Bahia",
        ["Esporte Clube Vitória"] = "Vitoria",
        ["Vitória Futebol Clube"] = "Vitoria",
        ["Cruzeiro Esporte Clube"] = "Cruzeiro",
        ["Cruzeiro E.C."] = "Cruzeiro",
        ["Chapecoense"] = "Chapecoense",
        ["Associação Chapecoense de Futebol"] = "Chapecoense",
        ["Boavista Sport Club"] = "Boavista",
        ["Boavista Sport Club (antigo Esporte Clube Barreira)"] = "Boavista",
        ["Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"] = "Boavista",
        ["Operário Ferroviário Esporte Clube"] = "Operario-PR",
        ["Operário Ferroviário"] = "Operario-PR",
        ["Operario"] = "Operario-PR",
        ["Parana Clube"] = "Parana Clube",
        ["Paraná Clube"] = "Parana Clube",
        ["Ponte Preta"] = "Ponte Preta",
        ["Associação Portuguesa de Desportos"] = "Portuguesa",
        ["Portuguesa Santista"] = "Portuguesa Santista",
        ["Portuguesa-SP"] = "Portuguesa",
        ["Red Bull Bragantino"] = "Bragantino",
        ["RB Bragantino"] = "Bragantino",
        ["Bragantino"] = "Bragantino",
        ["Goias Esporte Clube"] = "Goias",
        ["Goiás E.C."] = "Goias",
        ["Cuiaba Esporte Clube"] = "Cuiaba",
        ["Cuiabá"] = "Cuiaba",
        ["Tombense Futebol Clube"] = "Tombense",
        ["Avai"] = "Avai",
        ["Avaí"] = "Avai",
        ["Figueirense Futebol Clube"] = "Figueirense",
        ["Juventude"] = "Juventude",
        ["Esporte Clube Juventude"] = "Juventude",
        ["Esporte Clube Caxias"] = "Caxias",
        ["São José Esporte Clube"] = "Sao Jose",
        ["São José"] = "Sao Jose",
        ["Náutico Capibaribe"] = "Nautico",
        ["Náutico"] = "Nautico",
        ["Santa Cruz Futebol Clube"] = "Santa Cruz",
        ["Sport Recife"] = "Sport",
        ["Sport Club do Recife"] = "Sport",
        ["Sport-PE"] = "Sport",
        ["CSA Centro Sportivo Alagoano"] = "CSA",
        ["Botafogo Futebol Clube Ribeirao Preto"] = "Botafogo-SP",
        ["Botafogo Futebol Clube"] = "Botafogo-SP",
        ["Botafogo-SP"] = "Botafogo-SP",
        ["Confiança Esporte Clube"] = "Confianca",
        ["CRB Clube de Regatas Brasil"] = "CRB",
        ["Clube de Regatas Brasil"] = "CRB",
        ["Vila Nova Futebol Clube"] = "Vila Nova",
        ["Vila Nova-GO"] = "Vila Nova",
        ["Anápolis Futebol Clube"] = "Anapolis",
        ["Anápolis"] = "Anapolis",
        ["Gremio Anapolis"] = "Gremio Anapolis",
        ["Goiânia Esporte Clube"] = "Goiania",
        ["Goiânia"] = "Goiania",
        ["Aparecidense"] = "Aparecidense",
        ["Associação Atlética Aparecidense"] = "Aparecidense",
        ["Iporá Esporte Clube"] = "Ipora",
        ["Iporá"] = "Ipora",
        ["Inter de Limeira"] = "Inter de Limeira",
        ["Inter de Santa Maria"] = "Inter de Santa Maria",
        ["Nacional Futebol Clube"] = "Nacional",
        ["Nacional (URU)"] = "Nacional",
        ["Nacional-URU"] = "Nacional",
        ["Nacional (PAR)"] = "Nacional-PAR",
        ["Barcelona-EQU"] = "Barcelona-EQU",
        ["Barcelona"] = "Barcelona",
        ["Boca Juniors"] = "Boca Juniors",
        ["River Plate"] = "River Plate",
        ["Atletico Nacional"] = "Atletico Nacional",
    };

    /// <summary>Brazilian state abbreviations stripped from trailing suffixes.</summary>
    private static readonly HashSet<string> StateCodes = new(StringComparer.OrdinalIgnoreCase)
    {
        "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA",
        "PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"
    };

    /// <summary>Two-letter country/tournament codes that appear after a dash in international data.</summary>
    private static readonly HashSet<string> ForeignCodes = new(StringComparer.OrdinalIgnoreCase)
    {
        "URU","PAR","EQU","ARG","CHI","COL","PER","BOL","VEN","ECU","MEX","USA"
    };

    /// <summary>Returns the canonical short name for a raw team string.</summary>
    public string Normalize(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
        {
            return string.Empty;
        }

        var trimmed = raw.Trim();

        // Direct alias hit first (covers long official names verbatim).
        if (Aliased(trimmed, out var direct))
        {
            return direct;
        }

        // Strip parenthetical notes: "Team (antigo ...)" -> "Team".
        var noParens = StripParentheses(trimmed);
        if (Aliased(noParens, out var aliasedNoParens))
        {
            return aliasedNoParens;
        }

        // Strip a single trailing "- XX" suffix where XX is a known state or foreign code.
        var noSuffix = StripSuffix(noParens);
        if (Aliased(noSuffix, out var aliasedNoSuffix))
        {
            return aliasedNoSuffix;
        }

        return noSuffix.Trim();
    }

    /// <summary>True when <paramref name="candidate"/> matches <paramref name="query"/> after normalization.</summary>
    public bool Matches(string? candidate, string? query)
    {
        var a = Normalize(candidate);
        var b = Normalize(query);
        if (string.IsNullOrEmpty(a) || string.IsNullOrEmpty(b))
        {
            return false;
        }
        if (string.Equals(a, b, StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }
        // Allow one to contain the other when the normalized forms are not identical,
        // which handles partial user input such as "Corinthians" vs "Corinthians-SP".
        if (a.Contains(b, StringComparison.OrdinalIgnoreCase) || b.Contains(a, StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }
        return false;
    }

    private static bool Aliased(string value, out string canonical)
    {
        if (Aliases.TryGetValue(value, out var found))
        {
            canonical = found;
            return true;
        }
        canonical = value;
        return false;
    }

    private static string StripParentheses(string value)
    {
        var sb = new StringBuilder(value.Length);
        var depth = 0;
        foreach (var c in value)
        {
            if (c == '(')
            {
                depth++;
                continue;
            }
            if (c == ')')
            {
                if (depth > 0)
                {
                    depth--;
                }
                continue;
            }
            if (depth == 0)
            {
                sb.Append(c);
            }
        }
        return CollapseSpaces(sb.ToString());
    }

    private static string StripSuffix(string value)
    {
        // Handles "Team - SP", "Team-SP", "Team-RJ" and similar.
        var collapsed = CollapseSpaces(value);
        var dashIndex = collapsed.LastIndexOf('-');
        if (dashIndex <= 0)
        {
            return collapsed;
        }
        var tail = collapsed.Substring(dashIndex + 1).Trim();
        // Tail may itself include spaces like "R.J."; take the first token.
        var firstToken = tail.Split(' ', StringSplitOptions.RemoveEmptyEntries).FirstOrDefault() ?? tail;
        if (StateCodes.Contains(firstToken) || ForeignCodes.Contains(firstToken))
        {
            return CollapseSpaces(collapsed.Substring(0, dashIndex).Trim());
        }
        return collapsed;
    }

    private static string CollapseSpaces(string value)
    {
        var sb = new StringBuilder(value.Length);
        var lastWasSpace = false;
        foreach (var c in value)
        {
            if (char.IsWhiteSpace(c))
            {
                if (!lastWasSpace)
                {
                    sb.Append(' ');
                }
                lastWasSpace = true;
            }
            else
            {
                sb.Append(c);
                lastWasSpace = false;
            }
        }
        return sb.ToString().Trim();
    }
}
