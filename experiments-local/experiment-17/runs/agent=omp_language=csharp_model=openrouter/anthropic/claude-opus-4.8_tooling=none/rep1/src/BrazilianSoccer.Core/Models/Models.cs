// -----------------------------------------------------------------------------
// File: Models/Models.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Core immutable domain models for the Brazilian Soccer MCP knowledge graph.
//   These types are the common shape that every CSV loader projects into, so
//   downstream query services never need to know which file a row came from.
//
//   - Competition: the tournament a match belongs to. The provided datasets mix
//     several competitions (Brasileirao Serie A/B/C, Copa do Brasil, Copa
//     Libertadores); normalising to this enum lets callers filter uniformly.
//   - DataSource: which physical CSV produced a Match. Several files overlap in
//     coverage (e.g. 2012-2019 Serie A appears in three files), so stats/standings
//     services use Source to deduplicate and prefer the richest source.
//   - Match: one fixture. Goals are nullable because a few historical rows are
//     incomplete; services treat null-goal rows as "scheduled / unknown result".
//   - Player: one FIFA player row (subset of the ~90 columns that matter here).
//
//   All collections are read-only; the data is loaded once at startup and never
//   mutated, which keeps the store trivially thread-safe for concurrent MCP calls.
// -----------------------------------------------------------------------------

namespace BrazilianSoccer.Core.Models;

/// <summary>Tournament a match belongs to.</summary>
public enum Competition
{
    Unknown = 0,

    /// <summary>Campeonato Brasileiro Serie A (top flight).</summary>
    BrasileiraoSerieA,

    /// <summary>Campeonato Brasileiro Serie B (second division).</summary>
    BrasileiraoSerieB,

    /// <summary>Campeonato Brasileiro Serie C (third division).</summary>
    BrasileiraoSerieC,

    /// <summary>Copa do Brasil (national cup).</summary>
    CopaDoBrasil,

    /// <summary>Copa Libertadores (continental cup).</summary>
    Libertadores,
}

/// <summary>The physical CSV file a row was loaded from.</summary>
public enum DataSource
{
    /// <summary>Brasileirao_Matches.csv (Serie A, 2012-2022).</summary>
    BrasileiraoMatches,

    /// <summary>Brazilian_Cup_Matches.csv (Copa do Brasil, 2012-2021).</summary>
    BrazilianCupMatches,

    /// <summary>Libertadores_Matches.csv (Copa Libertadores, 2013-2022).</summary>
    LibertadoresMatches,

    /// <summary>BR-Football-Dataset.csv (extended stats, Serie A/B/C + Copa do Brasil).</summary>
    ExtendedStats,

    /// <summary>novo_campeonato_brasileiro.csv (historical Serie A, 2003-2019).</summary>
    HistoricalBrasileirao,
}

/// <summary>
/// Optional richer per-match statistics. Only populated for rows from
/// BR-Football-Dataset.csv; null for every other source.
/// </summary>
public sealed record MatchStats(
    int? HomeCorners,
    int? AwayCorners,
    int? HomeAttacks,
    int? AwayAttacks,
    int? HomeShots,
    int? AwayShots,
    string? HalfTimeHomeResult,
    string? HalfTimeAwayResult,
    int? TotalCorners);

/// <summary>A single match/fixture, normalised across all source files.</summary>
public sealed record Match
{
    /// <summary>Tournament this match belongs to.</summary>
    public required Competition Competition { get; init; }

    /// <summary>CSV file this row came from.</summary>
    public required DataSource Source { get; init; }

    /// <summary>Season year (e.g. 2019). Null only when the source omits it.</summary>
    public int? Season { get; init; }

    /// <summary>Kick-off date/time when known.</summary>
    public DateTime? Date { get; init; }

    /// <summary>Round or stage label as printed by the source (e.g. "22", "Final").</summary>
    public string? Round { get; init; }

    /// <summary>Tournament stage for cup competitions (e.g. "group stage"). May be null.</summary>
    public string? Stage { get; init; }

    /// <summary>Home team display name, exactly as canonicalised by the loader.</summary>
    public required string HomeTeam { get; init; }

    /// <summary>Away team display name, exactly as canonicalised by the loader.</summary>
    public required string AwayTeam { get; init; }

    /// <summary>Goals scored by the home team; null when the result is unknown.</summary>
    public int? HomeGoals { get; init; }

    /// <summary>Goals scored by the away team; null when the result is unknown.</summary>
    public int? AwayGoals { get; init; }

    /// <summary>Stadium name when known (only the historical Brasileirao file carries it).</summary>
    public string? Venue { get; init; }

    /// <summary>Extended statistics; only present for ExtendedStats rows.</summary>
    public MatchStats? Stats { get; init; }

    /// <summary>True when both goal counts are present (a playable, decided result).</summary>
    public bool HasResult => HomeGoals.HasValue && AwayGoals.HasValue;
}

/// <summary>A FIFA player record (the subset of columns relevant to this server).</summary>
public sealed record Player
{
    public required int Id { get; init; }
    public required string Name { get; init; }
    public int? Age { get; init; }
    public required string Nationality { get; init; }
    public int? Overall { get; init; }
    public int? Potential { get; init; }
    public string? Club { get; init; }
    public string? Position { get; init; }
    public int? JerseyNumber { get; init; }
    public string? Height { get; init; }
    public string? Weight { get; init; }
    public string? PreferredFoot { get; init; }
}
