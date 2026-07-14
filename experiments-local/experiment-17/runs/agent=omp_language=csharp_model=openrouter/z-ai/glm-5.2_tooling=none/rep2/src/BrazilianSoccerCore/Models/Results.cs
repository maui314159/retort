namespace BrazilianSoccerCore.Models;

/// <summary>Head-to-head comparison result between two teams.</summary>
public sealed class HeadToHeadResult
{
    public string TeamA { get; init; } = string.Empty;
    public string TeamB { get; init; } = string.Empty;
    public int Matches { get; init; }
    public int TeamAWins { get; init; }
    public int TeamBWins { get; init; }
    public int Draws { get; init; }
    public int TeamAGoals { get; init; }
    public int TeamBGoals { get; init; }
}

/// <summary>Aggregate team statistics over a (possibly filtered) set of matches.</summary>
public sealed class TeamStats
{
    public string Team { get; init; } = string.Empty;
    public int Matches { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public double WinRate => Matches == 0 ? 0 : Math.Round((double)Wins / Matches * 100, 1);

    /// <summary>Filtered to home/away when the caller asked for a venue-specific record.</summary>
    public string? Venue { get; init; }
    public string? Competition { get; init; }
    public int? Season { get; init; }
}

/// <summary>A single standings row computed from match results.</summary>
public sealed class StandingsRow
{
    public int Position { get; init; }
    public string Team { get; init; } = string.Empty;
    public int Points { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public int GoalDifference { get; init; }
    public int Matches { get; init; }
}

/// <summary>Aggregate statistics over a set of matches.</summary>
public sealed class MatchAggregateStats
{
    public int Matches { get; init; }
    public int HomeWins { get; init; }
    public int AwayWins { get; init; }
    public int Draws { get; init; }
    public int TotalGoals { get; init; }
    public double AverageGoalsPerMatch { get; init; }
    public double HomeWinRate { get; init; }
    public double AwayWinRate { get; init; }
    public double DrawRate { get; init; }
}