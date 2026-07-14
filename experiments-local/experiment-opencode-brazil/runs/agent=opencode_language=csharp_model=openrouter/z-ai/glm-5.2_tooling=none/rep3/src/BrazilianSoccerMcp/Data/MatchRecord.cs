using System.Globalization;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Normalized representation of a single soccer match across all of the
/// provided CSV datasets. Every dataset has slightly different column names
/// and team name conventions, so the loaders normalize everything into this
/// single shape to make cross-file queries possible.
/// </summary>
public sealed class MatchRecord
{
    /// <summary>Source file / competition tag, e.g. "Brasileirao", "CopaDoBrasil".</summary>
    public required string Competition { get; set; }

    /// <summary>Parsed match date (date-only precision is enough for queries).</summary>
    public DateTime Date { get; set; }

    /// <summary>Normalized home team name (no state suffix, trimmed).</summary>
    public required string HomeTeam { get; set; }

    /// <summary>Normalized away team name.</summary>
    public required string AwayTeam { get; set; }

    /// <summary>Home team state abbreviation if known, otherwise empty.</summary>
    public string HomeState { get; set; } = string.Empty;

    /// <summary>Away team state abbreviation if known, otherwise empty.</summary>
    public string AwayState { get; set; } = string.Empty;

    /// <summary>Goals scored by the home team.</summary>
    public int HomeGoal { get; set; }

    /// <summary>Goals scored by the away team.</summary>
    public int AwayGoal { get; set; }

    /// <summary>Season year.</summary>
    public int Season { get; set; }

    /// <summary>Round / stage label as provided by the source file.</summary>
    public string Round { get; set; } = string.Empty;

    /// <summary>Original raw home team name as it appeared in the source CSV.</summary>
    public string RawHomeTeam { get; set; } = string.Empty;

    /// <summary>Original raw away team name as it appeared in the source CSV.</summary>
    public string RawAwayTeam { get; set; } = string.Empty;

    public override string ToString()
    {
        var d = Date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        return $"{d}: {HomeTeam} {HomeGoal}-{AwayGoal} {AwayTeam} ({Competition}{(string.IsNullOrEmpty(Round) ? "" : " " + Round)})";
    }
}
