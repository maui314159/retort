// =============================================================================
// File:    NameNormalizer.cs
// Project: BrazilianSoccer.Core
// Purpose: Normalize Brazilian club names so the same team matches across the
//          six datasets despite formatting differences. Produces a fold "key"
//          (lower-case, accent-free, state-qualified, alias-collapsed) used for
//          matching, and a clean display name (suffix stripped, accents kept).
// Context: TASK.md "Data Quality Notes" requires handling: state suffixes
//          ("Palmeiras-SP", "Atletico-MG"), region adjectives that encode the
//          state ("Atletico Mineiro" = MG, "Athletico Paranaense" = PR),
//          embedded state tokens ("Botafogo RJ", "America MG"), full legal
//          names ("Sport Club Corinthians Paulista"), accents (São Paulo,
//          Grêmio) and country tags in Libertadores rows ("Nacional (URU)").
//          Two correctness hazards drove the design:
//            1. Distinct clubs share a base name and MUST stay separate by
//               state — Atlético-MG vs Athletico-PR vs Atlético-GO, Botafogo-RJ
//               vs Botafogo-SP, América-MG vs América-RN. These bases are
//               "ambiguous" and their key carries the UF (e.g. "atletico mg").
//            2. The same club is spelled differently across sources and MUST
//               collapse — "Vasco" / "Vasco da Gama" / "Vasco da Gama-RJ",
//               "Bragantino" / "Red Bull Bragantino", "Bahia" / "EC Bahia".
//               An alias table folds these onto one canonical base.
//          Without this, league standings and head-to-head counts inflate
//          (overlapping Série A sources would not deduplicate). See DataLoader
//          .Deduplicate, which keys fixtures on the resulting team keys.
// =============================================================================

using System.Globalization;
using System.Text;

namespace BrazilianSoccer.Core;

public static class NameNormalizer
{
    private static readonly HashSet<string> BrazilStates = new(StringComparer.Ordinal)
    {
        "ac","al","ap","am","ba","ce","df","es","go","ma","mt","ms","mg","pa",
        "pb","pr","pe","pi","rj","rn","rs","ro","rr","sc","sp","se","to",
    };

    // Region adjectives that uniquely encode a state.
    private static readonly Dictionary<string, string> AdjectiveToUf = new(StringComparer.Ordinal)
    {
        ["mineiro"] = "mg", ["paranaense"] = "pr", ["goianiense"] = "go",
        ["paulista"] = "sp", ["carioca"] = "rj", ["gaucho"] = "rs",
    };

    // Bases shared by multiple real clubs: the key must carry the state.
    private static readonly HashSet<string> Ambiguous = new(StringComparer.Ordinal)
    {
        "atletico", "botafogo", "america", "santa cruz", "guarani",
    };

    // Standalone club-type / corporate / connector tokens removed from any
    // position (never reducing a name to empty — see Key).
    private static readonly HashSet<string> Noise = new(StringComparer.Ordinal)
    {
        "fc", "ec", "ac", "aa", "ad", "sc", "se", "cr", "cd",
        "esporte", "esportivo", "esportiva", "clube", "club", "futebol",
        "foot", "ball", "regatas", "associacao",
        "sociedade", "recreativo", "de", "do", "da", "dos", "das",
    };
    // Verbose / variant folded names → canonical base (state appended later if
    // the base is ambiguous and a UF was detected).
    private static readonly Dictionary<string, string> Aliases = new(StringComparer.Ordinal)
    {
        ["sport club corinthians paulista"] = "corinthians",
        ["sociedade esportiva palmeiras"] = "palmeiras",
        ["sao paulo fc"] = "sao paulo",
        ["sao paulo futebol clube"] = "sao paulo",
        ["clube de regatas do flamengo"] = "flamengo",
        ["fluminense football club"] = "fluminense",
        ["botafogo de futebol e regatas"] = "botafogo",
        ["gremio foot ball porto alegrense"] = "gremio",
        ["sport club internacional"] = "internacional",
        ["santos futebol clube"] = "santos",
        ["cruzeiro esporte clube"] = "cruzeiro",
        ["esporte clube bahia"] = "bahia",
        ["fortaleza esporte clube"] = "fortaleza",
        ["vasco da gama"] = "vasco",
        ["red bull bragantino"] = "bragantino",
        ["sport recife"] = "sport",
        ["nautico capibaribe"] = "nautico",
        ["athletico"] = "athletico",          // sole "Athletico" => Paranaense (pr)
        ["athletico paranaense"] = "athletico",
        ["atletico paranaense"] = "athletico",
    };

    // After alias folding, these bases collapse onto another ambiguous base so
    // they share the state-qualified key (Athletico Paranaense == Atlético-PR).
    private static readonly Dictionary<string, (string Base, string Uf)> CanonOverride =
        new(StringComparer.Ordinal)
        {
            ["athletico"] = ("atletico", "pr"),
        };

    /// <summary>
    /// Builds a match key: accent-free, lower-case, club-noise stripped, alias
    /// folded, and state-qualified for ambiguous bases. Foreign clubs keep a
    /// country tag so they never merge with a same-named Brazilian club.
    /// </summary>
    public static string Key(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return "";

        var (core, uf, country) = SplitLocation(raw);
        var folded = Fold(core);

        // Alias the full folded name first, so multi-word legal names whose
        // tail looks like a region adjective ("...Paulista") are not mangled
        // by the adjective/state stripping below.
        if (Aliases.TryGetValue(folded, out var directAlias))
            return Qualify(directAlias, uf, country);

        // Pull a trailing region adjective ("... mineiro") into the UF.
        var tokens = folded.Split(' ', StringSplitOptions.RemoveEmptyEntries).ToList();
        if (tokens.Count > 1 && AdjectiveToUf.TryGetValue(tokens[^1], out var adjUf))
        {
            uf ??= adjUf;
            tokens.RemoveAt(tokens.Count - 1);
        }
        // Pull a trailing embedded state token ("botafogo rj", "america mg").
        if (uf is null && tokens.Count > 1 && BrazilStates.Contains(tokens[^1]))
        {
            uf = tokens[^1];
            tokens.RemoveAt(tokens.Count - 1);
        }

        var collapsed = string.Join(' ', tokens);

        string baseKey;
        if (Aliases.TryGetValue(collapsed, out var aliased))
            baseKey = aliased;
        else
        {
            // Strip standalone noise tokens, but never reduce to empty.
            var kept = tokens.Where(t => !Noise.Contains(t)).ToList();
            baseKey = kept.Count > 0 ? string.Join(' ', kept) : collapsed;
            if (Aliases.TryGetValue(baseKey, out var aliased2)) baseKey = aliased2;
        }

        return Qualify(baseKey, uf, country);
    }

    // Resolves a canonical base override (e.g. "athletico" => "atletico"/PR),
    // then appends a state tag to ambiguous bases and a country tag to foreign
    // clubs so distinct same-named clubs never collide and variants merge.
    private static string Qualify(string baseKey, string? uf, string? country)
    {
        if (CanonOverride.TryGetValue(baseKey, out var ov))
        {
            baseKey = ov.Base;
            uf ??= ov.Uf;
        }
        if (Ambiguous.Contains(baseKey) && uf is not null) return $"{baseKey} {uf}";
        if (country is not null) return $"{baseKey} {country}";
        return baseKey;
    }

    /// <summary>Human-readable name: trailing state/country tag removed, accents kept.</summary>
    public static string Display(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return "";
        var (core, _, _) = SplitLocation(raw);
        return core.Trim();
    }

    // Splits a raw name into (core, brazilianStateUf, foreignCountryCode).
    private static (string Core, string? Uf, string? Country) SplitLocation(string raw)
    {
        var s = raw.Trim();
        string? uf = null, country = null;

        // Country/state tag in parentheses: "Nacional (URU)".
        int paren = s.LastIndexOf('(');
        if (paren > 0 && s.EndsWith(')'))
        {
            var inside = s[(paren + 1)..^1].Trim();
            if (inside.Length is >= 2 and <= 4 && inside.All(char.IsLetter))
            {
                var low = inside.ToLowerInvariant();
                if (BrazilStates.Contains(low)) uf = low; else country = low;
                s = s[..paren].Trim();
            }
        }

        // Trailing "-UF" or " - UF" / "-EQU" location token.
        int dash = s.LastIndexOf('-');
        if (dash > 0)
        {
            var tail = s[(dash + 1)..].Trim();
            if (tail.Length is >= 2 and <= 4 && tail.All(char.IsLetter))
            {
                var low = tail.ToLowerInvariant();
                if (BrazilStates.Contains(low)) { uf ??= low; s = s[..dash].Trim(); }
                else if (tail.Length is 3 or 4 && tail.All(char.IsUpper))
                {
                    country ??= low; s = s[..dash].Trim();
                }
            }
        }

        return (s, uf, country);
    }

    // Lowercase, strip diacritics, collapse punctuation/whitespace to single spaces.
    private static string Fold(string s)
    {
        var decomposed = s.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(decomposed.Length);
        bool lastSpace = false;
        foreach (var ch in decomposed)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(ch) == UnicodeCategory.NonSpacingMark) continue;
            if (char.IsLetterOrDigit(ch)) { sb.Append(char.ToLowerInvariant(ch)); lastSpace = false; }
            else if (!lastSpace && sb.Length > 0) { sb.Append(' '); lastSpace = true; }
        }
        return sb.ToString().Trim();
    }
}
