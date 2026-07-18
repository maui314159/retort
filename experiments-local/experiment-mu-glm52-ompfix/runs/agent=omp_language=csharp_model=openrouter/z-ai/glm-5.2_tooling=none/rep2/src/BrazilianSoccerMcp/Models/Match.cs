// ============================================================================
// BrazilianSoccerMcp - Models/Match.cs
//
// Context block:
//   Unified match record produced by SoccerDataStore from all five match CSV
//   datasets. Every loader normalizes its source columns onto this shape so
//   downstream query tools never branch on file origin for the core fields.
//
//   Key design notes:
//   - HomeTeam/AwayTeam hold the *canonical* (normalized) team key; the raw
//     label as printed in the source CSV is kept in HomeTeamRaw/AwayTeamRaw
//     for display and debugging.
//   - Goals are nullable: rows with unparseable scores are kept for fixture
//     presence but excluded from goal aggregates by the tool layer.
//   - Extended stats (corners/attacks/shots) are only populated by the
//     BR-Football loader and stay null otherwise.
// ============================================================================

namespace BrazilianSoccerMcp.Models;

/// <summary>Single normalized match across all loaded datasets.</summary>
public sealed class Match
{
    public Competition Competition { get; init; } = Competition.Unknown;

    /// <summary>Free-form tournament label as written in the source (BR-Football).</summary>
    public string? Tournament { get; init; }

    public DateTime? Date { get; init; }

    public int? Season { get; init; }

    /// <summary>Canonical normalized home team key (diacritics/state suffix removed).</summary>
    public string HomeTeam { get; init; } = string.Empty;

    /// <summary>Canonical normalized away team key.</summary>
    public string AwayTeam { get; init; } = string.Empty;

    /// <summary>Raw home team label exactly as printed in the CSV.</summary>
    public string HomeTeamRaw { get; init; } = string.Empty;

    /// <summary>Raw away team label exactly as printed in the CSV.</summary>
    public string AwayTeamRaw { get; init; } = string.Empty;

    public string? HomeState { get; init; }
    public string? AwayState { get; init; }

    public int? HomeGoals { get; init; }
    public int? AwayGoals { get; init; }

    public string? Round { get; init; }
    public string? Stage { get; init; }
    public string? Stadium { get; init; }

    // --- BR-Football extended match statistics (null when not available) ---
    public int? HomeCorners { get; init; }
    public int? AwayCorners { get; init; }
    public int? HomeAttacks { get; init; }
    public int? AwayAttacks { get; init; }
    public int? HomeShots { get; init; }
    public int? AwayShots { get; init; }

    /// <summary>True when both teams' goals are known.</summary>
    public bool HasScore => HomeGoals.HasValue && AwayGoals.HasValue;

    /// <summary>Match outcome from the home team's perspective, or null if no score.</summary>
    public MatchOutcome? Outcome =>
        !HasScore ? null :
        HomeGoals > AwayGoals ? MatchOutcome.HomeWin :
        HomeGoals < AwayGoals ? MatchOutcome.AwayWin :
        MatchOutcome.Draw;
}

public enum MatchOutcome { HomeWin, AwayWin, Draw }
