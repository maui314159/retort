namespace BrazilianSoccerMcpServer.Models;

public sealed record UnifiedMatch
{
    public DateTime? Date { get; init; }
    public required string Competition { get; init; }
    public required string HomeTeam { get; init; }
    public required string AwayTeam { get; init; }
    public required string HomeTeamBase { get; init; }
    public required string AwayTeamBase { get; init; }
    public string? HomeState { get; init; }
    public string? AwayState { get; init; }
    public int? HomeGoals { get; init; }
    public int? AwayGoals { get; init; }
    public int? Season { get; init; }
    public string? Round { get; init; }
    public string? Stage { get; init; }

    public bool IsHomeWin => HomeGoals.HasValue && AwayGoals.HasValue && HomeGoals > AwayGoals;
    public bool IsAwayWin => HomeGoals.HasValue && AwayGoals.HasValue && HomeGoals < AwayGoals;
    public bool IsDraw => HomeGoals.HasValue && AwayGoals.HasValue && HomeGoals == AwayGoals;
    public int? TotalGoals => HomeGoals.HasValue && AwayGoals.HasValue ? HomeGoals + AwayGoals : null;
    public int? GoalDifference => HomeGoals.HasValue && AwayGoals.HasValue ? HomeGoals - AwayGoals : null;

    public string FormatShort()
    {
        var date = Date.HasValue ? Date.Value.ToString("yyyy-MM-dd") : "?";
        var score = HomeGoals.HasValue && AwayGoals.HasValue
            ? $"{HomeGoals}-{AwayGoals}"
            : "?-?";
        var detail = Competition;
        if (Season.HasValue) detail += $" {Season}";
        if (!string.IsNullOrEmpty(Round)) detail += $" Round {Round}";
        if (!string.IsNullOrEmpty(Stage)) detail += $" {Stage}";
        return $"{date}: {HomeTeam} {score} {AwayTeam} ({detail})";
    }
}
