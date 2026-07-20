namespace BrazilianSoccerMcp.Models;

public record UnifiedMatch(
    DateTime? DateTime,
    string HomeTeam,
    string AwayTeam,
    int HomeGoal,
    int AwayGoal,
    int Season,
    string Competition,
    string? Round = null,
    string? Stage = null,
    string? Arena = null
);
