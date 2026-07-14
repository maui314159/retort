namespace BrazilianSoccerMcp.Server.Models;

public sealed record MatchRecord(
    string Competition,
    DateTime? Date,
    string HomeTeam,
    string AwayTeam,
    int HomeGoals,
    int AwayGoals,
    int? Season,
    string? Round,
    string? Stage,
    string? Stadium,
    string SourceFile)
{
    public string Result => HomeGoals switch
    {
        _ when HomeGoals > AwayGoals => "home",
        _ when HomeGoals < AwayGoals => "away",
        _ => "draw"
    };

    public bool InvolvesTeam(string team) =>
        TeamMatches(HomeTeam, team) || TeamMatches(AwayTeam, team);

    public bool IsBetween(string teamA, string teamB) =>
        (TeamMatches(HomeTeam, teamA) && TeamMatches(AwayTeam, teamB)) ||
        (TeamMatches(HomeTeam, teamB) && TeamMatches(AwayTeam, teamA));

    private static bool TeamMatches(string actual, string query) =>
        TeamNameNormalizer.Normalize(actual)
            .Contains(TeamNameNormalizer.Normalize(query), StringComparison.OrdinalIgnoreCase) ||
        TeamNameNormalizer.Normalize(query)
            .Contains(TeamNameNormalizer.Normalize(actual), StringComparison.OrdinalIgnoreCase);
}
