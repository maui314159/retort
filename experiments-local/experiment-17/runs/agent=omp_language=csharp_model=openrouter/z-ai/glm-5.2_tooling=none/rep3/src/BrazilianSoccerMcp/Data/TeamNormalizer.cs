// Brazilian Soccer MCP Server - Team name normalisation
// Context: The six match/player CSV files use wildly inconsistent team naming:
// state-suffixed ("Palmeiras-SP", "América - MG"), parenthetical-annotated
// ("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"), full names
// ("Atlético Mineiro"), and ASCII-stripped ("Sao Paulo"). A naive "strip the
// trailing state code" normaliser COLLIDES short-named clubs that share a base
// name (Atletico-MG vs Atletico-PR vs Atletico-GO all collapse to "atletico";
// América-MG vs América-RN collapse to "america"), which corrupts standings
// and head-to-head aggregates.
//
// Strategy: keep the state suffix as part of the key (so suffixes
// differentiate), but layer a curated alias map on top that maps the common
// variant forms of the ~30 major Brazilian clubs to a single canonical display
// name. Variants cover: suffixed short form, full Portuguese name, and the
// FIFA-database form. Anything outside the map falls back to the normalised
// (suffix-preserving) form, which stays collision-free because the suffix is
// retained.

using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Data;

/// <summary>Normalises Brazilian football team names across the bundled datasets.</summary>
public static class TeamNormalizer
{
    private static readonly Regex Parenthetical = new(@"\s*\([^)]*\)", RegexOptions.Compiled);
    private static readonly Regex WhitespaceRun = new(@"\s+", RegexOptions.Compiled);

    // Canonical display name -> every normalised variant that should map to it.
    private static readonly Dictionary<string, string> AliasMap = BuildAliasMap();

    /// <summary>Returns the canonical key for a team name (used for matching/grouping).</summary>
    public static string Normalize(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        var norm = NormalizeCore(raw);
        if (AliasMap.TryGetValue(norm, out var canonical))
            return canonical;
        return norm;
    }

    /// <summary>Returns a human-friendly display name (canonical for known clubs,
    /// otherwise the raw string with parenthetical annotations removed).</summary>
    public static string DisplayName(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        var norm = NormalizeCore(raw);
        if (AliasMap.TryGetValue(norm, out var canonical))
            return canonical;
        return Parenthetical.Replace(raw, string.Empty).Trim();
    }

    private static string NormalizeCore(string raw)
    {
        // Drop parenthetical annotations, e.g. "Boavista SC (antigo EC Barreira) - RJ".
        var s = Parenthetical.Replace(raw, string.Empty);
        // Unify dash spacing: " - " / " – " -> "-" so "América - MG" and "América-MG" agree.
        s = s.Replace(" - ", "-").Replace(" – ", "-").Replace(" — ", "-");
        // Strip diacritics (São -> Sao, Grêmio -> Gremio, Ceará -> Ceara).
        s = RemoveDiacritics(s);
        s = s.ToLowerInvariant().Trim();
        // Collapse internal whitespace runs but keep the dash-bearing tokens intact.
        s = WhitespaceRun.Replace(s, " ");
        return s;
    }

    private static string RemoveDiacritics(string text)
    {
        var normalized = text.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(normalized.Length);
        foreach (var ch in normalized)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(ch) != UnicodeCategory.NonSpacingMark)
                sb.Append(ch);
        }
        return sb.ToString();
    }

    private static Dictionary<string, string> BuildAliasMap()
    {
        // (canonical display name, variant normalised forms)
        var entries = new[]
        {
            ("Palmeiras", new[] { "palmeiras", "palmeiras-sp", "s.e. palmeiras", "sociedade esportiva palmeiras" }),
            ("Flamengo", new[] { "flamengo", "flamengo-rj", "clube de regatas do flamengo" }),
            ("Corinthians", new[] { "corinthians", "corinthians-sp", "sport club corinthians paulista", "s.c. corinthians paulista" }),
            ("São Paulo", new[] { "sao paulo", "sao paulo-sp", "sao paulo fc", "sao paulo futebol clube" }),
            ("Santos", new[] { "santos", "santos-sp", "santos fc" }),
            ("Grêmio", new[] { "gremio", "gremio-rs", "gremio foot-ball portoalegrense" }),
            ("Internacional", new[] { "internacional", "internacional-rs", "sport club internacional", "sc internacional" }),
            ("Fluminense", new[] { "fluminense", "fluminense-rj", "fluminense football club" }),
            ("Atlético Mineiro", new[] { "atletico-mg", "atletico mg", "atletico mineiro", "clube atletico mineiro", "c.a. mineiro" }),
            ("Cruzeiro", new[] { "cruzeiro", "cruzeiro-mg", "cruzeiro esporte clube" }),
            ("Botafogo", new[] { "botafogo", "botafogo-rj", "botafogo fr", "botafogo de futebol e regatas" }),
            ("Athletico Paranaense", new[] { "athletico-pr", "atletico-pr", "athletico paranaense", "atletico paranaense", "club athletico paranaense" }),
            ("Bahia", new[] { "bahia", "bahia-ba", "ec bahia", "esporte clube bahia" }),
            ("Fortaleza", new[] { "fortaleza", "fortaleza-ce", "fortaleza ec", "fortaleza esporte clube" }),
            ("Ceará", new[] { "ceara", "ceara-ce", "ceara sporting club", "ceara sc", "ceara ec" }),
            ("Vasco da Gama", new[] { "vasco", "vasco-rj", "vasco da gama", "cr vasco da gama", "club de regatas vasco da gama" }),
            ("Sport", new[] { "sport", "sport-pe", "sport club do recife", "sport recife", "sport club recife" }),
            ("Chapecoense", new[] { "chapecoense", "chapecoense-sc", "associedade chapecoense de futebol" }),
            ("Goiás", new[] { "goias", "goias-go", "goias ec", "goias esporte clube" }),
            ("Avaí", new[] { "avai", "avai-sc", "avai futebol clube" }),
            ("Cuiabá", new[] { "cuiaba", "cuiaba-mt", "cuiaba ec", "cuiaba esporte clube" }),
            ("Juventude", new[] { "juventude", "juventude-rs", "ec juventude", "esporte clube juventude" }),
            ("Red Bull Bragantino", new[] { "bragantino", "bragantino-sp", "rb bragantino", "red bull bragantino" }),
            ("Atlético Goianiense", new[] { "atletico-go", "atletico goianiense", "atletico-goianiense" }),
            ("Coritiba", new[] { "coritiba", "coritiba-pr", "coritiba foot ball club" }),
            ("Vitória", new[] { "vitoria", "vitoria-ba", "ec vitoria", "esporte clube vitoria" }),
            ("América Mineiro", new[] { "america-mg", "america mg", "america fc (minas gerais)", "america futebol club (minas gerais)" }),
            ("Ponte Preta", new[] { "ponte preta", "ponte preta-sp", "aa ponte preta" }),
            ("Náutico", new[] { "nautico", "nautico-pe", "nautico capibaribe" }),
            ("Figueirense", new[] { "figueirense", "figueirense-sc" }),
            ("Vitória da Conquista", new[] { "vitoria da conquista" }),
            ("CRB", new[] { "crb", "crb-al", "clube de regatas brasil" }),
            ("CSA", new[] { "csa", "csa-al", "centro sportivo alagoano" }),
            ("Operário-PR", new[] { "operario-pr", "operario ferroviario", "operario pr" }),
            ("Brusque", new[] { "brusque", "brusque-sc", "brusque fc" }),
        };

        var map = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var (canonical, variants) in entries)
        {
            foreach (var variant in variants)
            {
                // Last-writer-wins is fine: variants are unique within a canonical group.
                map[variant] = canonical;
            }
        }
        return map;
    }
}
