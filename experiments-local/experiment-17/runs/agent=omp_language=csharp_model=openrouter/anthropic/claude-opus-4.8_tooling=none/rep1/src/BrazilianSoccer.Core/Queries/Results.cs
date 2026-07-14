// -----------------------------------------------------------------------------
// File: Queries/Results.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Plain result records returned by the query services. Keeping these separate
//   from both the raw domain models (Match/Player) and the MCP tool layer means
//   services return structured, testable data while the server layer is the only
//   place concerned with string formatting for the LLM. Every field here is
//   something a sample question in TASK.md asks for.
// -----------------------------------------------------------------------------

using BrazilianSoccer.Core.Models;

namespace BrazilianSoccer.Core.Queries;

/// <summary>Win/draw/loss/goal tally for one team over some set of matches.</summary>
public sealed record TeamRecord
{
    public required string Team { get; init; }
    public int Played { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }

    public int GoalDifference => GoalsFor - GoalsAgainst;

    /// <summary>Points using the standard 3-1-0 system.</summary>
    public int Points => Wins * 3 + Draws;

    /// <summary>Win rate as a fraction in [0,1]; 0 when no matches played.</summary>
    public double WinRate => Played == 0 ? 0 : (double)Wins / Played;
}

/// <summary>Head-to-head summary between two teams.</summary>
public sealed record HeadToHead
{
    public required string TeamA { get; init; }
    public required string TeamB { get; init; }
    public int TeamAWins { get; init; }
    public int TeamBWins { get; init; }
    public int Draws { get; init; }
    public int TeamAGoals { get; init; }
    public int TeamBGoals { get; init; }
    public required IReadOnlyList<Match> Matches { get; init; }

    public int TotalMatches => Matches.Count;
}

/// <summary>One row of a calculated league table.</summary>
public sealed record StandingRow
{
    public required int Position { get; init; }
    public required TeamRecord Record { get; init; }
}

/// <summary>A full calculated league table for one competition + season.</summary>
public sealed record Standings
{
    public required Competition Competition { get; init; }
    public required int Season { get; init; }
    public required IReadOnlyList<StandingRow> Rows { get; init; }
}

/// <summary>Aggregate statistics over a set of matches.</summary>
public sealed record MatchStatsSummary
{
    public int MatchesWithResult { get; init; }
    public int TotalGoals { get; init; }
    public int HomeWins { get; init; }
    public int AwayWins { get; init; }
    public int Draws { get; init; }

    public double AverageGoalsPerMatch
        => MatchesWithResult == 0 ? 0 : (double)TotalGoals / MatchesWithResult;

    public double HomeWinRate
        => MatchesWithResult == 0 ? 0 : (double)HomeWins / MatchesWithResult;

    public double AwayWinRate
        => MatchesWithResult == 0 ? 0 : (double)AwayWins / MatchesWithResult;

    public double DrawRate
        => MatchesWithResult == 0 ? 0 : (double)Draws / MatchesWithResult;
}

/// <summary>Per-club aggregation of FIFA players (used for "players at Brazilian clubs").</summary>
public sealed record ClubPlayers
{
    public required string Club { get; init; }
    public int Count { get; init; }
    public double AverageOverall { get; init; }
    public required IReadOnlyList<Player> Players { get; init; }
}
