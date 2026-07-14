using CsvHelper.Configuration.Attributes;

namespace BrazilianSoccerMCP.Models;

public record ExtendedMatch
{
    [Name("tournament")]
    public string Tournament { get; init; } = "";

    [Name("home")]
    public string Home { get; init; } = "";

    [Name("home_goal")]
    public double HomeGoal { get; init; }

    [Name("away_goal")]
    public double AwayGoal { get; init; }

    [Name("away")]
    public string Away { get; init; } = "";

    [Name("home_corner")]
    public double HomeCorner { get; init; }

    [Name("away_corner")]
    public double AwayCorner { get; init; }

    [Name("home_attack")]
    public double? HomeAttack { get; init; }

    [Name("away_attack")]
    public double? AwayAttack { get; init; }

    [Name("home_shots")]
    public double? HomeShots { get; init; }

    [Name("away_shots")]
    public double? AwayShots { get; init; }

    [Name("time")]
    public string Time { get; init; } = "";

    [Name("date")]
    public string Date { get; init; } = "";

    [Name("ht_diff")]
    public double? HtDiff { get; init; }

    [Name("at_diff")]
    public double? AtDiff { get; init; }

    [Name("ht_result")]
    public string HtResult { get; init; } = "";

    [Name("at_result")]
    public string AtResult { get; init; } = "";

    [Name("total_corners")]
    public double TotalCorners { get; init; }
}