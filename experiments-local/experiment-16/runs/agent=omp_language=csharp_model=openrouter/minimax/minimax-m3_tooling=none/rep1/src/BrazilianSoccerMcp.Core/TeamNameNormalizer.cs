// =============================================================================
// Brazilian Soccer MCP Server
// File: TeamNameNormalizer.cs
// Purpose: Convert heterogeneous team-name strings into a stable canonical
//          key so that "Flamengo", "Flamengo-RJ", "Flamengo - RJ" all match.
// Context: Every CSV uses its own naming convention. The query engine
//          normalizes both stored data and incoming queries through this
//          class; never compare raw team strings directly.
// =============================================================================

using System.Globalization;
using System.Text;

namespace BrazilianSoccerMcp.Core;

/// <summary>
/// Normalizes team names so cross-dataset queries work reliably.
/// Two-stage pipeline:
///   1. <see cref="DisplayName"/> produces a human-readable form
///      ("Flamengo", "São Paulo") for output.
///   2. <see cref="Key"/> produces a stable lookup key
///      ("flamengo", "saopaulo") for matching.
///
/// Use <see cref="Key"/> for comparisons and <see cref="DisplayName"/>
/// when rendering results to the LLM.
/// </summary>
public static class TeamNameNormalizer
{
    // Common alias table: maps a normalized key to its canonical display
    // string. The lookup key is the lowercased / diacritic-stripped form.
    // Entries here let us collapse spelling variations like
    // "Sao Paulo" / "São Paulo" / "São Paulo - SP" into one canonical name.
    private static readonly Dictionary<string, string> Aliases = new(StringComparer.Ordinal)
    {
        // State-suffixed forms: Brasileirão dataset uses "Flamengo-RJ",
        // Libertadores uses "Flamengo", Copa do Brasil uses "Flamengo - RJ".
        // Canonical form = "<Club> - <State>".
        { "palmeiras",           "Palmeiras - SP" },
        { "palmeirassp",         "Palmeiras - SP" },
        { "saopaulo",            "São Paulo - SP" },
        { "saopaulosp",          "São Paulo - SP" },
        { "corinthians",         "Corinthians - SP" },
        { "corinthianssp",       "Corinthians - SP" },
        { "santos",              "Santos - SP" },
        { "santossp",            "Santos - SP" },
        { "flamengo",            "Flamengo - RJ" },
        { "flamengorj",          "Flamengo - RJ" },
        { "fluminense",          "Fluminense - RJ" },
        { "fluminenserj",        "Fluminense - RJ" },
        { "vascodagama",         "Vasco da Gama - RJ" },
        { "vascodagamarj",       "Vasco da Gama - RJ" },
        { "botafogo",            "Botafogo - RJ" },
        { "botafogorj",          "Botafogo - RJ" },
        { "vasco",               "Vasco da Gama - RJ" },
        { "internacional",       "Internacional - RS" },
        { "internacionalrs",     "Internacional - RS" },
        { "gremio",              "Grêmio - RS" },
        { "gremiors",            "Grêmio - RS" },
        { "coritiba",            "Coritiba - PR" },
        { "coritobapr",          "Coritiba - PR" },
        { "athleticopr",         "Athletico-PR" },
        { "atleticopr",          "Athletico-PR" },
        { "atleticomg",          "Atlético-MG" },
        { "atleticogo",          "Atlético-GO" },
        { "cruzeiro",            "Cruzeiro - MG" },
        { "cruzeiromg",          "Cruzeiro - MG" },
        { "bahia",               "Bahia - BA" },
        { "bahiaba",             "Bahia - BA" },
        { "sport",               "Sport - PE" },
        { "sportpe",             "Sport - PE" },
        { "nautico",             "Náutico - PE" },
        { "nauticope",           "Náutico - PE" },
        { "santacruz",           "Santa Cruz - PE" },
        { "santacruzpe",         "Santa Cruz - PE" },
        { "pontepreta",          "Ponte Preta - SP" },
        { "pontepretasp",        "Ponte Preta - SP" },
        { "portuguesa",          "Portuguesa - SP" },
        { "portuguesasdesportos","Portuguesa - SP" },
        { "guarani",             "Guarani - SP" },
        { "guaranisp",           "Guarani - SP" },
        { "figueirense",         "Figueirense - SC" },
        { "figueirensesc",       "Figueirense - SC" },
        { "avai",                "Avaí - SC" },
        { "avaisc",              "Avaí - SC" },
        { "chapecoense",         "Chapecoense - SC" },
        { "chapecoensesc",       "Chapecoense - SC" },
        { "criciuma",            "Criciúma - SC" },
        { "joinville",           "Joinville - SC" },
        { "goias",               "Goiás - GO" },
        { "goiasgo",             "Goiás - GO" },
        { "vitoria",             "Vitória - BA" },
        { "vitoriaba",           "Vitória - BA" },
        { "fortaleza",           "Fortaleza - CE" },
        { "fortalezace",         "Fortaleza - CE" },
        { "ceara",               "Ceará - CE" },
        { "cearace",             "Ceará - CE" },
        { "juventude",           "Juventude - RS" },
        { "juventuders",         "Juventude - RS" },
        { "bragantino",          "Red Bull Bragantino - SP" },
        { "redbullbragantino",   "Red Bull Bragantino - SP" },
        { "redullbragantinosp",  "Red Bull Bragantino - SP" },
        { "america",             "América - MG" },
        { "americamg",           "América - MG" },
        { "csa",                 "CSA - AL" },
        { "csaal",               "CSA - AL" },
        { "parana",              "Paraná - PR" },
        { "paranapr",            "Paraná - PR" },
        { "ipatinga",            "Ipatinga - MG" },
        { "barueri",             "Barueri - SP" },
        { "saocaetano",          "São Caetano - SP" },
        { "saojosers",           "São José - RS" },
    };

    // Brazilian state codes -- used to strip the suffix from a string like
    // "Flamengo-RJ" or "Flamengo - RJ" before lookup.
    private static readonly HashSet<string> StateCodes = new(StringComparer.OrdinalIgnoreCase)
    {
        "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
        "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"
    };

    /// <summary>
    /// Strips diacritics, lowercases, and removes spaces/punctuation. Used
    /// as the dictionary key for alias lookup.
    /// </summary>
    public static string Key(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        // Step 1: decompose accents, then drop combining marks.
        var decomposed = raw.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(decomposed.Length);
        foreach (var ch in decomposed)
        {
            var cat = CharUnicodeInfo.GetUnicodeCategory(ch);
            if (cat == UnicodeCategory.NonSpacingMark)
                continue;
            sb.Append(ch);
        }
        var stripped = sb.ToString().Normalize(NormalizationForm.FormC);

        // Step 2: drop the trailing state code if present
        //   "Flamengo-RJ"        -> "Flamengo"
        //   "Flamengo - RJ"      -> "Flamengo"
        //   "Flamengo (RJ)"      -> "Flamengo"
        //   "Palmeiras-SP"       -> "Palmeiras"
        stripped = StripTrailingStateCode(stripped);

        // Step 3: lowercase, drop spaces and punctuation
        var lower = stripped.ToLowerInvariant();
        var clean = new StringBuilder(lower.Length);
        foreach (var ch in lower)
        {
            if (char.IsLetterOrDigit(ch))
                clean.Append(ch);
        }
        return clean.ToString();
    }

    /// <summary>
    /// Returns the canonical display name for the team. Falls back to the
    /// stripped original if no alias matches.
    /// </summary>
    public static string DisplayName(string? raw)
    {
        var key = Key(raw);
        if (key.Length == 0)
            return raw ?? string.Empty;
        return Aliases.TryGetValue(key, out var canonical) ? canonical : raw!.Trim();
    }

    /// <summary>
    /// True if the two raw team strings resolve to the same canonical team.
    /// </summary>
    public static bool AreSame(string? a, string? b) =>
        Key(a).Equals(Key(b), StringComparison.Ordinal) && Key(a).Length > 0;

    /// <summary>
    /// Drop a 2-letter state suffix in any of these shapes:
    ///   "Flamengo-RJ" / "Flamengo - RJ" / "Flamengo (RJ)" / "Flamengo (RJ"
    /// </summary>
    private static string StripTrailingStateCode(string s)
    {
        // First try the dash form: "X-RJ", "X - RJ", "X(RJ)"
        var lastDash = s.LastIndexOf('-');
        if (lastDash > 0)
        {
            var tail = s[(lastDash + 1)..].Trim(' ', '(', ')');
            if (tail.Length == 2 && StateCodes.Contains(tail))
                return s[..lastDash].TrimEnd(' ', '(', ')');
        }
        // Parens form: "X (RJ)" or "X (RJ"
        var parenOpen = s.LastIndexOf('(');
        if (parenOpen > 0 && s.EndsWith(')'))
        {
            var inside = s[(parenOpen + 1)..^1].Trim();
            if (inside.Length == 2 && StateCodes.Contains(inside))
                return s[..parenOpen].TrimEnd(' ', '(', ')');
        }
        // Open-paren form: "X (RJ"  (missing closing paren)
        if (parenOpen > 0)
        {
            var inside = s[(parenOpen + 1)..].Trim();
            if (inside.Length == 2 && StateCodes.Contains(inside))
                return s[..parenOpen].TrimEnd(' ', '(', ')');
        }
        return s;
    }
}
