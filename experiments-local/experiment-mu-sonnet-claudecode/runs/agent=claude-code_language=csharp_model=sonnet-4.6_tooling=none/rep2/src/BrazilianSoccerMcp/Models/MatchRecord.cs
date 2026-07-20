namespace BrazilianSoccerMcp.Models;

public record MatchRecord
{
    public string Competition { get; init; } = "";
    public string HomeTeam { get; init; } = "";
    public string AwayTeam { get; init; } = "";
    public string NormalizedHomeTeam { get; init; } = "";
    public string NormalizedAwayTeam { get; init; } = "";
    public int? HomeGoal { get; init; }
    public int? AwayGoal { get; init; }
    public DateTime? Date { get; init; }
    public int? Season { get; init; }
    public string? Round { get; init; }
    public string? Stage { get; init; }
}
