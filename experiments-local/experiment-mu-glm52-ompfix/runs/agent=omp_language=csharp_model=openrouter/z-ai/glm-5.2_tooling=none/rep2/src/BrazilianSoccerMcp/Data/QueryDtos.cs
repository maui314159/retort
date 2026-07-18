// ============================================================================
// BrazilianSoccerMcp - Data/QueryDtos.cs
//
// Context block:
//   Plain result DTOs returned by SoccerQueryService and serialized by the
//   MCP tool layer. Kept deliberately simple (records) so the MCP SDK can
//   JSON-serialize them and tests can assert field-by-field.
// ============================================================================

using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Data;

/// <summary>Which venue perspective to compute team statistics from.</summary>
public enum Venue { Either, Home, Away }

public sealed record TeamStats
{
    public string Team { get; init; } = "";
    public int? Season { get; init; }
    public Competition? Competition { get; init; }
    public Venue Venue { get; init; }
    public int Matches { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public double WinRate => Matches == 0 ? 0 : Wins * 100.0 / Matches;
}

public sealed record HeadToHead
{
    public string TeamA { get; init; } = "";
    public string TeamB { get; init; } = "";
    public int Total { get; init; }
    public int WinsA { get; init; }
    public int WinsB { get; init; }
    public int Draws { get; init; }
    public IReadOnlyList<Match> Matches { get; init; } = Array.Empty<Match>();
}

public sealed record StandingRow
{
    public int Position { get; init; }
    public string Team { get; init; } = "";
    public int Points { get; init; }
    public int Played { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public bool IsChampion { get; init; }
    public bool Relegated { get; init; }
}

public sealed record GoalsOverview
{
    public Competition? Competition { get; init; }
    public int Matches { get; init; }
    public double AverageGoalsPerMatch { get; init; }
    public double HomeWinRate { get; init; }
    public double AwayWinRate { get; init; }
    public double DrawRate { get; init; }
}
