namespace BrazilianSoccerMcp.Models;

/// <summary>
/// Unified match record across all match CSV sources.
/// Goals are nullable because some sources contain unplayed/NA fixtures.
/// </summary>
public sealed record MatchRecord
{
    public required DateOnly? Date { get; init; }
    public required int? Season { get; init; }

    /// <summary>Canonical competition name, e.g. "Brasileirão Série A".</summary>
    public required string Competition { get; init; }

    /// <summary>Short file-source identifier, e.g. "Brasileirao_Matches".</summary>
    public required string Source { get; init; }

    /// <summary>Human friendly round/stage label, e.g. "Round 22", "Final", "Group stage".</summary>
    public string? Round { get; init; }

    public required string HomeTeam { get; init; }
    public required string AwayTeam { get; init; }

    /// <summary>Canonical (normalized display) team names used for matching.</summary>
    public required string HomeTeamCanonical { get; init; }
    public required string AwayTeamCanonical { get; init; }

    public required int? HomeGoals { get; init; }
    public required int? AwayGoals { get; init; }

    public string? Stadium { get; init; }

    // Extended statistics (only present for BR-Football-Dataset rows).
    public int? HomeCorners { get; init; }
    public int? AwayCorners { get; init; }
    public int? HomeShots { get; init; }
    public int? AwayShots { get; init; }

    public bool Played => HomeGoals.HasValue && AwayGoals.HasValue;

    public MatchResult Result => !Played
        ? MatchResult.Unknown
        : HomeGoals > AwayGoals ? MatchResult.HomeWin
        : HomeGoals < AwayGoals ? MatchResult.AwayWin
        : MatchResult.Draw;

    public int GoalMargin => Played ? Math.Abs(HomeGoals!.Value - AwayGoals!.Value) : 0;
    public int TotalGoals => Played ? HomeGoals!.Value + AwayGoals!.Value : 0;

    public string ScoreText => Played ? $"{HomeGoals}-{AwayGoals}" : "vs (not played / n/a)";

    public string Describe() =>
        $"{Date?.ToString("yyyy-MM-dd") ?? "????-??-??"}: {HomeTeamCanonical} {ScoreText} {AwayTeamCanonical}" +
        $" ({Competition}{(Round is null ? "" : $", {Round}")})";
}

public enum MatchResult { Unknown, HomeWin, Draw, AwayWin }
