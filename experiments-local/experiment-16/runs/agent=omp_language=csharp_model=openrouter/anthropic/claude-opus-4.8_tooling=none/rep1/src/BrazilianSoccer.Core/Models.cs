// =============================================================================
// Context: Brazilian Soccer MCP Server — Core domain models.
//
// Defines the immutable record types that flow through the data layer and query
// engine: Match (a single fixture from any of the five match CSVs), Player (a
// FIFA database row), and the aggregate result shapes (TeamRecord, StandingRow,
// HeadToHead). All match rows from heterogeneous CSVs are normalized into the
// single Match shape so the query engine treats every competition uniformly.
//
// Goals may be unknown (the source CSVs contain "NA"/empty cells), so HomeGoal /
// AwayGoal are nullable; only matches with both goals known participate in
// standings and win/loss aggregation.
// =============================================================================
namespace BrazilianSoccer.Core;

/// <summary>Competition a match belongs to.</summary>
public enum Competition
{
    BrasileiraoSerieA,
    BrasileiraoSerieB,
    BrasileiraoSerieC,
    CopaDoBrasil,
    Libertadores,
    Other,
}

/// <summary>
/// A single match, normalized from any source CSV. Team names are stored both
/// raw (as they appear in the file) and normalized (state suffix stripped,
/// accents folded, lower-cased) for matching.
/// </summary>
public sealed record Match
{
    public required Competition Competition { get; init; }
    public DateOnly? Date { get; init; }
    public int? Season { get; init; }
    public string? Round { get; init; }
    public string? Stage { get; init; }

    public required string HomeTeam { get; init; }
    public required string AwayTeam { get; init; }
    public required string HomeTeamKey { get; init; }
    public required string AwayTeamKey { get; init; }

    public int? HomeGoal { get; init; }
    public int? AwayGoal { get; init; }

    /// <summary>Source dataset / venue identifier for provenance.</summary>
    public required string Source { get; init; }
    public string? Arena { get; init; }

    /// <summary>True when both goal counts are known (match was actually played and recorded).</summary>
    public bool HasResult => HomeGoal.HasValue && AwayGoal.HasValue;
}

/// <summary>A FIFA database player row (subset of columns relevant to the spec).</summary>
public sealed record Player
{
    public int Id { get; init; }
    public required string Name { get; init; }
    public required string NameKey { get; init; }
    public int? Age { get; init; }
    public required string Nationality { get; init; }
    public int? Overall { get; init; }
    public int? Potential { get; init; }
    public string? Club { get; init; }
    public string? ClubKey { get; init; }
    public string? Position { get; init; }
    public string? JerseyNumber { get; init; }
    public string? Height { get; init; }
    public string? Weight { get; init; }
}

/// <summary>Aggregated win/draw/loss/goals record for a team over a filtered match set.</summary>
public sealed record TeamRecord
{
    public required string Team { get; init; }
    public int Matches { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }

    public int Points => Wins * 3 + Draws;
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public double WinRate => Matches == 0 ? 0d : (double)Wins / Matches;
}

/// <summary>One row of a calculated league table.</summary>
public sealed record StandingRow
{
    public required string Team { get; init; }
    public int Position { get; init; }
    public required TeamRecord Record { get; init; }
}

/// <summary>Head-to-head summary between two teams from team A's perspective.</summary>
public sealed record HeadToHead
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
