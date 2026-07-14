namespace BrazilianSoccerMcp.Models;

public sealed record SoccerMatch
{
    public DateTime Date { get; init; }
    public string HomeTeam { get; init; } = string.Empty;
    public string AwayTeam { get; init; } = string.Empty;
    public int HomeGoals { get; init; }
    public int AwayGoals { get; init; }
    public string Competition { get; init; } = string.Empty;
    public int Season { get; init; }
    public string Round { get; init; } = string.Empty;
    public string? Stage { get; init; }
    public string? HomeTeamState { get; init; }
    public string? AwayTeamState { get; init; }
    public string? Stadium { get; init; }
    // Extended stats from BR-Football-Dataset
    public double? HomeCorners { get; init; }
    public double? AwayCorners { get; init; }
    public double? HomeAttacks { get; init; }
    public double? AwayAttacks { get; init; }
    public double? HomeShots { get; init; }
    public double? AwayShots { get; init; }
    public double? TotalCorners { get; init; }
    public string? HalfTimeResult { get; init; }

    public string HomeTeamNormalized => Data.TeamNameNormalizer.Normalize(HomeTeam);
    public string AwayTeamNormalized => Data.TeamNameNormalizer.Normalize(AwayTeam);

    public int HomeGoalDiff => HomeGoals - AwayGoals;
    public bool IsHomeWin => HomeGoals > AwayGoals;
    public bool IsDraw => HomeGoals == AwayGoals;
    public bool IsAwayWin => AwayGoals > HomeGoals;
}
