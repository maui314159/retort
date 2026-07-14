// <copyright file="CompetitionCatalog.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Canonical competition names and detection.
// </copyright>
namespace BrazilianSoccerMcp.Core.Normalization;

/// <summary>
/// Canonical competition names and helpers to identify them from raw data.
/// </summary>
public static class CompetitionCatalog
{
    public const string Brasileirao = "Brasileirão";
    public const string CopaDoBrasil = "Copa do Brasil";
    public const string CopaLibertadores = "Copa Libertadores";

    /// <summary>
    /// Maps rough input strings to canonical competition names.
    /// </summary>
    public static string Normalize(string? rawName)
    {
        if (string.IsNullOrWhiteSpace(rawName))
            return Brasileirao;

        var lower = rawName.Trim().ToLowerInvariant();

        if (lower.Contains("brasileir") || lower.Contains("campeonato brasileiro") || lower.Contains("serie a"))
            return Brasileirao;

        if (lower.Contains("copa do brasil") || lower.Contains("brazilian cup"))
            return CopaDoBrasil;

        if (lower.Contains("libertadores") || lower.Contains("copa libertadores"))
            return CopaLibertadores;

        // Source file-based fallback.
        if (lower.Contains("br-football") || lower.Contains("br_football"))
            return Brasileirao;

        return Capitalize(rawName.Trim());
    }

    /// <summary>
    /// Returns true when two competition names are canonically equal.
    /// </summary>
    public static bool Matches(string? nameA, string? nameB)
    {
        return Normalize(nameA).Equals(Normalize(nameB), StringComparison.OrdinalIgnoreCase);
    }

    private static string Capitalize(string input)
    {
        if (string.IsNullOrEmpty(input))
            return input;

        return input[0].ToString().ToUpperInvariant() + input[1..];
    }
}
