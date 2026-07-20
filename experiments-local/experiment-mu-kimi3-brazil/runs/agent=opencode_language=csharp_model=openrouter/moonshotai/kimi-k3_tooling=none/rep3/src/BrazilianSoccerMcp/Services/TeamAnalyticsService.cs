using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Graph;

namespace BrazilianSoccerMcp.Services;

/// <summary>Aggregated statistics: team records, head-to-head, standings, extremes.</summary>
public sealed class TeamAnalyticsService
{
    private readonly KnowledgeGraph _graph;
    private readonly MatchQueryService _queries;

    public TeamAnalyticsService(KnowledgeGraph graph, MatchQueryService queries)
    {
        _graph = graph;
        _queries = queries;
    }

    public sealed record TeamRecord(
        string TeamDisplay, int Played, int Wins, int Draws, int Losses,
        int GoalsFor, int GoalsAgainst, int Unplayed)
    {
        public int GoalDifference => GoalsFor - GoalsAgainst;
        public double WinRate => Played == 0 ? 0 : (double)Wins / Played;
        public int Points => Wins * 3 + Draws;
    }

    public sealed record HeadToHead(
        string Team1Display, string Team2Display,
        int Team1Wins, int Team2Wins, int Draws,
        IReadOnlyList<Match> Matches);

    public sealed record StandingRow(
        int Position, string Team, int Played, int Wins, int Draws, int Losses,
        int GoalsFor, int GoalsAgainst, int Points)
    {
        public int GoalDifference => GoalsFor - GoalsAgainst;
    }

    public sealed record CompetitionStats(
        string Competition, int? Season, int TotalMatches, int PlayedMatches,
        int TotalGoals, double AvgGoalsPerMatch,
        double HomeWinRate, double DrawRate, double AwayWinRate);

    /// <summary>Win/draw/loss record for a team with optional season/competition/venue filters.</summary>
    public TeamRecord GetTeamRecord(string teamQuery, int? season = null, string? competition = null,
        string? venue = null)
    {
        var resolution = _graph.ResolveTeam(teamQuery);
        if (!resolution.Found)
            throw new KeyNotFoundException(resolution.Note ?? $"Team '{teamQuery}' not found.");

        var key = resolution.Team!.Key;
        var matches = resolution.Team.Matches.AsEnumerable();

        if (season is { } s)
            matches = matches.Where(m => m.Season == s);
        if (!string.IsNullOrWhiteSpace(competition))
        {
            var comp = _queries.ResolveCompetition(competition)
                       ?? throw new KeyNotFoundException($"Competition '{competition}' not found.");
            matches = matches.Where(m => m.Competition == comp);
        }
        if (!string.IsNullOrWhiteSpace(venue))
        {
            matches = venue.Trim().ToLowerInvariant() switch
            {
                "home" => matches.Where(m => m.HomeKey == key),
                "away" => matches.Where(m => m.AwayKey == key),
                _ => matches,
            };
        }

        var w = 0; var d = 0; var l = 0; var gf = 0; var ga = 0; var unplayed = 0;
        foreach (var m in matches)
        {
            if (!m.Played)
            {
                unplayed++;
                continue;
            }
            var isHome = m.HomeKey == key;
            var scored = isHome ? m.HomeGoals!.Value : m.AwayGoals!.Value;
            var conceded = isHome ? m.AwayGoals!.Value : m.HomeGoals!.Value;
            gf += scored;
            ga += conceded;
            if (scored > conceded) w++;
            else if (scored < conceded) l++;
            else d++;
        }

        return new TeamRecord(resolution.Team.DisplayName, w + d + l, w, d, l, gf, ga, unplayed);
    }

    /// <summary>All matches between two teams plus the win tally from team1's perspective.</summary>
    public HeadToHead GetHeadToHead(string team1Query, string team2Query, string? competition = null,
        int limit = 50)
    {
        var r1 = _graph.ResolveTeam(team1Query);
        if (!r1.Found)
            throw new KeyNotFoundException(r1.Note ?? $"Team '{team1Query}' not found.");
        var r2 = _graph.ResolveTeam(team2Query);
        if (!r2.Found)
            throw new KeyNotFoundException(r2.Note ?? $"Team '{team2Query}' not found.");

        var k1 = r1.Team!.Key;
        var k2 = r2.Team!.Key;
        var matches = _graph.Matches
            .Where(m => m.Involves(k1) && m.Involves(k2));

        if (!string.IsNullOrWhiteSpace(competition))
        {
            var comp = _queries.ResolveCompetition(competition)
                       ?? throw new KeyNotFoundException($"Competition '{competition}' not found.");
            matches = matches.Where(m => m.Competition == comp);
        }

        var ordered = matches.OrderByDescending(m => m.Date).Take(Math.Clamp(limit, 1, 200)).ToList();

        var w1 = 0; var w2 = 0; var draws = 0;
        foreach (var m in ordered.Where(m => m.Played))
        {
            if (m.HomeGoals == m.AwayGoals) draws++;
            else
            {
                var winner = m.HomeGoals > m.AwayGoals ? m.HomeKey : m.AwayKey;
                if (winner == k1) w1++; else w2++;
            }
        }

        return new HeadToHead(r1.Team.DisplayName, r2.Team.DisplayName, w1, w2, draws, ordered);
    }

    /// <summary>Computes a league table (3/1/0 points) from the matches of one season.</summary>
    public IReadOnlyList<StandingRow> GetStandings(int season, string? competition = null)
    {
        var comp = string.IsNullOrWhiteSpace(competition)
            ? DataLoader.SerieA
            : _queries.ResolveCompetition(competition)
              ?? throw new KeyNotFoundException($"Competition '{competition}' not found.");

        var matches = _graph.Matches
            .Where(m => m.Competition == comp && m.Season == season && m.Played)
            .ToList();

        var table = new Dictionary<string, (string Display, int P, int W, int D, int L, int GF, int GA)>(
            StringComparer.Ordinal);

        void Bump(string key, string display, int scored, int conceded)
        {
            table.TryGetValue(key, out var row);
            var w = scored > conceded ? 1 : 0;
            var l = scored < conceded ? 1 : 0;
            var d = scored == conceded ? 1 : 0;
            table[key] = (display, row.P + 1, row.W + w, row.D + d, row.L + l, row.GF + scored, row.GA + conceded);
        }

        foreach (var m in matches)
        {
            Bump(m.HomeKey, m.HomeTeam, m.HomeGoals!.Value, m.AwayGoals!.Value);
            Bump(m.AwayKey, m.AwayTeam, m.AwayGoals!.Value, m.HomeGoals!.Value);
        }

        return table
            .Select(kv => new StandingRow(0, kv.Value.Display, kv.Value.P, kv.Value.W, kv.Value.D, kv.Value.L,
                kv.Value.GF, kv.Value.GA, kv.Value.W * 3 + kv.Value.D))
            .OrderByDescending(r => r.Points)
            .ThenByDescending(r => r.Wins)
            .ThenByDescending(r => r.GoalDifference)
            .ThenByDescending(r => r.GoalsFor)
            .ThenBy(r => r.Team, StringComparer.OrdinalIgnoreCase)
            .Select((r, i) => r with { Position = i + 1 })
            .ToList();
    }

    /// <summary>Largest victory margins in the (optionally filtered) dataset.</summary>
    public IReadOnlyList<Match> GetBiggestWins(string? competition = null, int? season = null, int limit = 10)
    {
        var matches = _graph.Matches.Where(m => m.Played);

        if (!string.IsNullOrWhiteSpace(competition))
        {
            var comp = _queries.ResolveCompetition(competition)
                       ?? throw new KeyNotFoundException($"Competition '{competition}' not found.");
            matches = matches.Where(m => m.Competition == comp);
        }
        if (season is { } s)
            matches = matches.Where(m => m.Season == s);

        return matches
            .OrderByDescending(m => Math.Abs(m.HomeGoals!.Value - m.AwayGoals!.Value))
            .ThenByDescending(m => m.HomeGoals!.Value + m.AwayGoals!.Value)
            .ThenByDescending(m => m.Date)
            .Take(Math.Clamp(limit, 1, 100))
            .ToList();
    }

    /// <summary>Aggregate stats: averages and outcome rates for a competition/season slice.</summary>
    public CompetitionStats GetCompetitionStats(string? competition = null, int? season = null)
    {
        var matches = _graph.Matches.AsEnumerable();
        string? comp = null;

        if (!string.IsNullOrWhiteSpace(competition))
        {
            comp = _queries.ResolveCompetition(competition)
                   ?? throw new KeyNotFoundException($"Competition '{competition}' not found.");
            matches = matches.Where(m => m.Competition == comp);
        }
        if (season is { } s)
            matches = matches.Where(m => m.Season == s);

        var list = matches.ToList();
        var played = list.Where(m => m.Played).ToList();
        var goals = played.Sum(m => m.HomeGoals!.Value + m.AwayGoals!.Value);
        var homeWins = played.Count(m => m.HomeGoals > m.AwayGoals);
        var draws = played.Count(m => m.HomeGoals == m.AwayGoals);
        var awayWins = played.Count - homeWins - draws;

        return new CompetitionStats(
            comp ?? "All competitions", season, list.Count, played.Count, goals,
            played.Count == 0 ? 0 : (double)goals / played.Count,
            played.Count == 0 ? 0 : (double)homeWins / played.Count,
            played.Count == 0 ? 0 : (double)draws / played.Count,
            played.Count == 0 ? 0 : (double)awayWins / played.Count);
    }
}
