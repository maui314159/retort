// =============================================================================
// Brazilian Soccer MCP Server
// File: PlayerRecord.cs
// Purpose: Canonical representation of a FIFA dataset player row.
// Context: The Kaggle FIFA file has 70+ columns; we keep the ones that answer
//          the most common natural-language questions (rating, club,
//          nationality, position) plus jersey number for context. Numeric
//          ratings are int to match the dataset; missing values are null.
// =============================================================================

namespace BrazilianSoccerMcp.Core.Models;

/// <summary>
/// Canonical FIFA player record. Only the fields that drive the supported
/// queries are retained -- the FIFA CSV has 70+ columns we intentionally
/// ignore because no documented query path needs them.
/// </summary>
public sealed record PlayerRecord
{
    public required int Id { get; init; }
    public required string Name { get; init; }
    public int? Age { get; init; }
    public string? Photo { get; init; }
    public string? Nationality { get; init; }
    public int? Overall { get; init; }
    public int? Potential { get; init; }
    public string? Club { get; init; }
    public int? JerseyNumber { get; init; }
    public string? Value { get; init; }     // raw string, e.g. "€110.5M"
    public string? Wage { get; init; }
    public string? PreferredFoot { get; init; }
    public string? InternationalReputation { get; init; }
    public string? WeakFoot { get; init; }
    public string? SkillMoves { get; init; }
    public string? WorkRate { get; init; }
    public string? BodyType { get; init; }
    public string? RealFace { get; init; }
    public string? Position { get; init; }
    public string? Joined { get; init; }
    public string? LoanedFrom { get; init; }
    public string? ContractValidUntil { get; init; }
    public string? Height { get; init; }
    public string? Weight { get; init; }
    public int? Crossing { get; init; }
    public int? Finishing { get; init; }
    public int? HeadingAccuracy { get; init; }
    public int? ShortPassing { get; init; }
    public int? Volleys { get; init; }
    public int? Dribbling { get; init; }
    public int? Curve { get; init; }
    public int? FKAccuracy { get; init; }
    public int? LongPassing { get; init; }
    public int? BallControl { get; init; }
    public int? Acceleration { get; init; }
    public int? SprintSpeed { get; init; }
    public int? Agility { get; init; }
    public int? Reactions { get; init; }
    public int? Balance { get; init; }
    public int? ShotPower { get; init; }
    public int? Jumping { get; init; }
    public int? Stamina { get; init; }
    public int? Strength { get; init; }
    public int? LongShots { get; init; }
    public int? Aggression { get; init; }
    public int? Interceptions { get; init; }
    public int? Positioning { get; init; }
    public int? Vision { get; init; }
    public int? Penalties { get; init; }
    public int? Composure { get; init; }
    public int? Marking { get; init; }
    public int? StandingTackle { get; init; }
    public int? SlidingTackle { get; init; }
    public int? GKDiving { get; init; }
    public int? GKHandling { get; init; }
    public int? GKKicking { get; init; }
    public int? GKPositioning { get; init; }
    public int? GKReflexes { get; init; }
    public string? ReleaseClause { get; init; }
}
