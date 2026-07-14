namespace BrazilianSoccerMcpServer.Models;

public sealed record Player
{
    public int Id { get; init; }
    public required string Name { get; init; }
    public int? Age { get; init; }
    public required string Nationality { get; init; }
    public int? Overall { get; init; }
    public int? Potential { get; init; }
    public string? Club { get; init; }
    public string? Position { get; init; }
    public int? JerseyNumber { get; init; }
    public string? Height { get; init; }
    public string? Weight { get; init; }

    public string FormatShort()
    {
        var club = string.IsNullOrWhiteSpace(Club) ? "No club" : Club;
        return $"{Name} - Overall: {Overall}, Position: {Position}, Club: {club}, Nationality: {Nationality}";
    }
}
