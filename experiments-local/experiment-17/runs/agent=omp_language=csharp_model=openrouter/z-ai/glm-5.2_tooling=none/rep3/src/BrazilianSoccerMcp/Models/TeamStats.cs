// Brazilian Soccer MCP Server - TeamStats model
// Context: Aggregated win/draw/loss and goal tallies for a team, optionally
// restricted to a venue (home/away/overall) and a competition+season slice.
// Computed by the query service from the unified Match set; the MCP tool layer
// renders it into the formatted text blocks shown in the spec.

namespace BrazilianSoccerMcp.Models;

/// <summary>Aggregated record for one team over a set of matches.</summary>
public sealed record TeamStats
{
    public required string TeamKey { get; init; }
    public required string TeamName { get; init; }
    public int Matches { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }

    public int Points => Wins * 3 + Draws;
    public double WinRate => Matches == 0 ? 0 : (double)Wins / Matches;
    public int GoalDifference => GoalsFor - GoalsAgainst;
}
