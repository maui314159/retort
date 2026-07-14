namespace BrazilianSoccerMcp.Models;

public sealed record TeamStats(
    string Team,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst)
{
    public int Matches => Wins + Draws + Losses;
    public int Points => Wins * 3 + Draws;
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public double WinRate => Matches == 0 ? 0 : (double)Wins / Matches * 100;
}
