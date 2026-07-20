namespace BrazilianSoccerMcp.Models;

/// <summary>
/// FIFA player record from fifa_data.csv.
/// </summary>
public sealed record Player
{
    public required string Id { get; init; }
    public required string Name { get; init; }
    public int? Age { get; init; }
    public string? Nationality { get; init; }
    public int? Overall { get; init; }
    public int? Potential { get; init; }
    public string? Club { get; init; }
    public string? Position { get; init; }
    public string? PreferredFoot { get; init; }
    public int? JerseyNumber { get; init; }
    public string? Height { get; init; }
    public string? Weight { get; init; }

    // Selected skill ratings
    public int? Crossing { get; init; }
    public int? Finishing { get; init; }
    public int? Dribbling { get; init; }
    public int? ShortPassing { get; init; }
    public int? SprintSpeed { get; init; }

    public override string ToString()
    {
        var bits = new List<string>();
        if (Overall is { } o) bits.Add($"Overall: {o}");
        if (Position is { } p) bits.Add($"Position: {p}");
        if (Club is { } c) bits.Add($"Club: {c}");
        return $"{Name} - {string.Join(", ", bits)}";
    }
}
