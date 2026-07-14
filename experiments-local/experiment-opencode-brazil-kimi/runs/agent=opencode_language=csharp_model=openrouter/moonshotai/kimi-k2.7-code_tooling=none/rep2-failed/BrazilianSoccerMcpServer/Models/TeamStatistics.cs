namespace BrazilianSoccerMcpServer.Models;

public sealed record TeamStatistics
{
    public string Team { get; init; } = string.Empty;
    public int Matches { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public int Points => Wins * 3 + Draws;
    public double WinRate => Matches == 0 ? 0 : (double)Wins / Matches;
    public int HomeWins { get; init; }
    public int HomeDraws { get; init; }
    public int HomeLosses { get; init; }
    public int AwayWins { get; init; }
    public int AwayDraws { get; init; }
    public int AwayLosses { get; init; }
    public string Context { get; init; } = string.Empty;
}
