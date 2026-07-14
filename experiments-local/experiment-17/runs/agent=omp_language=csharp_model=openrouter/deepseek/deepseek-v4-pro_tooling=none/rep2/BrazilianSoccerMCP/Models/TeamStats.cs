namespace BrazilianSoccerMCP.Models;

public class TeamStats
{
    public string TeamName { get; set; } = "";
    public int MatchesPlayed { get; set; }
    public int Wins { get; set; }
    public int Draws { get; set; }
    public int Losses { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }
    public HashSet<int> Seasons { get; set; } = [];
    public HashSet<string> Competitions { get; set; } = [];

    public int Points => Wins * 3 + Draws;

    public double WinRate => MatchesPlayed > 0 ? (double)Wins / MatchesPlayed : 0;

    public int GoalDifference => GoalsFor - GoalsAgainst;
}