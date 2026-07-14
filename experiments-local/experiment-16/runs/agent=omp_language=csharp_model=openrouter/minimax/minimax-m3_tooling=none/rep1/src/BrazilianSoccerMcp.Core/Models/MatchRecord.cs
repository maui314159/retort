// =============================================================================
// Brazilian Soccer MCP Server
// File: MatchRecord.cs
// Purpose: Canonical, normalized match representation across all data sources.
// Context: Each CSV loader maps its own row schema into this single record so
//          the query engine can treat matches from different competitions
//          uniformly. All nullable fields are intentionally optional because
//          some datasets omit goals, state codes, or tournament round info.
// =============================================================================

namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// Unified match record produced by every loader.
/// All team-name fields are stored in their original CSV form; the engine
/// applies <see cref="BrazilianSoccerMcp.Core.TeamNameNormalizer"/> at query time
/// so that fuzzy matches work across the entire corpus.
/// </summary>
public sealed record MatchRecord
{
    public required Competition Competition { get; init; }
    public required string HomeTeam { get; init; }
    public required string AwayTeam { get; init; }
    public string? HomeTeamState { get; init; }
    public string? AwayTeamState { get; init; }
    public int HomeGoal { get; init; }
    public int AwayGoal { get; init; }
    public int Season { get; init; }
    public DateTime Date { get; init; }
    public string? Round { get; init; }
    public string? Stage { get; init; }   // Libertadores only
    public string? Arena { get; init; }   // novo_campeonato_brasileiro only
    public string? SourceId { get; init; }

    // Extended stats (BR-Football-Dataset) -- nullable because the other
    // datasets do not provide them.
    public int? HomeCorners { get; init; }
    public int? AwayCorners { get; init; }
    public int? HomeShots { get; init; }
    public int? AwayShots { get; init; }
    public int? HomeAttacks { get; init; }
    public int? AwayAttacks { get; init; }
    public string? HalfTimeHomeResult { get; init; }
    public string? HalfTimeAwayResult { get; init; }
}
