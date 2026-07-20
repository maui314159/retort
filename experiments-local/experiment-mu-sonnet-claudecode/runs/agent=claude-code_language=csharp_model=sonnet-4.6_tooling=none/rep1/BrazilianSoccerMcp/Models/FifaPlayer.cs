namespace BrazilianSoccerMcp.Models;

public record FifaPlayer(
    int FifaId,
    string Name,
    int Age,
    string Nationality,
    int Overall,
    int Potential,
    string Club,
    string Position,
    int? JerseyNumber
);
