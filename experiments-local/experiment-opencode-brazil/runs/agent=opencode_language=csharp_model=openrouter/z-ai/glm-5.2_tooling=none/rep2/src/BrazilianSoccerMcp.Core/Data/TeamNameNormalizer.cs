// BrazilianSoccerMcp.Core - Team name normalization.
// The five match CSV files use a mix of naming conventions for the same team:
//   * "Palmeiras-SP"        (state suffix after a dash, no spaces)
//   * "Palmeiras - SP"      (state suffix after a spaced dash)
//   * "Palmeiras"           (no suffix)
//   * "Sport Club Corinthians Paulista" (full legal name)
//   * "América - MG"        (accented, spaced dash)
// Two distinct clubs can share a base name across states (e.g. "Atletico-MG"
// and "Atletico-PR"), so the canonical identity RETAINS the state code. The
// base name (suffix stripped, accents preserved) is used for display and for
// bare-name queries that should match every club with that base name.
using System.Globalization;
using System.Text;

namespace BrazilianSoccerMcp.Core.Data;

/// <summary>
/// Produces canonical team-name keys and human-friendly display names that
//  keep distinct same-base clubs (e.g. Atletico-MG vs Atletico-PR) separate.
/// </summary>
public static class TeamNameNormalizer
{
    // Brazilian state abbreviations used as suffixes in the source data.
    private static readonly HashSet<string> States = new(StringComparer.OrdinalIgnoreCase)
    {
        "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
        "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"
    };

    /// <summary>Base name with the state suffix removed but accents/case kept.</summary>
    public static string BaseName(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return "";
        var trimmed = raw.Trim();
        var (core, _) = SplitState(trimmed);
        return core.Trim();
    }

    /// <summary>Two-letter state code extracted from the suffix, or "" if none.</summary>
    public static string StateCode(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return "";
        var (_, state) = SplitState(raw.Trim());
        return state ?? "";
    }

    /// <summary>Display name: base name, plus "-UF" when a state is present.</summary>
    public static string DisplayName(string raw)
    {
        var baseName = BaseName(raw);
        var state = StateCode(raw);
        return state.Length > 0 ? $"{baseName}-{state}" : baseName;
    }

    /// <summary>Normalized base-name key (accent-stripped, lowercased).</summary>
    public static string BaseKey(string raw) =>
        RemoveDiacritics(BaseName(raw)).ToLowerInvariant().Trim();

    /// <summary>Full canonical identity key: baseKey + "|" + state(lower).</summary>
    public static string FullKey(string raw)
    {
        var baseKey = BaseKey(raw);
        var state = StateCode(raw).ToLowerInvariant();
        return $"{baseKey}|{state}";
    }

    /// <summary>Strips diacritics so "São Paulo" matches "Sao Paulo".</summary>
    public static string RemoveDiacritics(string text)
    {
        if (string.IsNullOrEmpty(text)) return text;
        var sb = new StringBuilder();
        foreach (var c in text.Normalize(NormalizationForm.FormD))
        {
            var category = char.GetUnicodeCategory(c);
            if (category != UnicodeCategory.NonSpacingMark &&
                category != UnicodeCategory.SpacingCombiningMark)
            {
                sb.Append(c);
            }
        }
        return sb.ToString().Normalize(NormalizationForm.FormC);
    }

    /// <summary>Splits a raw team name into (baseName, stateCode?) by the last dash.</summary>
    private static (string Core, string? State) SplitState(string value)
    {
        var dashIndex = value.LastIndexOf('-');
        while (dashIndex >= 0)
        {
            var tail = value.Substring(dashIndex + 1).Trim();
            // "Palmeiras-SP"        -> tail = "SP"
            // "América - MG"        -> tail = "MG"
            // "Vasco da Gama-RJ"    -> tail = "RJ"
            // "Boavista ... - RJ"   -> tail = "RJ"
            if (tail.Length <= 3 && States.Contains(tail))
                return (value.Substring(0, dashIndex), tail.ToUpperInvariant());

            var parts = tail.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 1 && States.Contains(parts[0]))
                return (value.Substring(0, dashIndex), parts[0].ToUpperInvariant());

            dashIndex = value.LastIndexOf('-', dashIndex - 1);
        }
        return (value, null);
    }
}
