using CsvHelper.Configuration.Attributes;

namespace BrazilianSoccerMCP.Models;

public record CopaBrasilMatch
{
    [Name("round")]
    public string Round { get; init; } = "";

    [Name("datetime")]
    public string Datetime { get; init; } = "";

    [Name("home_team")]
    public string HomeTeam { get; init; } = "";

    [Name("away_team")]
    public string AwayTeam { get; init; } = "";

    [Name("home_goal")]
    public int? HomeGoal { get; init; }

    [Name("away_goal")]
    public int? AwayGoal { get; init; }

    [Name("season")]
    public int Season { get; init; }
}