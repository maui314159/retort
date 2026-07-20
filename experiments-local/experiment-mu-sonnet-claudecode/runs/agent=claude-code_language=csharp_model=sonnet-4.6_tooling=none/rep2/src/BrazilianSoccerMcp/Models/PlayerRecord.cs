namespace BrazilianSoccerMcp.Models;

public record PlayerRecord
{
    public int? Id { get; init; }
    public string Name { get; init; } = "";
    public int? Age { get; init; }
    public string Nationality { get; init; } = "";
    public int? Overall { get; init; }
    public int? Potential { get; init; }
    public string Club { get; init; } = "";
    public string Position { get; init; } = "";
    public string? PreferredFoot { get; init; }
    public int? JerseyNumber { get; init; }
    public string? Height { get; init; }
    public string? Weight { get; init; }
    public int? Crossing { get; init; }
    public int? Finishing { get; init; }
    public int? Dribbling { get; init; }
    public int? ShortPassing { get; init; }
    public int? Acceleration { get; init; }
    public int? SprintSpeed { get; init; }
    public int? Stamina { get; init; }
    public int? Strength { get; init; }
    public int? GkDiving { get; init; }
    public int? GkHandling { get; init; }
    public int? GkReflexes { get; init; }
    public int? SkillMoves { get; init; }
    public int? WeakFoot { get; init; }
}
