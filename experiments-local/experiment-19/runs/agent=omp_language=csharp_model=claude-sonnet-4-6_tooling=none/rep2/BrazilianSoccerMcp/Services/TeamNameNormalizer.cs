using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Services;

public static class TeamNameNormalizer
{
    // Matches " - XX" or "-XX" at end where XX is a 2-letter state code
    private static readonly Regex StateSuffixPattern =
        new(@"\s*-\s*[A-Z]{2}\s*$", RegexOptions.Compiled);

    public static string Normalize(string name)
    {
        if (string.IsNullOrWhiteSpace(name)) return name;
        return StateSuffixPattern.Replace(name.Trim(), "").Trim();
    }

    /// <summary>
    /// Returns true if <paramref name="candidate"/> contains <paramref name="query"/>
    /// using case-insensitive, accent-tolerant comparison.
    /// </summary>
    public static bool Matches(string candidate, string query)
    {
        var norm = Normalize(candidate);
        return norm.Contains(query, StringComparison.OrdinalIgnoreCase)
            || StripAccents(norm).Contains(StripAccents(query), StringComparison.OrdinalIgnoreCase);
    }

    private static string StripAccents(string s)
    {
        var normalized = s.Normalize(System.Text.NormalizationForm.FormD);
        var sb = new System.Text.StringBuilder(normalized.Length);
        foreach (var c in normalized)
        {
            var cat = System.Globalization.CharUnicodeInfo.GetUnicodeCategory(c);
            if (cat != System.Globalization.UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        }
        return sb.ToString().Normalize(System.Text.NormalizationForm.FormC);
    }
}
