using System.Globalization;
using System.Text;

namespace BrazilianSoccerCore.Data;

/// <summary>
/// Normalizes Brazilian team names across the heterogeneous datasets so that
/// "Palmeiras-SP", "Palmeiras", "Sociedade Esportiva Palmeiras" all match.
/// </summary>
public static class TeamNormalizer
{
    /// <summary>Display name: state suffix stripped, accents preserved for readability.</summary>
    public static string Normalize(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        var name = raw.Trim();

        // Strip trailing state suffix: "Palmeiras-SP", "Flamengo-RJ", "América - MG"
        // Handles both "Name-XX" and "Name - XX" forms, including parenthetical "(antigo ...)".
        name = StripStateSuffix(name);

        // Remove parenthetical annotations like "(antigo Esporte Clube Barreira)"
        name = StripParenthetical(name);

        return name.Trim();
    }

    /// <summary>Lowercased, accent-stripped key for robust equality comparison.</summary>
    public static string Key(string display)
    {
        var name = Normalize(display);
        return RemoveDiacritics(name)
            .ToLowerInvariant()
            .Trim();
    }

    /// <summary>True if the two raw/display names refer to the same team.</summary>
    public static bool SameTeam(string a, string b) =>
        Key(a).Equals(Key(b), StringComparison.Ordinal);

    private static string StripStateSuffix(string name)
    {
        // Match a 2-letter UF at the end, preceded by '-' or ' - '.
        // e.g. "Palmeiras-SP", "Flamengo-RJ", "América - MG"
        var idx = name.LastIndexOf('-');
        if (idx < 0)
            return name;

        var suffix = name[(idx + 1)..].Trim();
        // Only strip if the suffix is exactly a 2-letter state code (A-Z, accented-free)
        if (suffix.Length == 2 && IsLettersOnly(suffix))
            return name[..idx].Trim();

        return name;
    }

    private static string StripParenthetical(string name)
    {
        var sb = new StringBuilder(name.Length);
        foreach (var ch in name)
        {
            if (ch == '(')
                break;
            sb.Append(ch);
        }
        return sb.ToString().Trim('-', ' ');
    }

    private static bool IsLettersOnly(string s)
    {
        foreach (var c in s)
            if (!char.IsLetter(c))
                return false;
        return true;
    }

    private static string RemoveDiacritics(string text)
    {
        var normalized = text.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(normalized.Length);
        foreach (var ch in normalized)
        {
            var uc = CharUnicodeInfo.GetUnicodeCategory(ch);
            if (uc != UnicodeCategory.NonSpacingMark)
                sb.Append(ch);
        }
        return sb.ToString();
    }
}