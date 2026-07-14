namespace BrazilianSoccerMcp.Models;

public enum Competition
{
    Brasileirao,
    CopaDoBrasil,
    Libertadores,
    BrFootball,
    HistoricoBrasileiro,
}

public sealed record Match(
    DateOnly Date,
    string HomeTeam,
    string AwayTeam,
    int HomeGoals,
    int AwayGoals,
    int Season,
    Competition Competition,
    string? Round = null,
    string? Stage = null,
    string? Stadium = null)
{
    public int GoalDifference => Math.Abs(HomeGoals - AwayGoals);
    public bool IsHomeWin => HomeGoals > AwayGoals;
    public bool IsAwayWin => AwayGoals > HomeGoals;
    public bool IsDraw => HomeGoals == AwayGoals;

    public string CompetitionLabel => Competition switch
    {
        Competition.Brasileirao => "Brasileirão",
        Competition.CopaDoBrasil => "Copa do Brasil",
        Competition.Libertadores => "Copa Libertadores",
        Competition.BrFootball => "BR Football",
        Competition.HistoricoBrasileiro => "Brasileirão (Historic)",
        _ => Competition.ToString(),
    };
}
