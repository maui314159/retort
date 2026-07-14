namespace BrazilianSoccerMCP.Models;

public record UnifiedMatch
{
    public DateTime? Date { get; init; }
    public int? Season { get; init; }
    public string Competition { get; init; } = "";
    public string HomeTeam { get; init; } = "";
    public string AwayTeam { get; init; } = "";
    public double HomeGoals { get; init; }
    public double AwayGoals { get; init; }
    public string Round { get; init; } = "";
    public string Stage { get; init; } = "";

    public string Winner => HomeGoals > AwayGoals ? "home"
        : AwayGoals > HomeGoals ? "away"
        : "draw";

    public double GoalDifference => Math.Abs(HomeGoals - AwayGoals);
}