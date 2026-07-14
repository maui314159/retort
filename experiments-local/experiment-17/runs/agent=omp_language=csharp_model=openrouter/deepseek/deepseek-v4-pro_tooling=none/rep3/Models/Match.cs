namespace BrazilianSoccerMCP.Models;

/// <summary>
/// Unified match model used across all data sources.
/// Team names are normalized (no state suffix, trimmed).
/// </summary>
public class Match
{
    public string Competition { get; set; } = "";
    public DateTime Date { get; set; }
    public string HomeTeam { get; set; } = "";
    public string AwayTeam { get; set; } = "";
    public int HomeGoal { get; set; }
    public int AwayGoal { get; set; }
    public int? Season { get; set; }
    public string? Round { get; set; }
    public string? Stage { get; set; }
    public string? Stadium { get; set; }
    public string? HomeTeamState { get; set; }
    public string? AwayTeamState { get; set; }

    // Extended stats from BR-Football-Dataset.csv
    public double? HomeCorner { get; set; }
    public double? AwayCorner { get; set; }
    public double? HomeAttack { get; set; }
    public double? AwayAttack { get; set; }
    public double? HomeShots { get; set; }
    public double? AwayShots { get; set; }
    public string? HalfTimeResult { get; set; }
    public double? TotalCorners { get; set; }

    /// <summary>Winner: "home", "away", or "draw".</summary>
    public string Winner =>
        HomeGoal > AwayGoal ? "home" :
        AwayGoal > HomeGoal ? "away" : "draw";

    /// <summary>Total goals in the match.</summary>
    public int TotalGoals => HomeGoal + AwayGoal;

    /// <summary>Goal difference.</summary>
    public int GoalDiff => Math.Abs(HomeGoal - AwayGoal);
}
