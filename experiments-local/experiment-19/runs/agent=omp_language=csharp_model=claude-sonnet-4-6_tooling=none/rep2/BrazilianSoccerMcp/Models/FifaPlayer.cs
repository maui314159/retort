namespace BrazilianSoccerMcp.Models;

public sealed record FifaPlayer(
    int Id,
    string Name,
    int Age,
    string Nationality,
    int Overall,
    int Potential,
    string Club,
    string Position,
    string JerseyNumber,
    string Height,
    string Weight);
