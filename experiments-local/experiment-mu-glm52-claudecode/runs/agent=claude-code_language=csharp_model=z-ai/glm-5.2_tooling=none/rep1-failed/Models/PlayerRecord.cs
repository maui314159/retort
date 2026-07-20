// =============================================================================
// File: Models/PlayerRecord.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   A player record derived from fifa_data.csv. Only the columns that are
//   useful for the MCP query surface are retained; the 80+ skill-rating
//   columns are not materialised here (kept out of memory).
//
// Notes:
//   - fifa_data.csv ships with an unnamed leading index column; loaders read
//     fields positionally rather than by header name.
//   - ClubNormalized is the canonical key produced by TeamNameNormalizer so
//     that "FC Barcelona", "Barcelona", and "Barcelona-EQU" can be matched
//     against the match data when cross-referencing players with clubs.
// =============================================================================
namespace BrazilianSoccerMcp.Models;

/// <summary>A player record from the FIFA dataset.</summary>
public sealed class PlayerRecord
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public int? Age { get; set; }
    public string Nationality { get; set; } = "";
    public int? Overall { get; set; }
    public int? Potential { get; set; }
    public string Club { get; set; } = "";
    public string? Position { get; set; }
    public int? JerseyNumber { get; set; }
    public string? PreferredFoot { get; set; }
    public string? Value { get; set; }
    public string? Wage { get; set; }

    /// <summary>Canonical normalized club key (see TeamNameNormalizer).</summary>
    public string ClubNormalized { get; set; } = "";
}
