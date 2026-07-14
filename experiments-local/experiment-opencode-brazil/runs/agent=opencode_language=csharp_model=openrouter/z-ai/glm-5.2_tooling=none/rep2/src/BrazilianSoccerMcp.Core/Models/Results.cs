// BrazilianSoccerMcp.Core - Query result models used by the query service
// and the MCP tools. These are simple, serializable DTOs.
namespace BrazilianSoccerMcp.Core.Models;

/// <summary>Aggregated win/draw/loss and goals for one team, optionally filtered.</summary>
public sealed class TeamStats
{
    public string Team { get; init; } = "";
    public int Matches { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public int HomeMatches { get; init; }
    public int HomeWins { get; init; }
    public int HomeDraws { get; init; }
    public int HomeLosses { get; init; }
    public int AwayMatches { get; init; }
    public int AwayWins { get; init; }
    public int AwayDraws { get; init; }
    public int AwayLosses { get; init; }
    public int Points { get; init; }
    public double WinRate => Matches == 0 ? 0 : (double)Wins / Matches;
    public double HomeWinRate => HomeMatches == 0 ? 0 : (double)HomeWins / HomeMatches;
    public double AwayWinRate => AwayMatches == 0 ? 0 : (double)AwayWins / AwayMatches;
    public int GoalDifference => GoalsFor - GoalsAgainst;
}

/// <summary>Head-to-head comparison between two teams.</summary>
public sealed record HeadToHead
{
    public string TeamA { get; init; } = "";
    public string TeamB { get; init; } = "";
    public int TeamAWins { get; init; }
    public int TeamBWins { get; init; }
    public int Draws { get; init; }
    public int Matches { get; init; }
    public IReadOnlyList<Match> MatchesList { get; init; } = Array.Empty<Match>();
}

/// <summary>A single row in a calculated standings table.</summary>
public sealed record StandingsRow
{
    public int Position { get; init; }
    public string Team { get; init; } = "";
    public int Played { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public int Points { get; init; }
    public bool Champion { get; init; }
}
