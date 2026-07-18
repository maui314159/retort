// ============================================================================
// BrazilianSoccerMcp - Models/Player.cs
//
// Context block:
//   Unified player record sourced from fifa_data.csv (FIFA 19 snapshot,
//   ~18k players). The FIFA CSV has ~70 skill columns; we capture the
//   identity/club/overview fields plus the most query-relevant attribute
//   ratings. Missing/empty cells become null rather than 0 so aggregates
//   can distinguish "not rated" from "rated 0".
//
//   Names in this dataset may be short forms ("L. Messi") or full names;
//   search is case/accent-insensitive substring match (see TeamNameNormalizer
//   for the shared diacritics helper).
// ============================================================================

namespace BrazilianSoccerMcp.Models;

/// <summary>A player from the FIFA dataset.</summary>
public sealed class Player
{
    public int Id { get; init; }
    public string Name { get; init; } = string.Empty;
    public int? Age { get; init; }
    public string? Nationality { get; init; }
    public int? Overall { get; init; }
    public int? Potential { get; init; }
    public string? Club { get; init; }
    public string? Position { get; init; }
    public int? JerseyNumber { get; init; }
    public string? PreferredFoot { get; init; }
    public string? Height { get; init; }
    public string? Weight { get; init; }
    public string? Value { get; init; }
    public string? Wage { get; init; }

    // Selected skill ratings (null when absent in source).
    public int? Crossing { get; init; }
    public int? Finishing { get; init; }
    public int? HeadingAccuracy { get; init; }
    public int? ShortPassing { get; init; }
    public int? Volleys { get; init; }
    public int? Dribbling { get; init; }
    public int? Curve { get; init; }
    public int? FkAccuracy { get; init; }
    public int? LongPassing { get; init; }
    public int? BallControl { get; init; }
    public int? Acceleration { get; init; }
    public int? SprintSpeed { get; init; }
    public int? ShotPower { get; init; }
    public int? Stamina { get; init; }
    public int? Strength { get; init; }
    public int? Aggression { get; init; }
    public int? Interceptions { get; init; }
    public int? Positioning { get; init; }
    public int? Vision { get; init; }
    public int? Penalties { get; init; }
    public int? Composure { get; init; }
    public int? Marking { get; init; }
    public int? StandingTackle { get; init; }
    public int? SlidingTackle { get; init; }
}
