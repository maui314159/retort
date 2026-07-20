namespace BrazilianSoccerMcp.Models;

/// <summary>Player record from the FIFA player database CSV.</summary>
public sealed record PlayerRecord
{
    public required int Id { get; init; }
    public required string Name { get; init; }
    public int? Age { get; init; }
    public string? Nationality { get; init; }
    public int? Overall { get; init; }
    public int? Potential { get; init; }
    public string? Club { get; init; }
    public string? Position { get; init; }
    public int? JerseyNumber { get; init; }
    public string? Height { get; init; }
    public string? Weight { get; init; }

    public string Describe() =>
        $"{Name} - Overall: {Overall?.ToString() ?? "?"}, Position: {Position ?? "?"}, " +
        $"Club: {Club ?? "?"}, Nationality: {Nationality ?? "?"}";
}
