namespace BrazilianSoccerMcp.Models;

/// <summary>
/// Unified match record normalised from all five CSV sources.
/// </summary>
public sealed record MatchRecord
{
    public DateTime Date { get; init; }
    public string HomeTeam { get; init; } = "";
    public string AwayTeam { get; init; } = "";
    public int HomeGoals { get; init; }
    public int AwayGoals { get; init; }
    /// <summary>Brasileirao | Copa do Brasil | Copa Libertadores | BR-Football</summary>
    public string Competition { get; init; } = "";
    public int Season { get; init; }
    /// <summary>Round number or descriptive name (e.g. "Quartas", "group stage").</summary>
    public string Round { get; init; } = "";
    public string? Arena { get; init; }

    /// <summary>
    /// Grouping key: accent-stripped, lowercased, state suffix kept.
    /// "Atletico-MG" → "atletico-mg", "Atletico-PR" → "atletico-pr".
    /// Use for standings tables so different state variants are kept separate.
    /// </summary>
    public string HomeTeamKey { get; init; } = "";
    public string AwayTeamKey { get; init; } = "";

    /// <summary>
    /// Search key: like the grouping key but state suffix stripped.
    /// "Flamengo-RJ" → "flamengo" = same as "Flamengo" → "flamengo".
    /// Use for user queries and cross-dataset deduplication.
    /// </summary>
    public string HomeTeamSearchKey { get; init; } = "";
    public string AwayTeamSearchKey { get; init; } = "";

    public int GoalDifference => Math.Abs(HomeGoals - AwayGoals);
    public string? WinningTeam => HomeGoals > AwayGoals ? HomeTeam
                                 : AwayGoals > HomeGoals ? AwayTeam
                                 : null;

    public bool IsHomeWin  => HomeGoals > AwayGoals;
    public bool IsAwayWin  => AwayGoals > HomeGoals;
    public bool IsDraw     => HomeGoals == AwayGoals;
}
