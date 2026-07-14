using System.Globalization;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Unified match record normalised across all five match datasets.
/// </summary>
public sealed class MatchRecord
{
    public DateTime Date { get; init; }
    public int? Season { get; init; }
    public string Competition { get; init; } = string.Empty;
    public string HomeTeam { get; init; } = string.Empty;
    public string AwayTeam { get; init; } = string.Empty;
    public int HomeGoals { get; init; }
    public int AwayGoals { get; init; }
    public string? Round { get; init; }
    public string? Stage { get; init; }
    public string? HomeTeamState { get; init; }
    public string? AwayTeamState { get; init; }
    public string? Stadium { get; init; }

    // Extended stats from BR-Football-Dataset (nullable)
    public double? HomeCorners { get; init; }
    public double? AwayCorners { get; init; }
    public double? HomeShots { get; init; }
    public double? AwayShots { get; init; }
    public string? HalfTimeResult { get; init; }
    public string? FullTimeResult { get; init; }

    /// <summary>Match winner: "home", "away", or "draw".</summary>
    public string Winner => HomeGoals > AwayGoals ? "home" : AwayGoals > HomeGoals ? "away" : "draw";

    /// <summary>Absolute goal difference.</summary>
    public int GoalDifference => Math.Abs(HomeGoals - AwayGoals);

    public override string ToString() =>
        $"{Date:yyyy-MM-dd}: {HomeTeam} {HomeGoals}-{AwayGoals} {AwayTeam} ({Competition})";

    internal static DateTime ParseDate(string raw)
    {
        if (DateTime.TryParse(raw, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt))
            return dt;
        if (DateTime.TryParseExact(raw, "dd/MM/yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out dt))
            return dt;
        if (DateTime.TryParseExact(raw, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out dt))
            return dt;
        return DateTime.MinValue;
    }
}