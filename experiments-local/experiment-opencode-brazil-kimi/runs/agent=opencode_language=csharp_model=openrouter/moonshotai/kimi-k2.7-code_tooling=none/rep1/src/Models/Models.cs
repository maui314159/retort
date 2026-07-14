/*
 * Brazilian Soccer MCP Server - Data Models
 *
 * Unified domain models used by the query engine and exposed through MCP tools.
 * Match records are normalized from the six heterogeneous CSV sources so that
 * the query engine can operate on a single, consistent shape.
 */
namespace BrazilianSoccerMcp.Models;

/// <summary>
/// A normalized match record aggregated from all provided CSV datasets.
/// </summary>
public sealed record MatchRecord
{
    public DateTime? Date { get; init; }
    public required string HomeTeam { get; init; }
    public required string AwayTeam { get; init; }
    public int? HomeGoals { get; init; }
    public int? AwayGoals { get; init; }
    public required string Competition { get; init; }
    public int? Season { get; init; }
    public string? Round { get; init; }
    public string? Stage { get; init; }
    public string? Stadium { get; init; }

    public bool IsDraw => HomeGoals.HasValue && AwayGoals.HasValue && HomeGoals.Value == AwayGoals.Value;
    public bool HomeWin => HomeGoals.HasValue && AwayGoals.HasValue && HomeGoals.Value > AwayGoals.Value;
    public bool AwayWin => HomeGoals.HasValue && AwayGoals.HasValue && HomeGoals.Value < AwayGoals.Value;

    public string Winner()
    {
        if (!HomeGoals.HasValue || !AwayGoals.HasValue) return "Unknown";
        if (HomeGoals.Value > AwayGoals.Value) return HomeTeam;
        if (HomeGoals.Value < AwayGoals.Value) return AwayTeam;
        return "Draw";
    }
}

/// <summary>
/// A player record from the FIFA player dataset.
/// </summary>
public sealed record PlayerRecord
{
    public int? Id { get; init; }
    public required string Name { get; init; }
    public int? Age { get; init; }
    public string? Nationality { get; init; }
    public int? Overall { get; init; }
    public int? Potential { get; init; }
    public string? Club { get; init; }
    public string? Position { get; init; }
    public string? JerseyNumber { get; init; }
    public string? Height { get; init; }
    public string? Weight { get; init; }
}

/// <summary>
/// Aggregated team statistics for a set of matches.
/// </summary>
public sealed record TeamStatistics
{
    public required string Team { get; init; }
    public int Matches { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public int Points => Wins * 3 + Draws;
    public double WinRate => Matches == 0 ? 0 : (double)Wins / Matches;
}

/// <summary>
/// Head-to-head statistics between two teams.
/// </summary>
public sealed record HeadToHeadRecord
{
    public required string TeamA { get; init; }
    public required string TeamB { get; init; }
    public int Matches { get; init; }
    public int TeamAWins { get; init; }
    public int TeamBWins { get; init; }
    public int Draws { get; init; }
    public int TeamAGoals { get; init; }
    public int TeamBGoals { get; init; }
}

/// <summary>
/// A competition standing row.
/// </summary>
public sealed record StandingRow
{
    public required string Team { get; init; }
    public int Points { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public int Matches => Wins + Draws + Losses;
    public int GoalDifference => GoalsFor - GoalsAgainst;
}
