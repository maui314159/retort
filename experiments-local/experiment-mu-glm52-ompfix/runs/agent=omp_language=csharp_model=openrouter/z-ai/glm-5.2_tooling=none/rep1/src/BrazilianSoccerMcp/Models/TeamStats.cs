// Brazilian Soccer MCP Server - Aggregated team statistics model
//
// Context: Computed (not stored) win/loss/draw record and goal tallies for a
// team, optionally scoped to a competition and/or season. Produced by
// SoccerDataService from the in-memory match set.

namespace BrazilianSoccerMcp.Models;

/// <summary>Aggregated win/draw/loss and goal record for a single team.</summary>
public sealed class TeamStats
{
    public string Team { get; set; } = string.Empty;
    public int Matches { get; set; }
    public int Wins { get; set; }
    public int Draws { get; set; }
    public int Losses { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }

    public int Points => Wins * 3 + Draws;
    public double WinRate => Matches == 0 ? 0 : (double)Wins / Matches * 100;
    public double GoalsPerMatch => Matches == 0 ? 0 : (double)GoalsFor / Matches;

    /// <summary>Formatted multi-line record matching the spec's answer format.</summary>
    public string Format(string? scope = null)
    {
        var header = string.IsNullOrWhiteSpace(scope) ? Team : $"{Team} ({scope})";
        return $"{header}:\n" +
               $"- Matches: {Matches}\n" +
               $"- Wins: {Wins}, Draws: {Draws}, Losses: {Losses}\n" +
               $"- Goals For: {GoalsFor}, Goals Against: {GoalsAgainst}\n" +
               $"- Points: {Points}\n" +
               $"- Win rate: {WinRate:F1}%";
    }
}

/// <summary>A standings row (points-based ranking) for a competition season.</summary>
public sealed class StandingsEntry
{
    public int Position { get; set; }
    public string Team { get; set; } = string.Empty;
    public int Played { get; set; }
    public int Wins { get; set; }
    public int Draws { get; set; }
    public int Losses { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public int Points => Wins * 3 + Draws;
    public bool Champion { get; set; }
}
