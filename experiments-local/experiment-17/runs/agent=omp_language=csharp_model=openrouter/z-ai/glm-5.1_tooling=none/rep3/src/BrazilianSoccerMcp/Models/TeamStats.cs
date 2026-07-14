namespace BrazilianSoccerMcp.Models;

public sealed class TeamStats
{
    public string Team { get; init; } = string.Empty;
    public int Matches { get; init; }
    public int Wins { get; init; }
    public int Draws { get; init; }
    public int Losses { get; init; }
    public int GoalsFor { get; init; }
    public int GoalsAgainst { get; init; }
    public int Points => Wins * 3 + Draws;
    public double WinRate => Matches > 0 ? Math.Round((double)Wins / Matches * 100, 1) : 0;
    public double GoalsPerMatch => Matches > 0 ? Math.Round((double)GoalsFor / Matches, 2) : 0;

    public static TeamStats operator +(TeamStats a, TeamStats b) => new()
    {
        Team = a.Team,
        Matches = a.Matches + b.Matches,
        Wins = a.Wins + b.Wins,
        Draws = a.Draws + b.Draws,
        Losses = a.Losses + b.Losses,
        GoalsFor = a.GoalsFor + b.GoalsFor,
        GoalsAgainst = a.GoalsAgainst + b.GoalsAgainst,
    };
}
