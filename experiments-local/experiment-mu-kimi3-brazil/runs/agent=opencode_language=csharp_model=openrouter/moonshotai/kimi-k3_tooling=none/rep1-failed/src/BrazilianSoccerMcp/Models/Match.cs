namespace BrazilianSoccerMcp.Models;

/// <summary>
/// Unified match record normalized from any of the 5 match CSV files.
/// </summary>
public sealed record Match
{
    /// <summary>Competition name, e.g. "Brasileirão Série A", "Copa do Brasil", "Copa Libertadores".</summary>
    public required string Competition { get; init; }

    /// <summary>Match date (time component when available). Null when unparseable.</summary>
    public DateTime? Date { get; init; }

    /// <summary>Season year (e.g. 2023). Null when unknown.</summary>
    public int? Season { get; init; }

    /// <summary>Round / stage label (e.g. "8", "Final", "group stage").</summary>
    public string? Round { get; init; }

    /// <summary>Home team as written in the source file.</summary>
    public required string HomeTeam { get; init; }

    /// <summary>Away team as written in the source file.</summary>
    public required string AwayTeam { get; init; }

    /// <summary>Normalized home team name (diacritics removed, state suffix stripped, lower-cased).</summary>
    public required string HomeTeamKey { get; init; }

    /// <summary>Normalized away team name.</summary>
    public required string AwayTeamKey { get; init; }

    public int HomeGoals { get; init; }
    public int AwayGoals { get; init; }

    /// <summary>Source CSV file name (for provenance / debugging).</summary>
    public required string Source { get; init; }

    public string Result => HomeGoals > AwayGoals ? "home" : HomeGoals < AwayGoals ? "away" : "draw";

    public int GoalMargin => Math.Abs(HomeGoals - AwayGoals);

    public int TotalGoals => HomeGoals + AwayGoals;

    public override string ToString()
    {
        var date = Date?.ToString("yyyy-MM-dd") ?? "unknown-date";
        var round = string.IsNullOrWhiteSpace(Round) ? "" : $" ({Competition} {Round})";
        return $"{date}: {HomeTeam} {HomeGoals}-{AwayGoals} {AwayTeam}{round}";
    }
}
