// BrazilianSoccerMcp.Core / Models / Player.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. Source: data/kaggle/fifa_data.csv
// (18,207 players, FIFA-19-style attributes, Apache 2.0 license).
// Purpose: Capture the subset of FIFA player columns needed to answer the player
// queries in TASK.md (search by name, nationality, club, position, rating).
// Design notes:
//   * The source CSV has an unnamed leading index column and many rating columns
//     formatted as "88+2". We only model the columns queries rely on, and parse
//     the "+"-suffixed ratings by taking the base value before the plus sign so
//     downstream sorting is stable.
//   * Height/Weight are strings ("5'7", "159lbs") preserved verbatim because the
//     spec lists them as physical attributes but no query parses them numerically.
// -----------------------------------------------------------------------------

namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// Subset of FIFA player attributes loaded for query purposes.
/// Rating columns that can appear as "88+2" are reduced to their base integer.
/// </summary>
public sealed class Player
{
    public int Id { get; set; }

    public string Name { get; set; } = string.Empty;

    public int? Age { get; set; }

    public string? Nationality { get; set; }

    /// <summary>FIFA overall rating (base value when source has "+N" form).</summary>
    public int Overall { get; set; }

    /// <summary>FIFA potential rating.</summary>
    public int? Potential { get; set; }

    public string? Club { get; set; }

    public string? Position { get; set; }

    public int? JerseyNumber { get; set; }

    public string? PreferredFoot { get; set; }

    public string? Height { get; set; }

    public string? Weight { get; set; }

    // Selected skill ratings (base integer of "88+2" form).
    public int? Crossing { get; set; }
    public int? Finishing { get; set; }
    public int? Dribbling { get; set; }
    public int? ShortPassing { get; set; }
    public int? LongPassing { get; set; }
    public int? ShotPower { get; set; }
    public int? StandingTackle { get; set; }
    public int? SlidingTackle { get; set; }

    public bool IsBrazilian =>
        Nationality is not null &&
        Nationality.Trim().Equals("Brazil", StringComparison.OrdinalIgnoreCase);
}
