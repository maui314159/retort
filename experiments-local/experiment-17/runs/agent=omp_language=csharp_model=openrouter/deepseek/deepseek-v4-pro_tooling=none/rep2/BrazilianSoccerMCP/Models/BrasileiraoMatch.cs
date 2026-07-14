using CsvHelper.Configuration.Attributes;

namespace BrazilianSoccerMCP.Models;

public record BrasileiraoMatch
{
    [Name("datetime")]
    public string Datetime { get; init; } = "";

    [Name("home_team")]
    public string HomeTeam { get; init; } = "";

    [Name("home_team_state")]
    public string HomeTeamState { get; init; } = "";

    [Name("away_team")]
    public string AwayTeam { get; init; } = "";

    [Name("away_team_state")]
    public string AwayTeamState { get; init; } = "";

    [Name("home_goal")]
    public int? HomeGoal { get; init; }

    [Name("away_goal")]
    public int? AwayGoal { get; init; }

    [Name("season")]
    public int Season { get; init; }

    [Name("round")]
    public int Round { get; init; }
}