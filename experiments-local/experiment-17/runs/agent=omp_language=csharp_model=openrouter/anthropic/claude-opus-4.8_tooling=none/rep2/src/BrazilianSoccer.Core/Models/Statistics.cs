// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    Statistics.cs
// Project: BrazilianSoccer.Core
// Purpose: Aggregate value objects returned by QueryService: team records,
//          head-to-head summaries, league standings rows and dataset-wide
//          statistics. These are pure data carriers consumed by the formatter
//          and the MCP tool layer.
// =============================================================================

namespace BrazilianSoccer.Core.Models;

/// <summary>Win/draw/loss + goals record for a team over a set of matches.</summary>
public sealed class TeamRecord
{
    public required string Team { get; init; }
    public int Played { get; set; }
    public int Wins { get; set; }
    public int Draws { get; set; }
    public int Losses { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }

    public int Points => Wins * 3 + Draws;
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public double WinRate => Played == 0 ? 0 : (double)Wins / Played;
}

/// <summary>Head-to-head summary between two teams.</summary>
public sealed class HeadToHead
{
    public required string TeamA { get; init; }
    public required string TeamB { get; init; }
    public int TeamAWins { get; set; }
    public int TeamBWins { get; set; }
    public int Draws { get; set; }
    public int TeamAGoals { get; set; }
    public int TeamBGoals { get; set; }
    public int TotalMatches => TeamAWins + TeamBWins + Draws;
    public IReadOnlyList<Match> Matches { get; init; } = [];
}

/// <summary>A single row in a calculated league table.</summary>
public sealed class StandingRow
{
    public int Position { get; set; }
    public required TeamRecord Record { get; init; }
}

/// <summary>Dataset-wide aggregate statistics for a slice of matches.</summary>
public sealed class MatchStatistics
{
    public int TotalMatches { get; init; }
    public int TotalGoals { get; init; }
    public int HomeWins { get; init; }
    public int AwayWins { get; init; }
    public int Draws { get; init; }

    public double AverageGoalsPerMatch =>
        TotalMatches == 0 ? 0 : (double)TotalGoals / TotalMatches;
    public double HomeWinRate => TotalMatches == 0 ? 0 : (double)HomeWins / TotalMatches;
    public double AwayWinRate => TotalMatches == 0 ? 0 : (double)AwayWins / TotalMatches;
    public double DrawRate => TotalMatches == 0 ? 0 : (double)Draws / TotalMatches;
}
