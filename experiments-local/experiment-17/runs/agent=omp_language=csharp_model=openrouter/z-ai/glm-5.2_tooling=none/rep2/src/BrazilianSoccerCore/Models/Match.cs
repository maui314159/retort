using System.Globalization;

namespace BrazilianSoccerCore.Models;

/// <summary>
/// Unified match record across all provided CSV datasets.
/// </summary>
public sealed class Match
{
    /// <summary>Competition name used for grouping: Brasileirão, Copa do Brasil, etc.</summary>
    public string Competition { get; init; } = string.Empty;

    /// <summary>Source CSV file the record originated from.</summary>
    public string Source { get; init; } = string.Empty;

    public DateTime Date { get; init; }

    /// <summary>Normalized (no state suffix, no accents) home team display name.</summary>
    public string HomeTeam { get; init; } = string.Empty;

    /// <summary>Normalized away team display name.</summary>
    public string AwayTeam { get; init; } = string.Empty;

    public int? HomeGoal { get; init; }
    public int? AwayGoal { get; init; }
    public int? Season { get; init; }
    public string Round { get; init; } = string.Empty;
    public string Stage { get; init; } = string.Empty;
    public string Arena { get; init; } = string.Empty;

    // Extended statistics (BR-Football-Dataset only)
    public int? HomeCorner { get; init; }
    public int? AwayCorner { get; init; }
    public int? HomeShots { get; init; }
    public int? AwayShots { get; init; }
    public int? HomeAttack { get; init; }
    public int? AwayAttack { get; init; }
    public int? TotalCorners { get; init; }

    public string? HalfTimeResult { get; init; }
    public string? HalfTimeDiff { get; init; }

    /// <summary>Raw home team name as it appeared in the source file (pre-normalization).</summary>
    public string HomeTeamRaw { get; init; } = string.Empty;
    public string AwayTeamRaw { get; init; } = string.Empty;

    /// <summary>Winner of the match: "Home", "Away", or "Draw" (null if score missing).</summary>
    public string? Winner =>
        (HomeGoal, AwayGoal) switch
        {
            (null, _) or (_, null) => null,
            (var h, var a) when h > a => "Home",
            (var h, var a) when h < a => "Away",
            _ => "Draw"
        };

    public int? GoalDifference =>
        HomeGoal is { } hg && AwayGoal is { } ag ? Math.Abs(hg - ag) : null;

    public int? TotalGoals =>
        HomeGoal is { } hg && AwayGoal is { } ag ? hg + ag : null;
}