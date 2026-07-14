namespace BrazilianSoccerMCP.Models;

public class Match
{
    public DateTime Date { get; set; }
    public string HomeTeam { get; set; } = "";
    public string AwayTeam { get; set; } = "";
    public int HomeGoals { get; set; }
    public int AwayGoals { get; set; }
    public string Competition { get; set; } = "";
    public int Season { get; set; }
}
