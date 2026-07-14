namespace BrazilianSoccerMcpServer.Models;

public sealed record Player
{
    public int Id { get; init; }
    public string Name { get; init; } = string.Empty;
    public int Age { get; init; }
    public string Nationality { get; init; } = string.Empty;
    public int Overall { get; init; }
    public int Potential { get; init; }
    public string Club { get; init; } = string.Empty;
    public string Position { get; init; } = string.Empty;
    public string? JerseyNumber { get; init; }
    public string? Height { get; init; }
    public string? Weight { get; init; }
    public int? Crossing { get; init; }
    public int? Finishing { get; init; }
    public int? Dribbling { get; init; }
    public int? ShortPassing { get; init; }
}
