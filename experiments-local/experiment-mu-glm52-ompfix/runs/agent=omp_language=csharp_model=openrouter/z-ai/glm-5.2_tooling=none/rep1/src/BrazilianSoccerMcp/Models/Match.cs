// Brazilian Soccer MCP Server - Match model
//
// Context: Unified representation of a single soccer match, normalized from the
// five match-oriented CSV datasets (Brasileirao_Matches, Brazilian_Cup_Matches,
// Libertadores_Matches, BR-Football-Dataset, novo_campeonato_brasileiro).
// Team names are stored both in display form (state suffix stripped) and as a
// canonical key (accent/case/punctuation-insensitive) for reliable matching
// across datasets that spell team names differently.

namespace BrazilianSoccerMcp.Models;

/// <summary>
/// A single soccer match aggregated and normalized from the provided datasets.
/// </summary>
public sealed class Match
{
    /// <summary>Human-readable competition name, e.g. "Brasileirão", "Copa do Brasil".</summary>
    public string Competition { get; set; } = string.Empty;

    /// <summary>Source file the record was loaded from.</summary>
    public string Source { get; set; } = string.Empty;

    /// <summary>Home team display name with any state/country suffix removed.</summary>
    public string HomeTeam { get; set; } = string.Empty;

    /// <summary>Away team display name with any state/country suffix removed.</summary>
    public string AwayTeam { get; set; } = string.Empty;

    /// <summary>Canonical matching key for the home team.</summary>
    public string HomeTeamKey { get; set; } = string.Empty;

    /// <summary>Canonical matching key for the away team.</summary>
    public string AwayTeamKey { get; set; } = string.Empty;

    public int? HomeGoals { get; set; }
    public int? AwayGoals { get; set; }

    /// <summary>Parsed match date (null when the source date was unparseable/missing).</summary>
    public DateTime? Date { get; set; }

    public int? Season { get; set; }

    public string? Round { get; set; }
    public string? Stage { get; set; }
    public string? Arena { get; set; }
    public string? HomeState { get; set; }
    public string? AwayState { get; set; }

    // Extended statistics only present in BR-Football-Dataset.csv.
    public int? HomeCorners { get; set; }
    public int? AwayCorners { get; set; }
    public int? HomeShots { get; set; }
    public int? AwayShots { get; set; }
    public int? HomeAttacks { get; set; }
    public int? AwayAttacks { get; set; }

    /// <summary>True when both goal values are present and the home team outscored the away team.</summary>
    public bool HomeWin => HomeGoals.HasValue && AwayGoals.HasValue && HomeGoals > AwayGoals;

    /// <summary>True when both goal values are present and equal.</summary>
    public bool Draw => HomeGoals.HasValue && AwayGoals.HasValue && HomeGoals == AwayGoals;

    /// <summary>True when both goal values are present and the away team outscored the home team.</summary>
    public bool AwayWin => HomeGoals.HasValue && AwayGoals.HasValue && HomeGoals < AwayGoals;

    /// <summary>Total goals scored in the match, or null when scores are missing.</summary>
    public int? TotalGoals => (HomeGoals.HasValue && AwayGoals.HasValue) ? HomeGoals + AwayGoals : null;

    /// <summary>The absolute goal difference, or null when scores are missing.</summary>
    public int? GoalDifference => (HomeGoals.HasValue && AwayGoals.HasValue) ? Math.Abs(HomeGoals.Value - AwayGoals.Value) : null;

    /// <summary>One-line summary used by the formatted tool output.</summary>
    public string Summary
    {
        get
        {
            var date = Date?.ToString("yyyy-MM-dd") ?? "unknown date";
            var score = (HomeGoals.HasValue && AwayGoals.HasValue)
                ? $"{HomeGoals}-{AwayGoals}"
                : "?-?";
            var detail = !string.IsNullOrWhiteSpace(Stage)
                ? $" ({Competition}, {Stage})"
                : !string.IsNullOrWhiteSpace(Round)
                    ? $" ({Competition}, Round {Round})"
                    : $" ({Competition})";
            return $"{date}: {HomeTeam} {score} {AwayTeam}{detail}";
        }
    }
}
