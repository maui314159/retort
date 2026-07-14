// Brazilian Soccer MCP Server - Player model
// Context: Projection of the FIFA player database (fifa_data.csv). The raw CSV
// ships ~80 columns including per-position skill ratings encoded as "88+2";
// only the columns needed to answer the spec's player queries (identity,
// nationality, club, ratings, position, physicals) are parsed and exposed here.
// Numeric ratings are parsed defensively because the source mixes integers and
// "n+m" growth strings.

namespace BrazilianSoccerMcp.Models;

/// <summary>A FIFA-database player record.</summary>
public sealed class Player
{
    public int Id { get; init; }
    public required string Name { get; init; }
    public int Age { get; init; }
    public required string Nationality { get; init; }
    public int Overall { get; init; }
    public int Potential { get; init; }
    public string? Club { get; init; }
    public string? Position { get; init; }
    public int? JerseyNumber { get; init; }
    public string? PreferredFoot { get; init; }
    public string? Height { get; init; }
    public string? Weight { get; init; }
    public string? Value { get; init; }
    public string? Wage { get; init; }

    /// <summary>Canonical (normalised) club key, or null for unattached players.</summary>
    public string? ClubKey { get; init; }
}
