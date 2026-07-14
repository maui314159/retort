// Brazilian Soccer MCP Server - Match model
// Context: Unified match record projected from the six heterogeneous match CSV
// files. All source-specific column names (datetime, Data, home, Equipe_mandante,
// Gols_mandante, etc.) are normalised onto this single shape so the query layer
// can treat every competition uniformly. Optional fields (Round, Stage, Arena,
// corners/shots) are only populated when the originating file provides them.

using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Models;

/// <summary>A single Brazilian football match resolved from any of the CSV sources.</summary>
public sealed class Match
{
    /// <summary>Canonical competition bucket.</summary>
    public required Competition Competition { get; init; }

    /// <summary>Raw tournament/competition label from the source file (for display).</summary>
    public required string CompetitionLabel { get; init; }

    /// <summary>Raw home team string exactly as it appears in the source file.</summary>
    public required string HomeTeam { get; init; }

    /// <summary>Raw away team string exactly as it appears in the source file.</summary>
    public required string AwayTeam { get; init; }

    /// <summary>Canonical (normalised) home team key used for grouping/matching.</summary>
    public required string HomeTeamKey { get; init; }

    /// <summary>Canonical (normalised) away team key used for grouping/matching.</summary>
    public required string AwayTeamKey { get; init; }

    /// <summary>Home team goals (0 when the source row is missing a score).</summary>
    public int HomeGoal { get; init; }

    /// <summary>Away team goals (0 when the source row is missing a score).</summary>
    public int AwayGoal { get; init; }

    /// <summary>Season year, or null when not derivable from the source row.</summary>
    public int? Season { get; init; }

    /// <summary>Match date (UTC-unspecified, parsed from the source), or null if unparseable.</summary>
    public DateOnly? Date { get; init; }

    /// <summary>Round/stage label (e.g. "22", "Final", "group stage").</summary>
    public string? Round { get; init; }

    /// <summary>Stadium name when available (historical dataset only).</summary>
    public string? Arena { get; init; }

    /// <summary>True when the source row carried a valid final score for both teams.</summary>
    public bool HasScore => HomeGoal >= 0 && AwayGoal >= 0;

    /// <summary>Total goals scored in the match.</summary>
    public int TotalGoals => HomeGoal + AwayGoal;

    /// <summary>Absolute goal difference (used for "biggest wins").</summary>
    public int GoalDifference => Math.Abs(HomeGoal - AwayGoal);
}
