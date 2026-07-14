namespace BrazilianSoccerMcp.Data;

/// <summary>Unified match record from any of the CSV sources.</summary>
public record Match(
    string Competition,
    DateTime Date,
    string HomeTeam,
    string AwayTeam,
    int HomeGoals,
    int AwayGoals,
    int? Season,
    string? Round,
    string? Stage
)
{
    public int GoalDifference => Math.Abs(HomeGoals - AwayGoals);

    public string? Winner =>
        HomeGoals > AwayGoals ? HomeTeam :
        AwayGoals > HomeGoals ? AwayTeam : null;

    public bool IsDraw => HomeGoals == AwayGoals;
}

public record Player(
    string FifaId,
    string Name,
    int Age,
    string Nationality,
    int Overall,
    int Potential,
    string Club,
    string Position,
    string? JerseyNumber,
    string? Height,
    string? Weight
);

public record Standing(
    int Rank,
    string Team,
    int Played,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst,
    int Points
)
{
    public int GoalDifference => GoalsFor - GoalsAgainst;
}

public record TeamStats(
    string Team,
    string? Competition,
    int? Season,
    bool HomeOnly,
    int Played,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst
)
{
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public double WinRate => Played == 0 ? 0 : Math.Round((double)Wins / Played * 100, 1);
}
