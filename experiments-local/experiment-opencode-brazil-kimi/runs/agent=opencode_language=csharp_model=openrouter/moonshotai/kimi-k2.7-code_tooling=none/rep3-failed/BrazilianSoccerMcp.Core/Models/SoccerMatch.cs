// <copyright file="SoccerMatch.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Unified match model used across all CSV sources.
// </copyright>
namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// Represents a normalized soccer match loaded from any of the provided CSV datasets.
/// </summary>
public sealed class SoccerMatch
{
    /// <summary>
    /// Unique identifier assigned during import.
    /// </summary>
    public string Id { get; init; } = Guid.NewGuid().ToString("N");

    /// <summary>
    /// Match date (normalized to UTC-less DateOnly when possible).
    /// </summary>
    public DateTime? Date { get; init; }

    /// <summary>
    /// Normalized home team name.
    /// </summary>
    public string HomeTeam { get; init; } = string.Empty;

    /// <summary>
    /// Normalized away team name.
    /// </summary>
    public string AwayTeam { get; init; } = string.Empty;

    /// <summary>
    /// Goals scored by the home team.
    /// </summary>
    public int? HomeGoals { get; init; }

    /// <summary>
    /// Goals scored by the away team.
    /// </summary>
    public int? AwayGoals { get; init; }

    /// <summary>
    /// Normalized competition name.
    /// </summary>
    public string Competition { get; init; } = string.Empty;

    /// <summary>
    /// Season / year of the match.
    /// </summary>
    public int? Season { get; init; }

    /// <summary>
    /// Round, stage or phase of the competition.
    /// </summary>
    public string? Round { get; init; }

    /// <summary>
    /// Original source file name.
    /// </summary>
    public string SourceFile { get; init; } = string.Empty;

    /// <summary>
    /// Human-readable string for the match result.
    /// </summary>
    public string ResultText => $"{HomeTeam} {HomeGoals}-{AwayGoals} {AwayTeam}";

    /// <summary>
    /// Determines whether the team supplied is involved in this match.
    /// </summary>
    public bool Involves(string team)
    {
        return HomeTeam.Equals(team, StringComparison.OrdinalIgnoreCase)
            || AwayTeam.Equals(team, StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>
    /// Returns the outcome for the supplied team, if it takes part in this match.
    /// </summary>
    public MatchOutcome OutcomeFor(string team)
    {
        if (!Involves(team) || !HomeGoals.HasValue || !AwayGoals.HasValue)
            return MatchOutcome.Unknown;

        var isHome = HomeTeam.Equals(team, StringComparison.OrdinalIgnoreCase);
        var teamGoals = isHome ? HomeGoals.Value : AwayGoals.Value;
        var opponentGoals = isHome ? AwayGoals.Value : HomeGoals.Value;

        return teamGoals > opponentGoals ? MatchOutcome.Win
            : teamGoals < opponentGoals ? MatchOutcome.Loss
            : MatchOutcome.Draw;
    }

    /// <summary>
    /// Goals scored by the supplied team in this match.
    /// </summary>
    public int? GoalsFor(string team)
    {
        if (HomeTeam.Equals(team, StringComparison.OrdinalIgnoreCase))
            return HomeGoals;
        if (AwayTeam.Equals(team, StringComparison.OrdinalIgnoreCase))
            return AwayGoals;
        return null;
    }

    /// <summary>
    /// Goals conceded by the supplied team in this match.
    /// </summary>
    public int? GoalsAgainst(string team)
    {
        if (HomeTeam.Equals(team, StringComparison.OrdinalIgnoreCase))
            return AwayGoals;
        if (AwayTeam.Equals(team, StringComparison.OrdinalIgnoreCase))
            return HomeGoals;
        return null;
    }
}

/// <summary>
/// Possible outcomes of a match from a team's perspective.
/// </summary>
public enum MatchOutcome
{
    Unknown,
    Win,
    Draw,
    Loss
}
