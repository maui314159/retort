using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Normalizes the many team-name spellings used across the datasets:
/// state suffixes ("Palmeiras-SP", "América - MG"), country suffixes ("Nacional (URU)"),
/// accents ("Grêmio" vs "Gremio"), club prefixes ("EC Juventude") and full official names
/// ("Sport Club Corinthians Paulista"). All variants map to one canonical display name.
/// </summary>
public static partial class TeamNameNormalizer
{
    /// <summary>Canonical display name -> aliases (each alias is itself normalized before use).</summary>
    private static readonly Dictionary<string, string[]> AliasTable = new(StringComparer.Ordinal)
    {
        ["Flamengo"] = ["flamengo", "flamengo rj", "cr flamengo", "clube de regatas do flamengo"],
        ["Fluminense"] = ["fluminense", "fluminense rj", "fluminense fc", "fluminense football club"],
        ["Palmeiras"] = ["palmeiras", "palmeiras sp", "se palmeiras", "sociedade esportiva palmeiras"],
        ["Corinthians"] = ["corinthians", "corinthians sp", "sc corinthians", "sport club corinthians paulista", "sc corinthians paulista", "corinthians paulista"],
        ["São Paulo"] = ["sao paulo", "sao paulo sp", "sao paulo fc", "sao paulo futebol clube"],
        ["Santos"] = ["santos", "santos sp", "santos fc", "santos futebol clube", "santos futebol clube sp"],
        ["Vasco da Gama"] = ["vasco", "vasco rj", "vasco da gama", "cr vasco da gama", "club de regatas vasco da gama"],
        ["Botafogo"] = ["botafogo", "botafogo rj", "botafogo fr", "botafogo de futebol e regatas"],
        ["Grêmio"] = ["gremio", "gremio rs", "gremio fbpa", "gremio foot-ball porto alegrense"],
        ["Internacional"] = ["internacional", "internacional rs", "sc internacional", "sport club internacional"],
        ["Cruzeiro"] = ["cruzeiro", "cruzeiro mg", "cruzeiro ec", "cruzeiro esporte clube"],
        ["Atlético Mineiro"] = ["atletico", "atletico mg", "atletico mineiro", "clube atletico mineiro", "cam"],
        ["Athletico Paranaense"] = ["atletico pr", "athletico pr", "atletico paranaense", "athletico paranaense", "club athletico paranaense"],
        ["Bahia"] = ["bahia", "bahia ba", "ec bahia", "esporte clube bahia"],
        ["Sport Recife"] = ["sport", "sport pe", "sport recife", "sport club do recife"],
        ["Coritiba"] = ["coritiba", "coritiba pr", "coritiba fc", "coritiba foot ball club"],
        ["Goiás"] = ["goias", "goias go", "goias ec", "goias esporte clube"],
        ["Ceará"] = ["ceara", "ceara ce", "ceara sc", "ceara sporting club"],
        ["Fortaleza"] = ["fortaleza", "fortaleza ce", "fortaleza ec", "fortaleza esporte clube"],
        ["Avaí"] = ["avai", "avai sc", "avai fc", "avai futebol clube"],
        ["Chapecoense"] = ["chapecoense", "chapecoense sc", "chapecoense af", "assoc chapecoense de futebol", "associacao chapecoense de futebol"],
        ["Figueirense"] = ["figueirense", "figueirense sc", "figueirense fc"],
        ["Juventude"] = ["juventude", "juventude rs", "ec juventude", "esporte clube juventude"],
        ["Náutico"] = ["nautico", "nautico pe", "clube nautico capibaribe"],
        ["Ponte Preta"] = ["ponte preta", "ponte preta sp", "aa ponte preta", "associacao atletica ponte preta"],
        ["Portuguesa"] = ["portuguesa", "portuguesa sp", "associacao portuguesa de desportos"],
        ["Paraná"] = ["parana", "parana pr", "parana clube"],
        ["Santa Cruz"] = ["santa cruz", "santa cruz pe", "santa cruz fc", "santa cruz futebol clube"],
        ["Vitória"] = ["vitoria", "vitoria ba", "ec vitoria", "esporte clube vitoria"],
        ["Criciúma"] = ["criciuma", "criciuma sc", "criciuma ec", "criciuma esporte clube"],
        ["CSA"] = ["csa", "csa al", "centro sportivo alagoano"],
        ["Cuiabá"] = ["cuiaba", "cuiaba mt", "cuiaba ec", "cuiaba esporte clube"],
        ["Red Bull Bragantino"] = ["bragantino", "bragantino sp", "red bull bragantino", "rb bragantino", "ca bragantino", "clube atletico bragantino"],
        ["Joinville"] = ["joinville", "joinville sc", "joinville ec", "joinville esporte clube"],
        ["Atlético Goianiense"] = ["atletico go", "atletico goianiense", "ac goianiense", "atletico clube goianiense"],
        ["América Mineiro"] = ["america", "america mg", "america mineiro", "america fc", "america futebol clube", "america futebol clube mg"],
        ["Guarani"] = ["guarani", "guarani sp", "guarani fc", "guarani futebol clube"],
        ["Boavista"] = ["boavista", "boavista rj", "boavista sport club", "boavista sc"],
        ["São Caetano"] = ["sao caetano", "sao caetano sp", "ad sao caetano", "associacao desportiva sao caetano"],
        ["Remo"] = ["remo", "remo pa", "clube do remo"],
        ["Paysandu"] = ["paysandu", "paysandu pa", "paysandu sport club"],
        ["ABC"] = ["abc", "abc rn", "abc futebol clube"],
        ["América de Natal"] = ["america rn", "america de natal", "america fc rn", "america futebol clube rn"],
    };

    private static readonly Dictionary<string, string> AliasToCanonical = BuildAliasLookup();

    private static Dictionary<string, string> BuildAliasLookup()
    {
        var map = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var (canonical, aliases) in AliasTable)
        {
            map[NormalizeKey(canonical)] = canonical;
            foreach (var alias in aliases)
                map[NormalizeKey(alias)] = canonical;
        }
        return map;
    }

    /// <summary>
    /// Accent-free lowercase key with parentheticals removed and club prefixes stripped.
    /// State/country suffixes are KEPT ("Atletico-MG" -> "atletico mg") because bare stems
    /// such as "atletico" are ambiguous (Mineiro vs Paranaense vs Goianiense).
    /// </summary>
    public static string NormalizeKey(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return string.Empty;

        // Capture the trailing state/country suffix BEFORE stripping decorations,
        // then re-attach it as a plain word ("Atletico-MG" -> "atletico mg").
        var suffixMatch = DashSuffixToWordRegex().Match(raw.Trim());
        var suffix = suffixMatch.Success ? suffixMatch.Groups[1].Value : null;

        var cleaned = StripDecorations(raw);
        cleaned = RemoveAccents(cleaned).ToLowerInvariant();
        cleaned = cleaned.Replace(".", "", StringComparison.Ordinal); // "A.B.C." -> "abc"
        cleaned = StripClubPrefix(cleaned);
        cleaned = TrailingClubSuffixRegex().Replace(cleaned, ""); // "4 de Julho EC" -> "4 de julho"
        cleaned = WhitespaceRegex().Replace(cleaned, " ").Trim();

        if (suffix is not null)
        {
            var suffixKey = RemoveAccents(suffix).ToLowerInvariant();
            // Avoid doubling when the stem already ends with the suffix word.
            if (!cleaned.EndsWith(suffixKey, StringComparison.Ordinal))
                cleaned = cleaned.Length == 0 ? suffixKey : $"{cleaned} {suffixKey}";
        }
        return cleaned;
    }

    /// <summary>Canonical display name for a raw dataset name (falls back to the cleaned raw name).</summary>
    public static string CanonicalName(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return string.Empty;

        // Pass 1: full key including state suffix ("atletico mg" -> Atlético Mineiro).
        var key = NormalizeKey(raw);
        if (AliasToCanonical.TryGetValue(key, out var canonical))
            return canonical;

        // Pass 2: stem without the trailing state/country word ("palmeiras sp" -> "palmeiras").
        var stem = KeyStemSuffixRegex().Replace(key, "").Trim();
        if (stem.Length > 0 && stem != key && AliasToCanonical.TryGetValue(stem, out canonical))
            return canonical;

        var cleaned = StripClubPrefix(StripDecorations(raw)).Trim();
        cleaned = TrailingClubSuffixRegex().Replace(cleaned, "").Trim();
        return WhitespaceRegex().Replace(cleaned, " ");
    }

    /// <summary>True when both raw names refer to the same club.</summary>
    public static bool SameTeam(string? a, string? b)
    {
        if (string.IsNullOrWhiteSpace(a) || string.IsNullOrWhiteSpace(b)) return false;
        var ca = CanonicalName(a);
        var cb = CanonicalName(b);
        return ca.Length > 0 && string.Equals(ca, cb, StringComparison.Ordinal);
    }

    // Removes trailing "(...)" groups and "-XX" / " - XX" state/country suffixes entirely,
    // alternating until stable (handles "Name (notes) - RJ").
    private static string StripDecorations(string raw)
    {
        var s = raw.Trim();
        string previous;
        do
        {
            previous = s;
            s = TrailingStateSuffixRegex().Replace(s, "").Trim();
            s = TrailingParentheticalRegex().Replace(s, "").Trim();
        } while (!string.Equals(s, previous, StringComparison.Ordinal));
        return s;
    }

    private static string StripClubPrefix(string name) =>
        ClubPrefixRegex().Replace(name, "");

    private static string RemoveAccents(string text)
    {
        var normalized = text.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(normalized.Length);
        foreach (var c in normalized)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        }
        return sb.ToString().Normalize(NormalizationForm.FormC);
    }

    [GeneratedRegex(@"\s*\([^()]*\)\s*$")]
    private static partial Regex TrailingParentheticalRegex();

    [GeneratedRegex(@"\s*-\s*([A-Za-z]{2,3})\s*$")]
    private static partial Regex DashSuffixToWordRegex();

    [GeneratedRegex(@"\s*-\s*[A-Za-z]{2,3}\s*$")]
    private static partial Regex TrailingStateSuffixRegex();

    [GeneratedRegex(@"\s+[a-z]{2,3}$")]
    private static partial Regex KeyStemSuffixRegex();

    [GeneratedRegex(@"^(ec|fc|sc|ac|se|ca|aa|ad|cd|cf|as)\s+", RegexOptions.IgnoreCase)]
    private static partial Regex ClubPrefixRegex();

    [GeneratedRegex(@"\s+(ec|fc|sc|cf)$", RegexOptions.IgnoreCase)]
    private static partial Regex TrailingClubSuffixRegex();

    [GeneratedRegex(@"\s+")]
    private static partial Regex WhitespaceRegex();
}
