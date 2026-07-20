// BrazilianSoccerMcp.Core / Models / Match.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. This record unifies the row shapes of the
// five match CSVs described in TASK.md (Brasileirão, Copa do Brasil, Libertadores,
// the extended BR-Football-Dataset, and the historical 2003-2019 Brasileirão).
// Purpose: A single normalized in-memory representation so that queries across
// files can be expressed against one type instead of five.
// Design notes:
//   * Team names are stored both in their original form (for display fidelity, e.g.
//     "Palmeiras-SP", "América - MG") and in a normalized canonical form produced by
//     TeamNormalizer (for accent-/suffix-insensitive matching).
//   * Goals are nullable because some rows in Libertadores are blank; nullable keeps
//     the data honest instead of inventing a 0.
//   * Round/Stage/Stadium are optional and only populated by the files that carry
//     them. ExtraStats is populated only by the extended dataset.
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Models;

namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// Enrichment statistics only present in the extended BR-Football-Dataset rows.
/// </summary>
public sealed class MatchExtraStats
{
    public int? HomeCorners { get; set; }
    public int? AwayCorners { get; set; }
    public int? HomeShots { get; set; }
    public int? AwayShots { get; set; }
    public int? HomeAttacks { get; set; }
    public int? AwayAttacks { get; set; }
    public string? HalfTimeResult { get; set; }
    public int? TotalCorners { get; set; }
}

/// <summary>
/// Unified match record across all five match CSVs.
/// </summary>
public sealed class Match
{
    /// <summary>Source competition this row came from.</summary>
    public CompetitionKind Competition { get; set; }

    /// <summary>Free-text competition label as it appears in the source file
    /// (e.g. "Copa do Brasil", or the tournament column for the extended file).</summary>
    public string CompetitionLabel { get; set; } = string.Empty;

    public DateTime? Date { get; set; }

    /// <summary>Home team as written in the source CSV (e.g. "Palmeiras-SP").</summary>
    public string HomeTeamOriginal { get; set; } = string.Empty;

    /// <summary>Canonical, matchable home-team key (see TeamNormalizer).</summary>
    public string HomeTeam { get; set; } = string.Empty;

    public string? HomeTeamState { get; set; }

    public string AwayTeamOriginal { get; set; } = string.Empty;

    public string AwayTeam { get; set; } = string.Empty;

    public string? AwayTeamState { get; set; }

    public int? HomeGoals { get; set; }

    public int? AwayGoals { get; set; }

    public int? Season { get; set; }

    /// <summary>Round label as written in the source (round number or cup round name).</summary>
    public string? Round { get; set; }

    /// <summary>Libertadores stage (e.g. "group stage", "knockout").</summary>
    public string? Stage { get; set; }

    /// <summary>Stadium name, populated only by the historical Brasileirão file.</summary>
    public string? Stadium { get; set; }

    public MatchExtraStats? ExtraStats { get; set; }

    // ----- Derived helpers ---------------------------------------------------

    public bool HasScore => HomeGoals.HasValue && AwayGoals.HasValue;

    public MatchOutcome? OutcomeFor(string canonicalTeamName)
    {
        if (!HasScore) return null;
        var isHome = string.Equals(HomeTeam, canonicalTeamName, StringComparison.Ordinal);
        var isAway = string.Equals(AwayTeam, canonicalTeamName, StringComparison.Ordinal);
        if (!isHome && !isAway) return null;

        int hg = HomeGoals!.Value, ag = AwayGoals!.Value;
        if (hg == ag) return MatchOutcome.Draw;
        var teamWon = hg > ag;
        return (teamWon && isHome) || (!teamWon && isAway) ? MatchOutcome.Win : MatchOutcome.Loss;
    }

    public int? GoalsFor(string canonicalTeamName)
    {
        if (string.Equals(HomeTeam, canonicalTeamName, StringComparison.Ordinal)) return HomeGoals;
        if (string.Equals(AwayTeam, canonicalTeamName, StringComparison.Ordinal)) return AwayGoals;
        return null;
    }

    public int? GoalsAgainst(string canonicalTeamName)
    {
        if (string.Equals(HomeTeam, canonicalTeamName, StringComparison.Ordinal)) return AwayGoals;
        if (string.Equals(AwayTeam, canonicalTeamName, StringComparison.Ordinal)) return HomeGoals;
        return null;
    }

    public bool Involves(string canonicalTeamName) =>
        string.Equals(HomeTeam, canonicalTeamName, StringComparison.Ordinal) ||
        string.Equals(AwayTeam, canonicalTeamName, StringComparison.Ordinal);
}

public enum MatchOutcome { Win, Loss, Draw }
