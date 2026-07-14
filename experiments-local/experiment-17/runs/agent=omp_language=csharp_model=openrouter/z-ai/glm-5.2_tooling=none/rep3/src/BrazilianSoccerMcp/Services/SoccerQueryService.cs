// Brazilian Soccer MCP Server - Query service
// Context: The pure-logic brain of the server. It owns the loaded datasets and
// exposes structured query methods covering the five capability groups in the
// spec: match queries, team queries, player queries, competition (standings)
// queries, and statistical analysis. The MCP tool layer (SoccerTools) calls
// these methods and renders the results into the formatted text blocks the spec
// shows; tests call them directly to assert behaviour without coupling to the
// rendered strings.
//
// Design notes:
// - Team inputs are normalised through TeamNormalizer so "Flamengo",
//   "Flamengo-RJ" and "flamengo" all resolve to the same canonical key.
// - Competition filters are parsed loosely from free text ("brasileirão",
//   "copa do brasil", "libertadores", "all") so LLM callers don't need to know
//   the enum.
// - Standings for "Brasileirão" auto-route to the historical bucket for
//   seasons 2003-2011 (modern Serie A bucket only covers 2012-2022) so a
//   single competition name answers both eras.

using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Services;

/// <summary>Filter specification for match searches.</summary>
public sealed class MatchFilter
{
    public string? Team { get; init; }
    public string? Opponent { get; init; }
    public Competition? Competition { get; init; }
    public int? Season { get; init; }
    public DateOnly? From { get; init; }
    public DateOnly? To { get; init; }
    public int? Limit { get; init; }
}

/// <summary>Filter specification for player searches.</summary>
public sealed class PlayerFilter
{
    public string? Name { get; init; }
    public string? Nationality { get; init; }
    public string? Club { get; init; }
    public string? Position { get; init; }
    public int? MinOverall { get; init; }
    public int? Limit { get; init; }
    public string? SortBy { get; init; } // "overall" (default), "potential", "age", "name"
}

public enum Venue { All, Home, Away }

/// <summary>Aggregated head-to-head summary between two teams.</summary>
public sealed record HeadToHeadResult(
    string Team1, string Team2,
    int Team1Wins, int Team2Wins, int Draws,
    IReadOnlyList<Match> Matches);

/// <summary>Goal-distribution analysis over a set of matches.</summary>
public sealed record GoalsAnalysis(
    int Matches, double AvgGoals, double AvgHomeGoals, double AvgAwayGoals,
    double HomeWinRate, double AwayWinRate, double DrawRate);

/// <summary>Core query API over the loaded soccer datasets.</summary>
public sealed class SoccerQueryService
{
    private readonly SoccerDataLoader _loader;

    public SoccerQueryService(SoccerDataLoader loader) => _loader = loader;

    public SoccerQueryService(string? dataDirectory = null)
        => _loader = new SoccerDataLoader(dataDirectory ?? DataLocator.FindDataDirectory());

    public IReadOnlyList<Match> AllMatches => _loader.Matches;
    public IReadOnlyList<Player> AllPlayers => _loader.Players;

    // ---------------------------------------------------------------------
    // Match queries
    // ---------------------------------------------------------------------

    /// <summary>Finds matches matching the given filter, newest first.</summary>
    public IReadOnlyList<Match> FindMatches(MatchFilter filter)
    {
        string? teamKey = filter.Team is null ? null : TeamNormalizer.Normalize(filter.Team);
        string? oppKey = filter.Opponent is null ? null : TeamNormalizer.Normalize(filter.Opponent);

        var query = _loader.Matches.AsEnumerable();

        if (teamKey is { Length: > 0 })
            query = query.Where(m => m.HomeTeamKey == teamKey || m.AwayTeamKey == teamKey);

        if (oppKey is { Length: > 0 })
            query = query.Where(m => m.HomeTeamKey == oppKey || m.AwayTeamKey == oppKey);

        // When both team and opponent are given, require both to be involved.
        if (teamKey is { Length: > 0 } && oppKey is { Length: > 0 })
            query = query.Where(m =>
                (m.HomeTeamKey == teamKey && m.AwayTeamKey == oppKey) ||
                (m.HomeTeamKey == oppKey && m.AwayTeamKey == teamKey));

        if (filter.Competition.HasValue)
            query = query.Where(m => m.Competition == filter.Competition.Value);

        if (filter.Season.HasValue)
            query = query.Where(m => m.Season == filter.Season.Value);

        if (filter.From.HasValue)
            query = query.Where(m => m.Date >= filter.From.Value);

        if (filter.To.HasValue)
            query = query.Where(m => m.Date <= filter.To.Value);

        var ordered = query.OrderByDescending(m => m.Date ?? DateOnly.MinValue)
                           .ThenByDescending(m => m.Season ?? 0);
        return filter.Limit.HasValue ? ordered.Take(filter.Limit.Value).ToList() : ordered.ToList();
    }

    /// <summary>Returns the most recent match involving the team (and opponent, if given).</summary>
    public Match? LastMatch(string team, string? opponent = null)
        => FindMatches(new MatchFilter { Team = team, Opponent = opponent, Limit = 1 }).FirstOrDefault();

    // ---------------------------------------------------------------------
    // Team queries
    // ---------------------------------------------------------------------

    /// <summary>Computes win/draw/loss and goal tallies for a team over a filter slice.</summary>
    public TeamStats ComputeTeamStats(string team, Competition? competition, int? season, Venue venue)
    {
        var teamKey = TeamNormalizer.Normalize(team);
        var matches = _loader.Matches.Where(m => m.HasScore &&
            (m.HomeTeamKey == teamKey || m.AwayTeamKey == teamKey) &&
            (!competition.HasValue || m.Competition == competition.Value) &&
            (!season.HasValue || m.Season == season.Value));

        int w = 0, d = 0, l = 0, gf = 0, ga = 0, count = 0;
        foreach (var m in matches)
        {
            bool isHome = m.HomeTeamKey == teamKey;
            if (venue == Venue.Home && !isHome) continue;
            if (venue == Venue.Away && isHome) continue;

            int myGoals = isHome ? m.HomeGoal : m.AwayGoal;
            int oppGoals = isHome ? m.AwayGoal : m.HomeGoal;
            gf += myGoals;
            ga += oppGoals;
            count++;
            if (myGoals > oppGoals) w++;
            else if (myGoals < oppGoals) l++;
            else d++;
        }

        return new TeamStats
        {
            TeamKey = teamKey,
            TeamName = TeamNormalizer.DisplayName(team),
            Matches = count, Wins = w, Draws = d, Losses = l,
            GoalsFor = gf, GoalsAgainst = ga,
        };
    }

    /// <summary>Head-to-head record between two teams.</summary>
    public HeadToHeadResult ComputeHeadToHead(string team1, string team2, Competition? competition, int? season)
    {
        var k1 = TeamNormalizer.Normalize(team1);
        var k2 = TeamNormalizer.Normalize(team2);
        var matches = _loader.Matches.Where(m => m.HasScore &&
            ((m.HomeTeamKey == k1 && m.AwayTeamKey == k2) ||
             (m.HomeTeamKey == k2 && m.AwayTeamKey == k1)) &&
            (!competition.HasValue || m.Competition == competition.Value) &&
            (!season.HasValue || m.Season == season.Value))
            .OrderByDescending(m => m.Date ?? DateOnly.MinValue)
            .ToList();

        int w1 = 0, w2 = 0, draws = 0;
        foreach (var m in matches)
        {
            bool t1Home = m.HomeTeamKey == k1;
            int g1 = t1Home ? m.HomeGoal : m.AwayGoal;
            int g2 = t1Home ? m.AwayGoal : m.HomeGoal;
            if (g1 > g2) w1++;
            else if (g1 < g2) w2++;
            else draws++;
        }

        return new HeadToHeadResult(
            TeamNormalizer.DisplayName(team1), TeamNormalizer.DisplayName(team2),
            w1, w2, draws, matches);
    }

    /// <summary>Lists the competitions a team has appeared in (with match counts).</summary>
    public IReadOnlyDictionary<Competition, (string Label, int Count)> TeamCompetitions(string team)
    {
        var teamKey = TeamNormalizer.Normalize(team);
        return _loader.Matches
            .Where(m => m.HomeTeamKey == teamKey || m.AwayTeamKey == teamKey)
            .GroupBy(m => m.Competition)
            .OrderByDescending(g => g.Count())
            .ToDictionary(g => g.Key, g => (g.First().CompetitionLabel, g.Count()));
    }

    // ---------------------------------------------------------------------
    // Competition queries
    // ---------------------------------------------------------------------

    /// <summary>Computes league standings (by points) for a competition+season.
    /// "Brasileirão" auto-routes to the historical bucket for seasons 2003-2011.</summary>
    public IReadOnlyList<TeamStats> ComputeStandings(string competition, int season)
    {
        var bucket = ResolveStandingsBucket(competition, season);
        var seasonMatches = _loader.Matches
            .Where(m => m.Competition == bucket && m.Season == season && m.HasScore);

        var byTeam = new Dictionary<string, TeamStats>(StringComparer.Ordinal);
        foreach (var m in seasonMatches)
            Accumulate(byTeam, m.HomeTeamKey, m.HomeGoal, m.AwayGoal, isHome: true);

        // Second pass for away side so each team's record aggregates both venues.
        foreach (var m in seasonMatches)
            Accumulate(byTeam, m.AwayTeamKey, m.AwayGoal, m.HomeGoal, isHome: false);

        return byTeam.Values
            .OrderByDescending(t => t.Points)
            .ThenByDescending(t => t.Wins)
            .ThenByDescending(t => t.GoalDifference)
            .ThenByDescending(t => t.GoalsFor)
            .ThenBy(t => t.TeamKey, StringComparer.Ordinal)
            .Select(t => t with { TeamName = t.TeamKey })
            .ToList();
    }

    private static void Accumulate(Dictionary<string, TeamStats> dict, string teamKey, int gf, int ga, bool isHome)
    {
        if (string.IsNullOrEmpty(teamKey)) return;
        if (!dict.TryGetValue(teamKey, out var stats))
        {
            stats = new TeamStats { TeamKey = teamKey, TeamName = teamKey };
            dict[teamKey] = stats;
        }
        // Records are immutable-init; rebuild accumulator.
        dict[teamKey] = stats with
        {
            Matches = stats.Matches + 1,
            Wins = stats.Wins + (gf > ga ? 1 : 0),
            Draws = stats.Draws + (gf == ga ? 1 : 0),
            Losses = stats.Losses + (gf < ga ? 1 : 0),
            GoalsFor = stats.GoalsFor + gf,
            GoalsAgainst = stats.GoalsAgainst + ga,
        };
    }

    private static Competition ResolveStandingsBucket(string competition, int season)
    {
        var c = ParseCompetition(competition);
        // "Brasileirão" modern bucket only covers 2012-2022; route older seasons
        // to the historical 2003-2019 dataset so the same competition name works
        // across the full era.
        if (c == Competition.Brasileirao && season < 2012)
            return Competition.BrasileiraoHistorico;
        return c ?? Competition.Brasileirao;
    }

    // ---------------------------------------------------------------------
    // Statistical analysis
    // ---------------------------------------------------------------------

    /// <summary>Biggest winning margins in the dataset, filtered optionally.</summary>
    public IReadOnlyList<Match> BiggestWins(Competition? competition, int? season, int limit)
    {
        var query = _loader.Matches.Where(m => m.HasScore && m.HomeGoal != m.AwayGoal);
        if (competition.HasValue) query = query.Where(m => m.Competition == competition.Value);
        if (season.HasValue) query = query.Where(m => m.Season == season.Value);
        return query.OrderByDescending(m => m.GoalDifference)
                    .ThenByDescending(m => m.TotalGoals)
                    .Take(limit)
                    .ToList();
    }

    /// <summary>Goal-distribution analysis over a (filtered) set of matches.</summary>
    public GoalsAnalysis ComputeGoalsAnalysis(Competition? competition, int? season)
    {
        var query = _loader.Matches.Where(m => m.HasScore);
        if (competition.HasValue) query = query.Where(m => m.Competition == competition.Value);
        if (season.HasValue) query = query.Where(m => m.Season == season.Value);

        int matches = 0, totalGoals = 0, homeGoals = 0, awayGoals = 0;
        int homeWins = 0, awayWins = 0, draws = 0;
        foreach (var m in query)
        {
            matches++;
            totalGoals += m.TotalGoals;
            homeGoals += m.HomeGoal;
            awayGoals += m.AwayGoal;
            if (m.HomeGoal > m.AwayGoal) homeWins++;
            else if (m.AwayGoal > m.HomeGoal) awayWins++;
            else draws++;
        }

        if (matches == 0)
            return new GoalsAnalysis(0, 0, 0, 0, 0, 0, 0);

        return new GoalsAnalysis(
            matches,
            (double)totalGoals / matches,
            (double)homeGoals / matches,
            (double)awayGoals / matches,
            (double)homeWins / matches,
            (double)awayWins / matches,
            (double)draws / matches);
    }

    // ---------------------------------------------------------------------
    // Player queries
    // ---------------------------------------------------------------------

    /// <summary>Finds players matching the given filter.</summary>
    public IReadOnlyList<Player> FindPlayers(PlayerFilter filter)
    {
        var query = _loader.Players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(filter.Name))
        {
            var name = filter.Name.Trim();
            query = query.Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));
        }
        if (!string.IsNullOrWhiteSpace(filter.Nationality))
        {
            var nat = filter.Nationality.Trim();
            query = query.Where(p => p.Nationality.Contains(nat, StringComparison.OrdinalIgnoreCase));
        }
        if (!string.IsNullOrWhiteSpace(filter.Club))
        {
            var clubKey = TeamNormalizer.Normalize(filter.Club);
            query = query.Where(p => p.ClubKey != null && p.ClubKey == clubKey);
        }
        if (!string.IsNullOrWhiteSpace(filter.Position))
        {
            var pos = filter.Position.Trim();
            query = query.Where(p => p.Position != null && p.Position.Contains(pos, StringComparison.OrdinalIgnoreCase));
        }
        if (filter.MinOverall.HasValue)
            query = query.Where(p => p.Overall >= filter.MinOverall.Value);

        query = (filter.SortBy?.ToLowerInvariant()) switch
        {
            "potential" => query.OrderByDescending(p => p.Potential).ThenBy(p => p.Name),
            "age" => query.OrderByDescending(p => p.Age).ThenBy(p => p.Name),
            "name" => query.OrderBy(p => p.Name),
            _ => query.OrderByDescending(p => p.Overall).ThenByDescending(p => p.Potential).ThenBy(p => p.Name),
        };

        return filter.Limit.HasValue ? query.Take(filter.Limit.Value).ToList() : query.ToList();
    }

    // ---------------------------------------------------------------------
    // Competition-name parsing
    // ---------------------------------------------------------------------

    /// <summary>Parses a free-text competition name into a canonical enum value.
    /// Returns null for "all"/empty (meaning: no filter).</summary>
    public static Competition? ParseCompetition(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return null;
        var t = text.Trim().ToLowerInvariant();
        if (t is "all" or "todos" or "todas" or "any")
            return null;
        if (t.Contains("libertadores"))
            return Competition.Libertadores;
        if (t.Contains("copa do brasil") || t.Contains("brazilian cup") || t == "copa")
            return Competition.CopaDoBrasil;
        if (t.Contains("histórico") || t.Contains("historico") || t.Contains("historical") || t.Contains("2003"))
            return Competition.BrasileiraoHistorico;
        if (t.Contains("brasileir") || t.Contains("série a") || t.Contains("serie a"))
            return Competition.Brasileirao;
        return null;
    }

    /// <summary>Resolves a team display name from any raw input variant.</summary>
    public string TeamDisplayName(string raw) => TeamNormalizer.DisplayName(raw);
}
