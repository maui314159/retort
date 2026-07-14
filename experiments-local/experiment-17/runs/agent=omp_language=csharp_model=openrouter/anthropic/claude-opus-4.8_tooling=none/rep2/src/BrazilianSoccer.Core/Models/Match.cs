// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    Match.cs
// Project: BrazilianSoccer.Core
// Purpose: Unified match record produced from every match CSV (Brasileirão,
//          Copa do Brasil, Libertadores, the extended BR-Football stats set and
//          the historical 2003-2019 Brasileirão file). All source files are
//          mapped onto this single shape so queries are dataset-agnostic.
// Notes:   Display names keep accents; HomeTeamKey/AwayTeamKey are the
//          normalised canonical keys used for matching/grouping.
// =============================================================================

namespace BrazilianSoccer.Core.Models;

/// <summary>The competition a match belongs to.</summary>
public enum Competition
{
    Brasileirao,
    CopaDoBrasil,
    Libertadores,
    Other,
}

/// <summary>Result of a match from the home team's perspective.</summary>
public enum MatchResult
{
    HomeWin,
    AwayWin,
    Draw,
}

/// <summary>A single normalised match across all datasets.</summary>
public sealed class Match
{
    public required string HomeTeam { get; init; }
    public required string AwayTeam { get; init; }
    public required string HomeTeamKey { get; init; }
    public required string AwayTeamKey { get; init; }
    public int HomeGoals { get; init; }
    public int AwayGoals { get; init; }
    public DateTime? Date { get; init; }
    public int? Season { get; init; }
    public string? Round { get; init; }
    public string? Stage { get; init; }
    public Competition Competition { get; init; }
    public string Source { get; init; } = string.Empty;

    /// <summary>Stadium/arena, when the source provides it.</summary>
    public string? Arena { get; init; }

    public MatchResult Result => HomeGoals > AwayGoals
        ? MatchResult.HomeWin
        : HomeGoals < AwayGoals
            ? MatchResult.AwayWin
            : MatchResult.Draw;

    public int TotalGoals => HomeGoals + AwayGoals;

    public string CompetitionName => Competition switch
    {
        Competition.Brasileirao => "Brasileirão",
        Competition.CopaDoBrasil => "Copa do Brasil",
        Competition.Libertadores => "Copa Libertadores",
        _ => "Other",
    };
}
