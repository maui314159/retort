// Context block
// File: Models/PlayerRecord.cs
// Purpose: Subset of the FIFA player database fields needed by the Brazilian Soccer MCP
// server. The full fifa_data.csv has 75+ columns; we only load the columns used by
// queries (name, age, nationality, overall, potential, club, position, jersey number,
// preferred foot) so loading 18k players stays fast. Skill rating columns that look like
// "88+2" are not loaded here but the loader exposes a helper to parse the leading
// numeric value when a query needs it.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

namespace BrazilianSoccerMcp.Models;

/// <summary>A trimmed FIFA player record.</summary>
public sealed record PlayerRecord
{
    public required int Id { get; init; }
    public required string Name { get; init; }
    public required int Age { get; init; }
    public required string Nationality { get; init; }
    public required int Overall { get; init; }
    public required int Potential { get; init; }
    public required string Club { get; init; }
    public required string Position { get; init; }
    public int? JerseyNumber { get; init; }
    public string? PreferredFoot { get; init; }

    /// <summary>Display string used by the formatter.</summary>
    public string Display =>
        $"{Name} - Overall: {Overall}, Position: {Position}, Club: {Club}" +
        (Nationality is null || Nationality.Length == 0 ? "" : $", Nationality: {Nationality}");
}
