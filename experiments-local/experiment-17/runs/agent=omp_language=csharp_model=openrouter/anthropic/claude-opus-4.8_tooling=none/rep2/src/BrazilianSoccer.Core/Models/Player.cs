// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    Player.cs
// Project: BrazilianSoccer.Core
// Purpose: Player record loaded from fifa_data.csv. Only the columns relevant
//          to the spec's player queries (name, nationality, club, rating,
//          position, physical attributes) are surfaced; the wide skill-rating
//          columns are intentionally not modelled.
// =============================================================================

namespace BrazilianSoccer.Core.Models;

/// <summary>A FIFA-database player.</summary>
public sealed class Player
{
    public int Id { get; init; }
    public required string Name { get; init; }
    public int Age { get; init; }
    public required string Nationality { get; init; }
    public int Overall { get; init; }
    public int Potential { get; init; }
    public string Club { get; init; } = string.Empty;

    /// <summary>Normalised key of <see cref="Club"/> for club matching.</summary>
    public string ClubKey { get; init; } = string.Empty;
    public string Position { get; init; } = string.Empty;
    public int? JerseyNumber { get; init; }
    public string Height { get; init; } = string.Empty;
    public string Weight { get; init; } = string.Empty;
    public string PreferredFoot { get; init; } = string.Empty;

    public bool IsBrazilian =>
        string.Equals(Nationality, "Brazil", StringComparison.OrdinalIgnoreCase);
}
