namespace BrazilianSoccerCore.Models;

/// <summary>
/// FIFA player record. Only the columns relevant to the required queries are retained;
/// the full skill-rating columns are kept as a dictionary for completeness.
/// </summary>
public sealed class Player
{
    public int Id { get; init; }
    public string Name { get; init; } = string.Empty;
    public int Age { get; init; }
    public string Nationality { get; init; } = string.Empty;
    public int Overall { get; init; }
    public int Potential { get; init; }
    public string Club { get; init; } = string.Empty;
    public string Position { get; init; } = string.Empty;
    public int? JerseyNumber { get; init; }
    public string Height { get; init; } = string.Empty;
    public string Weight { get; init; } = string.Empty;
    public string PreferredFoot { get; init; } = string.Empty;

    /// <summary>Selected skill ratings, keyed by their original CSV column name.</summary>
    public Dictionary<string, int?> Skills { get; init; } = new();
}