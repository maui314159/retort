namespace BrazilianSoccerMcp.Models;

public class SoccerMatch
{
    public string Competition { get; set; } = string.Empty;
    public DateTime Date { get; set; }
    public string Season { get; set; } = string.Empty;
    public string Round { get; set; } = string.Empty;
    public string HomeTeam { get; set; } = string.Empty;
    public string AwayTeam { get; set; } = string.Empty;
    public int HomeGoals { get; set; }
    public int AwayGoals { get; set; }
    public string? Stage { get; set; }
    public string? Arena { get; set; }
    public int? HomeCorners { get; set; }
    public int? AwayCorners { get; set; }
    public string SourceFile { get; set; } = string.Empty;

    public string Result => HomeGoals > AwayGoals ? "Home Win" : 
                            AwayGoals > HomeGoals ? "Away Win" : "Draw";
}
