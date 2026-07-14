namespace BrazilianSoccerMcp.Server.Models;

public sealed record PlayerRecord(
    int Id,
    string Name,
    int? Age,
    string Nationality,
    int? Overall,
    int? Potential,
    string Club,
    string Position,
    int? JerseyNumber,
    string? Height,
    string? Weight);
