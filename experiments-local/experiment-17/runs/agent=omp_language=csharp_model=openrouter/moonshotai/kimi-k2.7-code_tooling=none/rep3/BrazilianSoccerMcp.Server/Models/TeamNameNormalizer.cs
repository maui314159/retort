using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Server.Models;

public static partial class TeamNameNormalizer
{
    public static string Normalize(string name)
    {
        if (string.IsNullOrWhiteSpace(name))
            return string.Empty;

        var normalized = name.Trim();

        // Remove common suffixes like " - SP", " - RJ", " (URU)", etc.
        normalized = SuffixRegex().Replace(normalized, string.Empty);

        // Remove diacritics
        normalized = RemoveDiacritics(normalized);

        // Normalize common abbreviations and punctuation
        normalized = normalized
            .Replace("Athletico", "Atletico", StringComparison.OrdinalIgnoreCase)
            .Replace("Athletico-PR", "Atletico-PR", StringComparison.OrdinalIgnoreCase)
            .Replace(".", string.Empty, StringComparison.OrdinalIgnoreCase)
            .Replace("FC", string.Empty, StringComparison.OrdinalIgnoreCase)
            .Replace("Esporte Clube", string.Empty, StringComparison.OrdinalIgnoreCase)
            .Replace("Sport Club", string.Empty, StringComparison.OrdinalIgnoreCase)
            .Replace("Clube de Regatas", string.Empty, StringComparison.OrdinalIgnoreCase)
            .Replace("Sociedade Esportiva", string.Empty, StringComparison.OrdinalIgnoreCase);

        return normalized.Trim().ToLowerInvariant();
    }

    public static bool IsSameTeam(string a, string b)
    {
        var na = Normalize(a);
        var nb = Normalize(b);
        return na == nb ||
               na.Contains(nb, StringComparison.OrdinalIgnoreCase) ||
               nb.Contains(na, StringComparison.OrdinalIgnoreCase);
    }

    private static string RemoveDiacritics(string text)
    {
        var normalizedString = text.Normalize(NormalizationForm.FormD);
        var stringBuilder = new StringBuilder();
        foreach (var c in normalizedString)
        {
            var unicodeCategory = CharUnicodeInfo.GetUnicodeCategory(c);
            if (unicodeCategory != UnicodeCategory.NonSpacingMark)
            {
                stringBuilder.Append(c);
            }
        }
        return stringBuilder.ToString().Normalize(NormalizationForm.FormC);
    }

    [GeneratedRegex(@"\s*[-–—]\s*[A-Z]{2}$|\s*\([A-Z]+\)$", RegexOptions.IgnoreCase)]
    private static partial Regex SuffixRegex();
}
