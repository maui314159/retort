using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Services;

public static class TeamNameNormalizer
{
    // Strips state suffix like "-SP", "-RJ", " - MG", " (description) - RJ"
    private static readonly Regex StateSuffixPattern =
        new(@"\s*[-–]\s*[A-Z]{2}\s*$", RegexOptions.Compiled);

    // Strips parenthetical descriptions like "(antigo Esporte Clube Barreira)"
    private static readonly Regex ParenPattern =
        new(@"\s*\(.*?\)\s*", RegexOptions.Compiled);

    public static string Normalize(string teamName)
    {
        if (string.IsNullOrWhiteSpace(teamName))
            return teamName;

        var name = teamName.Trim();
        // Remove parenthetical notes first
        name = ParenPattern.Replace(name, " ").Trim();
        // Remove state suffix
        name = StateSuffixPattern.Replace(name, "").Trim();
        return name;
    }

    public static bool Matches(string storedName, string queryName)
    {
        var normalizedStored = Normalize(storedName);
        var normalizedQuery = Normalize(queryName);
        return normalizedStored.Equals(normalizedQuery, StringComparison.OrdinalIgnoreCase)
            || normalizedStored.Contains(normalizedQuery, StringComparison.OrdinalIgnoreCase)
            || normalizedQuery.Contains(normalizedStored, StringComparison.OrdinalIgnoreCase);
    }
}
