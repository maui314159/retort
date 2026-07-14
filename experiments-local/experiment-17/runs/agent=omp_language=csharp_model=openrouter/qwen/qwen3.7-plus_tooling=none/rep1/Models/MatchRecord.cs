namespace BrazilianSoccerMcp.Models;

public class MatchRecord
{
    public string Source { get; set; } = "";
    public string Competition { get; set; } = "";
    public DateTime? Date { get; set; }
    public string Season { get; set; } = "";
    public string Round { get; set; } = "";
    public string Stage { get; set; } = "";
    public string HomeTeam { get; set; } = "";
    public string AwayTeam { get; set; } = "";
    public int HomeGoals { get; set; }
    public int AwayGoals { get; set; }
    public string? HomeTeamState { get; set; }
    public string? AwayTeamState { get; set; }
    public int? HomeCorners { get; set; }
    public int? AwayCorners { get; set; }
    public int? HomeShots { get; set; }
    public int? AwayShots { get; set; }

    public string Result => HomeGoals > AwayGoals ? "Home Win" : AwayGoals > HomeGoals ? "Away Win" : "Draw";
}
