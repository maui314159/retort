using System.Globalization;
using System.Text;

namespace BrazilianSoccerMcpServer.Services;

public static class TeamNameMatcher
{
    private static readonly HashSet<string> BrazilianStates = new(StringComparer.OrdinalIgnoreCase)
    {
        "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg",
        "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to"
    };

    public static string Normalize(string name)
    {
        if (string.IsNullOrWhiteSpace(name)) return string.Empty;

        var noDiacritics = RemoveDiacritics(name);
        var lowered = noDiacritics.ToLowerInvariant();
        var builder = new StringBuilder(lowered.Length);
        foreach (var ch in lowered)
        {
            builder.Append(char.IsLetterOrDigit(ch) ? ch : ' ');
        }

        // collapse whitespace
        var compacted = string.Join(" ", builder.ToString().Split(' ', StringSplitOptions.RemoveEmptyEntries));
        return compacted;
    }

    public static string BaseName(string name)
    {
        var normalized = Normalize(name);
        var tokens = normalized.Split(' ', StringSplitOptions.RemoveEmptyEntries).ToList();

        // Remove trailing state abbreviations.
        while (tokens.Count > 0 && BrazilianStates.Contains(tokens[^1]))
        {
            tokens.RemoveAt(tokens.Count - 1);
        }

        return string.Join(" ", tokens);
    }

    public static string? ExtractState(string name)
    {
        var normalized = Normalize(name);
        var tokens = normalized.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        for (var i = tokens.Length - 1; i >= 0; i--)
        {
            if (BrazilianStates.Contains(tokens[i]))
            {
                return tokens[i].ToUpperInvariant();
            }
        }
        return null;
    }

    public static string DisplayName(string rawName)
    {
        // Prefer the base form for display; if the base is empty fall back to the raw name.
        var baseName = BaseName(rawName);
        if (string.IsNullOrWhiteSpace(baseName))
        {
            return rawName.Trim();
        }
        // Title-case each word for nicer output.
        var textInfo = CultureInfo.InvariantCulture.TextInfo;
        return textInfo.ToTitleCase(baseName);
    }

    public static bool IsMatch(string candidate, string query)
    {
        var candidateNorm = Normalize(candidate);
        var queryNorm = Normalize(query);
        if (string.IsNullOrWhiteSpace(queryNorm)) return false;

        return candidateNorm.Equals(queryNorm, StringComparison.OrdinalIgnoreCase)
            || candidateNorm.Contains(queryNorm, StringComparison.OrdinalIgnoreCase)
            || queryNorm.Contains(candidateNorm, StringComparison.OrdinalIgnoreCase);
    }

    private static string RemoveDiacritics(string text)
    {
        var normalized = text.Normalize(NormalizationForm.FormD);
        var builder = new StringBuilder(normalized.Length);
        foreach (var ch in normalized)
        {
            var category = CharUnicodeInfo.GetUnicodeCategory(ch);
            if (category != UnicodeCategory.NonSpacingMark)
            {
                builder.Append(ch);
            }
        }
        return builder.ToString().Normalize(NormalizationForm.FormC);
    }
}
