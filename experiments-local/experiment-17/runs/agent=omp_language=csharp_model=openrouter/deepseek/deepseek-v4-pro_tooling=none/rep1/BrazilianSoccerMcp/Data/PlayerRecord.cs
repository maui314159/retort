namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Player record from the FIFA dataset, holding key fields for querying.
/// </summary>
public sealed class PlayerRecord
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
    public string PreferredFoot { get; init; } = string.Empty;
    public string? Height { get; init; }
    public string? Weight { get; init; }

    // Key skill ratings
    public int Crossing { get; init; }
    public int Finishing { get; init; }
    public int Dribbling { get; init; }
    public int Passing { get; init; }
    public int Pace { get; init; }
    public int Shooting { get; init; }
    public int Defending { get; init; }
    public int Physical { get; init; }

    public override string ToString() => $"{Name} (OVR: {Overall}, {Position}, {Club})";
}