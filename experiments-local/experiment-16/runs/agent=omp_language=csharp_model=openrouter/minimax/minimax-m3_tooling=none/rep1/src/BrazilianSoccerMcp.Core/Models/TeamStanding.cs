// =============================================================================
// Brazilian Soccer MCP Server
// File: TeamStanding.cs
// Purpose: Computed league/competition standing for a team in a given season.
// Context: Built on demand by aggregating MatchRecord rows. The query engine
//          orders by the official 3-1-0 scoring (W win / D draw) used in the
//          Brasileirão.
// =============================================================================

namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// A single team's row in a calculated competition standings table.
/// </summary>
public sealed record TeamStanding
{
    public required string Team { get; init; }
    public required int Played { get; init; }
    public required int Wins { get; init; }
    public required int Draws { get; init; }
    public required int Losses { get; init; }
    public required int GoalsFor { get; init; }
    public required int GoalsAgainst { get; init; }
    public int Points => Wins * 3 + Draws;
    public int GoalDifference => GoalsFor - GoalsAgainst;
}
