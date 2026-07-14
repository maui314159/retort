// =============================================================================
// Brazilian Soccer MCP Server
// File: TeamRecord.cs
// Purpose: Aggregated team-level statistics computed from match data.
// Context: Returned by the team query endpoints. Win/Draw/Loss are
//          counted across all competitions when Competition == null, or
//          scoped to one competition otherwise.
// =============================================================================

namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// Win/loss/draw summary for a single team, optionally scoped to a
/// competition and home/away side.
/// </summary>
public sealed record TeamRecord
{
    public required string Team { get; init; }
    public string? Competition { get; init; }
    public string? HomeOrAway { get; init; }   // "Home" | "Away" | null == all
    public int? Season { get; init; }
    public required int Played { get; init; }
    public required int Wins { get; init; }
    public required int Draws { get; init; }
    public required int Losses { get; init; }
    public required int GoalsFor { get; init; }
    public required int GoalsAgainst { get; init; }

    public double WinRate => Played == 0 ? 0.0 : (double)Wins / Played;
}
