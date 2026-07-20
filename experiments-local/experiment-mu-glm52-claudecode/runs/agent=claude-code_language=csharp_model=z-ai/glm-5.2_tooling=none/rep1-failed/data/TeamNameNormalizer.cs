// =============================================================================
// File: Data/TeamNameNormalizer.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   The six Kaggle datasets use wildly different team-naming conventions:
//     - Brasileirao_Matches.csv        : "Palmeiras-SP", "Flamengo-RJ"
//     - Brazilian_Cup_Matches.csv      : "América - MG",
//                                        "Boavista Sport Club (antigo ...) - RJ"
//     - Libertadores_Matches.csv       : "Nacional (URU)", "Barcelona-EQU"
//     - BR-Football-Dataset.csv        : "Sao Paulo", "Flamengo" (no suffix)
//     - novo_campeonato_brasileiro.csv : "Guarani", "Athletico-PR", "Grêmio"
//     - fifa_data.csv                  : "FC Barcelona", "Atlético Mineiro",
//                                        "Paris Saint-Germain"
//   Without normalization, "Palmeiras-SP", "Palmeiras", and "Sociedade
//   Esportiva Palmeiras" would never match.
//
// Approach:
//   Normalize(name) returns a canonical lowercase ASCII key:
//     1. Strip parenthetical asides  "(antigo Esporte Clube Barreira)"
//     2. Drop trailing state / country suffixes:
//          "-SP", " - MG", "-RJ", "-URU", "-EQU"  (2-3 letter codes)
//     3. Remove diacritics (São Paulo -> sao paulo, Grêmio -> gremio)
//     4. Drop common club legal-form tokens: fc, sc, ec, clube, club,
//        sport, de, do, da, the, atletico-paranaense stays "atletico"
//        (handled via alias map for known long-form names)
//     5. Trim stray punctuation/whitespace.
//   A small alias map resolves known full legal names ("Sociedade Esportiva
//   Palmeiras" -> "palmeiras") before the generic pipeline.
//
// CanonicalDisplay(name) returns a human-friendly short form derived from the
// normalized key (title-cased), used when the caller has no prettier source.
// =============================================================================
namespace BrazilianSoccerMcp.Data;

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

public static class TeamNameNormalizer
{
    // Full legal / alternate names -> canonical short key. Applied first.
    private static readonly Dictionary<string, string> AliasMap = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Sociedade Esportiva Palmeiras"] = "palmeiras",
        ["Sport Club Corinthians Paulista"] = "corinthians",
        ["Clube de Regatas do Flamengo"] = "flamengo",
        ["Fluminense Football Club"] = "fluminense",
        ["São Paulo Futebol Clube"] = "sao paulo",
        ["Sao Paulo Futebol Clube"] = "sao paulo",
        ["São Paulo FC"] = "sao paulo",
        ["Sao Paulo FC"] = "sao paulo",
        ["Club de Regatas Vasco da Gama"] = "vasco",
        ["Vasco da Gama"] = "vasco",
        ["Grêmio Foot-Ball Porto Alegrense"] = "gremio",
        ["Sport Club Internacional"] = "internacional",
        ["Internacional"] = "internacional",
        ["Atlético Mineiro"] = "atletico mineiro",
        ["Atletico Mineiro"] = "atletico mineiro",
        ["Clube Atlético Mineiro"] = "atletico mineiro",
        ["Athletico Paranaense"] = "athletico paranaense",
        ["Atlético Paranaense"] = "athletico paranaense",
        ["Club Athletico Paranaense"] = "athletico paranaense",
        ["Fortaleza Esporte Clube"] = "fortaleza",
        ["Esporte Clube Bahia"] = "bahia",
        ["Bahia"] = "bahia",
        [" Cruzeiro Esporte Clube"] = "cruzeiro",
        ["Santos Futebol Clube"] = "santos",
        ["Botafogo de Futebol e Regatas"] = "botafogo",
        ["Botafogo"] = "botafogo",
        ["Goiás Esporte Clube"] = "goias",
        ["Goias Esporte Clube"] = "goias",
        ["Coritiba"] = "coritiba",
        ["Sport Club do Recife"] = "sport",
        ["Sport Recife"] = "sport",
        ["Sport-PE"] = "sport",
        ["Criciúma Esporte Clube"] = "criciuma",
        ["Avaí Futebol Clube"] = "avai",
        ["Avai"] = "avai",
    };

    // Trailing state/country suffix patterns: "-SP", " - MG", "-URU", "-EQU".
    private static readonly Regex StateSuffix = new(
        @"\s*-\s*([A-Za-z]{2,3})\s*$", RegexOptions.Compiled);

    // Parenthetical asides anywhere in the string.
    private static readonly Regex Paren = new(
        @"\([^)]*\)", RegexOptions.Compiled);

    public static string Normalize(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return "";

        string s = raw.Trim();

        // 1. Alias resolution (case-insensitive) on the verbatim input.
        if (AliasMap.TryGetValue(s, out var aliased))
            return aliased;

        // 2. Drop parenthetical asides.
        s = Paren.Replace(s, "");

        // 3. Drop trailing state / country suffix.
        s = StateSuffix.Replace(s, "");

        // 4. Remove diacritics.
        s = RemoveDiacritics(s);

        // 5. Lowercase, collapse punctuation to spaces.
        s = s.ToLowerInvariant();
        var sb = new StringBuilder(s.Length);
        foreach (var ch in s)
        {
            if (char.IsLetterOrDigit(ch)) sb.Append(ch);
            else sb.Append(' ');
        }
        s = sb.ToString();

        // 6. Drop common legal-form / filler tokens.
        var tokens = new List<string>();
        foreach (var tok in s.Split(' ', StringSplitOptions.RemoveEmptyEntries))
        {
            switch (tok)
            {
                case "fc":
                case "sc":
                case "ec":
                case "ac":
                case "clube":
                case "club":
                case "de":
                case "do":
                case "da":
                case "dos":
                case "das":
                case "the":
                case "sport":
                case "futebol":
                case "futebolclube":
                case "society":
                case "association":
                    continue;
                default:
                    tokens.Add(tok);
                    break;
            }
        }

        s = string.Join(' ', tokens).Trim();
        // Alias-fallback: if everything got stripped (e.g. raw was "Sport Club"),
        // fall back to the diacritics-stripped, lowercased raw without token removal.
        if (s.Length == 0)
        {
            var fallback = RemoveDiacritics(raw).ToLowerInvariant();
            return fallback.Trim();
        }
        return s;
    }

    internal static string RemoveDiacritics(string s)
    {
        // 1. Manual fold for the Portuguese/Latin-1 accented letters that
        //    matter for team names. This makes the normalizer robust even on
        //    runtimes where Unicode FormD decomposition is unavailable
        //    (e.g. InvariantGlobalization builds without ICU).
        var sb = new StringBuilder(s.Length);
        foreach (var c in s)
            sb.Append(FoldChar(c));

        // 2. Best-effort FormD decomposition for anything the manual map
        //    missed (drops combining marks via NonSpacingMark category).
        var normalized = sb.ToString().Normalize(NormalizationForm.FormD);
        var result = new StringBuilder(normalized.Length);
        foreach (var c in normalized)
        {
            if (char.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
                result.Append(c);
        }
        return result.ToString();
    }

    private static char FoldChar(char c) => c switch
    {
        'à' or 'á' or 'â' or 'ã' or 'ä' or 'ā' => 'a',
        'À' or 'Á' or 'Â' or 'Ã' or 'Ä' or 'Ā' => 'A',
        'ç' or 'ć' or 'č' => 'c',
        'Ç' or 'Ć' or 'Č' => 'C',
        'è' or 'é' or 'ê' or 'ë' or 'ē' => 'e',
        'È' or 'É' or 'Ê' or 'Ë' or 'Ē' => 'E',
        'ì' or 'í' or 'î' or 'ï' or 'ī' => 'i',
        'Ì' or 'Í' or 'Î' or 'Ï' or 'Ī' => 'I',
        'ñ' or 'ń' => 'n',
        'Ñ' or 'Ń' => 'N',
        'ò' or 'ó' or 'ô' or 'õ' or 'ö' or 'ō' => 'o',
        'Ò' or 'Ó' or 'Ô' or 'Õ' or 'Ö' or 'Ō' => 'O',
        'ù' or 'ú' or 'û' or 'ü' or 'ū' => 'u',
        'Ù' or 'Ú' or 'Û' or 'Ü' or 'Ū' => 'U',
        'ý' or 'ÿ' => 'y',
        'Ý' or 'Ÿ' => 'Y',
        _ => c,
    };

    /// <summary>A human-friendly title-cased display string from a normalized key.</summary>
    public static string CanonicalDisplay(string normalized)
    {
        if (string.IsNullOrEmpty(normalized)) return "";
        var sb = new StringBuilder(normalized.Length);
        bool nextUpper = true;
        foreach (var c in normalized)
        {
            if (c == ' ')
            {
                sb.Append(' ');
                nextUpper = true;
            }
            else if (nextUpper)
            {
                sb.Append(char.ToUpper(c, CultureInfo.InvariantCulture));
                nextUpper = false;
            }
            else
            {
                sb.Append(c);
            }
        }
        return sb.ToString();
    }
}
