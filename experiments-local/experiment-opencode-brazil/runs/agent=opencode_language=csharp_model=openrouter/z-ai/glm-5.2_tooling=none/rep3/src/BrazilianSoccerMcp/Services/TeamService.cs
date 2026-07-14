using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Services;

/// <summary>
/// Aggregates match results into team-level statistics: wins/draws/losses,
/// goals scored/conceded, home vs away splits and per-competition breakdowns.
/// </summary>
public sealed class TeamService
{
    private readonly IReadOnlyList<MatchRecord> _matches;

    public TeamService(DataRepository repo)
    {
        _matches = repo.Matches;
    }

    public TeamStats GetStats(string team, int? season = null, string? competition = null, string? venue = null)
    {
        var key = TeamNameNormalizer.NormalizeKey(team);
        var compKey = (competition ?? "").Trim();
        bool compFilter = !string.IsNullOrEmpty(compKey);

        int wins = 0, draws = 0, losses = 0;
        int goalsFor = 0, goalsAgainst = 0;
        int homeMatches = 0, awayMatches = 0;

        foreach (var m in _matches)
        {
            if (season.HasValue && m.Season != season.Value) continue;
            if (compFilter && !m.Competition.Contains(compKey, StringComparison.OrdinalIgnoreCase)) continue;

            var hk = TeamNameNormalizer.NormalizeKey(m.HomeTeam);
            var ak = TeamNameNormalizer.NormalizeKey(m.AwayTeam);
            bool isHome = hk == key;
            bool isAway = ak == key;
            if (!isHome && !isAway) continue;
            if (venue == "home" && !isHome) continue;
            if (venue == "away" && !isAway) continue;

            int gf = isHome ? m.HomeGoal : m.AwayGoal;
            int ga = isHome ? m.AwayGoal : m.HomeGoal;
            goalsFor += gf;
            goalsAgainst += ga;
            if (isHome) homeMatches++; else awayMatches++;

            if (gf > ga) wins++;
            else if (gf < ga) losses++;
            else draws++;
        }

        int total = wins + draws + losses;
        double winRate = total > 0 ? (double)wins / total * 100.0 : 0;
        return new TeamStats(team, season, competition, venue,
            total, wins, draws, losses, goalsFor, goalsAgainst, homeMatches, awayMatches, winRate);
    }

    /// <summary>Returns team display names matching the supplied prefix/substring.</summary>
    public IReadOnlyList<string> SearchTeams(string query, int limit = 25)
    {
        var qKey = TeamNameNormalizer.NormalizeKey(query);
        var seen = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var m in _matches)
        {
            foreach (var name in new[] { m.HomeTeam, m.AwayTeam })
            {
                if (string.IsNullOrEmpty(name)) continue;
                var nk = TeamNameNormalizer.NormalizeKey(name);
                if (nk.Contains(qKey, StringComparison.OrdinalIgnoreCase))
                {
                    seen.TryAdd(name, name);
                }
            }
        }
        return seen.Values.OrderBy(v => v).Take(limit).ToList();
    }
}

public sealed record TeamStats(
    string Team,
    int? Season,
    string? Competition,
    string? Venue,
    int Matches,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst,
    int HomeMatches,
    int AwayMatches,
    double WinRatePercent);
