// BrazilianSoccerMcp.Core - Unified match model.
// Every match record from the five CSV sources is normalized into this shape
// so that cross-file queries (e.g. "all Palmeiras matches across competitions")
// can be answered through a single LINQ surface.
using BrazilianSoccerMcp.Core.Data;

namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// A single soccer match normalized across all provided CSV datasets.
/// Optional fields are populated only by the datasets that carry them
/// (e.g. corners/shots only come from BR-Football-Dataset.csv).
/// </summary>
public sealed class Match
{
    public Competition Competition { get; init; }
    /// <summary>Raw tournament label as found in the source file (e.g. "Serie A").</summary>
    public string RawCompetition { get; init; } = "";
    public DateTime Date { get; init; }
    public string HomeTeam { get; init; } = "";
    public string AwayTeam { get; init; } = "";
    public int HomeGoal { get; init; }
    public int AwayGoal { get; init; }
    public int Season { get; init; }
    public string Round { get; init; } = "";
    public string Stage { get; init; } = "";
    public string Arena { get; init; } = "";
    public string HomeState { get; init; } = "";
    public string AwayState { get; init; } = "";

    // Extended statistics (BR-Football-Dataset only).
    public double? HomeCorner { get; init; }
    public double? AwayCorner { get; init; }
    public double? HomeAttack { get; init; }
    public double? AwayAttack { get; init; }
    public double? HomeShots { get; init; }
    public double? AwayShots { get; init; }
    public string? HalfTimeResult { get; init; }
    public double? TotalCorners { get; init; }

    public bool HasStatistics => HomeCorner.HasValue || HomeShots.HasValue;

    public string Result =>
        HomeGoal == AwayGoal ? "Draw"
        : HomeGoal > AwayGoal ? "HomeWin"
        : "AwayWin";

    public int GoalDifference => Math.Abs(HomeGoal - AwayGoal);

    public string Score => $"{HomeGoal}-{AwayGoal}";
}
