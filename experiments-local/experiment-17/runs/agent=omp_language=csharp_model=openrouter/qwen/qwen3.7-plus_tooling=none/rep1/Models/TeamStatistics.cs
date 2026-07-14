namespace BrazilianSoccerMcp.Models;

public class TeamStatistics
{
    public string TeamName { get; set; } = "";
    public string Competition { get; set; } = "";
    public string Season { get; set; } = "";
    public int MatchesPlayed { get; set; }
    public int Wins { get; set; }
    public int Draws { get; set; }
    public int Losses { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }
    public int HomeMatches { get; set; }
    public int HomeWins { get; set; }
    public int HomeDraws { get; set; }
    public int HomeLosses { get; set; }
    public int AwayMatches { get; set; }
    public int AwayWins { get; set; }
    public int AwayDraws { get; set; }
    public int AwayLosses { get; set; }

    public double WinRate => MatchesPlayed > 0 ? (double)Wins / MatchesPlayed * 100 : 0;
    public double GoalDifference => GoalsFor - GoalsAgainst;
}

public class HeadToHeadResult
{
    public string Team1 { get; set; } = "";
    public string Team2 { get; set; } = "";
    public int Team1Wins { get; set; }
    public int Team2Wins { get; set; }
    public int Draws { get; set; }
    public int TotalMatches { get; set; }
    public int Team1Goals { get; set; }
    public int Team2Goals { get; set; }
    public List<MatchRecord> RecentMatches { get; set; } = new();
}

public class CompetitionStanding
{
    public string TeamName { get; set; } = "";
    public int MatchesPlayed { get; set; }
    public int Wins { get; set; }
    public int Draws { get; set; }
    public int Losses { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }
    public int Points => Wins * 3 + Draws;
    public double GoalDifference => GoalsFor - GoalsAgainst;
}
