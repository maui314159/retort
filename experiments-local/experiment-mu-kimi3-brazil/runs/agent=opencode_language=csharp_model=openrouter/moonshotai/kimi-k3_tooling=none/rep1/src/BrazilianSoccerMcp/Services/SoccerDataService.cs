using System.Text;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Services;

/// <summary>
/// Query engine over the unified in-memory match and player records.
/// All team/competition inputs are normalized so spelling variations match.
/// </summary>
public sealed class SoccerDataService
{
    private readonly List<MatchRecord> _matches;
    private readonly List<PlayerRecord> _players;
    private readonly IReadOnlyList<DatasetInfo> _datasets;

    /// <summary>All canonical team names present in the loaded match data.</summary>
    public IReadOnlyList<string> Teams { get; }

    public IReadOnlyList<DatasetInfo> Datasets => _datasets;

    public SoccerDataService(DataLoader loader)
        : this(loader.Matches, loader.Players, loader.Datasets)
    {
    }

    public SoccerDataService(List<MatchRecord> matches, List<PlayerRecord> players, IReadOnlyList<DatasetInfo>? datasets = null)
    {
        _matches = matches;
        _players = players;
        _datasets = datasets ?? [];
        Teams = matches
            .SelectMany(m => new[] { m.HomeTeamCanonical, m.AwayTeamCanonical })
            .Where(n => n.Length > 0)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(n => n, StringComparer.Ordinal)
            .ToList();
    }

    // ---------- Team / competition resolution ----------

    /// <summary>
    /// Resolves a user-supplied team name to a canonical team present in the data.
    /// Throws <see cref="TeamResolutionException"/> when unknown or ambiguous.
    /// </summary>
    public string ResolveTeam(string query)
    {
        if (string.IsNullOrWhiteSpace(query))
            throw new TeamResolutionException("Team name is required.");

        var canonical = TeamNameNormalizer.CanonicalName(query);
        var exact = Teams.FirstOrDefault(t => string.Equals(t, canonical, StringComparison.Ordinal));
        if (exact is not null)
            return exact;

        var key = TeamNameNormalizer.NormalizeKey(query);
        var contains = Teams
            .Where(t => TeamNameNormalizer.NormalizeKey(t).Contains(key, StringComparison.Ordinal)
                     || key.Contains(TeamNameNormalizer.NormalizeKey(t), StringComparison.Ordinal))
            .Distinct()
            .ToList();

        return contains.Count switch
        {
            1 => contains[0],
            0 => throw new TeamResolutionException(
                $"Team '{query}' was not found in the datasets."),
            _ => throw new TeamResolutionException(
                $"Team '{query}' is ambiguous. Did you mean: {string.Join(", ", contains.Take(8))}?"),
        };
    }

    /// <summary>Maps competition synonyms ("brasileirao", "serie a", "libertadores", ...) to canonical names.</summary>
    public static string? ResolveCompetition(string? query)
    {
        if (string.IsNullOrWhiteSpace(query)) return null;
        var key = TeamNameNormalizer.NormalizeKey(query);
        return key switch
        {
            "brasileirao" or "brasileirao serie a" or "serie a" or "campeonato brasileiro"
                or "campeonato brasileiro serie a" or "brasileirao a" => DataLoader.BrasileiraoSerieA,
            "serie b" or "brasileirao serie b" => DataLoader.BrasileiraoSerieB,
            "serie c" or "brasileirao serie c" => DataLoader.BrasileiraoSerieC,
            "copa do brasil" or "brazilian cup" => DataLoader.CopaDoBrasil,
            "libertadores" or "copa libertadores" or "copa libertadores da america"
                or "conmebol libertadores" => DataLoader.CopaLibertadores,
            _ => _matchesCompetitions.FirstOrDefault(c =>
                string.Equals(c, query, StringComparison.OrdinalIgnoreCase)
                || TeamNameNormalizer.NormalizeKey(c) == key),
        };
    }

    private static readonly string[] _matchesCompetitions =
    [
        DataLoader.BrasileiraoSerieA, DataLoader.BrasileiraoSerieB, DataLoader.BrasileiraoSerieC,
        DataLoader.CopaDoBrasil, DataLoader.CopaLibertadores,
    ];

    // ---------- 1. Match queries ----------

    public sealed record MatchFilter
    {
        public string? Team { get; init; }
        public string? Opponent { get; init; }
        public string? Competition { get; init; }
        public int? Season { get; init; }
        public DateOnly? From { get; init; }
        public DateOnly? To { get; init; }
        public string? Round { get; init; }
        public int Limit { get; init; } = 50;
    }

    public List<MatchRecord> FindMatches(MatchFilter filter)
    {
        string? team = filter.Team is null ? null : ResolveTeam(filter.Team);
        string? opponent = filter.Opponent is null ? null : ResolveTeam(filter.Opponent);
        var competition = ResolveCompetition(filter.Competition);

        IEnumerable<MatchRecord> q = _matches;
        if (team is not null && opponent is not null)
        {
            q = q.Where(m =>
                (m.HomeTeamCanonical == team && m.AwayTeamCanonical == opponent) ||
                (m.HomeTeamCanonical == opponent && m.AwayTeamCanonical == team));
        }
        else if (team is not null)
        {
            q = q.Where(m => m.HomeTeamCanonical == team || m.AwayTeamCanonical == team);
        }
        else if (opponent is not null)
        {
            q = q.Where(m => m.HomeTeamCanonical == opponent || m.AwayTeamCanonical == opponent);
        }

        if (competition is not null)
            q = q.Where(m => m.Competition == competition);
        if (filter.Season is { } season)
            q = q.Where(m => m.Season == season);
        if (filter.From is { } from)
            q = q.Where(m => m.Date >= from);
        if (filter.To is { } to)
            q = q.Where(m => m.Date <= to);
        if (!string.IsNullOrWhiteSpace(filter.Round))
            q = q.Where(m => m.Round is not null && RoundMatches(m.Round, filter.Round));

        return q.OrderByDescending(m => m.Date).ThenByDescending(m => m.Season)
                .Take(Math.Clamp(filter.Limit, 1, 500))
                .ToList();
    }

    /// <summary>
    /// Matches a round/stage filter against the stored label. Exact match or whole-word match
    /// ("Final" must NOT match "Semifinals"); multi-word filters ("of 16", "group stage")
    /// fall back to substring matching.
    /// </summary>
    internal static bool RoundMatches(string actual, string wanted)
    {
        if (actual.Equals(wanted, StringComparison.OrdinalIgnoreCase)) return true;
        if (wanted.Contains(' ', StringComparison.Ordinal))
            return actual.Contains(wanted, StringComparison.OrdinalIgnoreCase);
        return actual.Split(' ', StringSplitOptions.RemoveEmptyEntries)
            .Any(token => token.Equals(wanted, StringComparison.OrdinalIgnoreCase));
    }

    public int CountMatches(MatchFilter filter) =>
        FindMatches(filter with { Limit = 500 }).Count;

    // ---------- 2. Team queries ----------

    public sealed record TeamStats
    {
        public required string Team { get; init; }
        public int Matches { get; set; }
        public int Wins { get; set; }
        public int Draws { get; set; }
        public int Losses { get; set; }
        public int GoalsFor { get; set; }
        public int GoalsAgainst { get; set; }
        public double WinRate => Matches == 0 ? 0 : 100.0 * Wins / Matches;
        public int GoalDifference => GoalsFor - GoalsAgainst;
    }

    public enum Venue { All, Home, Away }

    public TeamStats GetTeamStatistics(string teamQuery, int? season = null, string? competition = null, Venue venue = Venue.All)
    {
        var team = ResolveTeam(teamQuery);
        var resolvedCompetition = ResolveCompetition(competition);

        var stats = new TeamStats { Team = team };
        foreach (var m in _matches)
        {
            if (!m.Played) continue;
            if (season is { } s && m.Season != s) continue;
            if (resolvedCompetition is not null && m.Competition != resolvedCompetition) continue;

            var isHome = m.HomeTeamCanonical == team;
            var isAway = m.AwayTeamCanonical == team;
            if (!isHome && !isAway) continue;
            if (venue == Venue.Home && !isHome) continue;
            if (venue == Venue.Away && !isAway) continue;

            var gf = isHome ? m.HomeGoals!.Value : m.AwayGoals!.Value;
            var ga = isHome ? m.AwayGoals!.Value : m.HomeGoals!.Value;
            stats.Matches++;
            stats.GoalsFor += gf;
            stats.GoalsAgainst += ga;
            if (gf > ga) stats.Wins++;
            else if (gf < ga) stats.Losses++;
            else stats.Draws++;
        }
        return stats;
    }

    // ---------- Head-to-head ----------

    public sealed record HeadToHeadResult
    {
        public required string Team1 { get; init; }
        public required string Team2 { get; init; }
        public required List<MatchRecord> Matches { get; init; }
        public int Team1Wins { get; init; }
        public int Team2Wins { get; init; }
        public int Draws { get; init; }
    }

    public HeadToHeadResult HeadToHead(string team1Query, string team2Query, int matchLimit = 20)
    {
        var team1 = ResolveTeam(team1Query);
        var team2 = ResolveTeam(team2Query);

        var matches = _matches
            .Where(m => m.Played &&
                ((m.HomeTeamCanonical == team1 && m.AwayTeamCanonical == team2) ||
                 (m.HomeTeamCanonical == team2 && m.AwayTeamCanonical == team1)))
            .OrderByDescending(m => m.Date)
            .ToList();

        var t1w = 0; var t2w = 0; var d = 0;
        foreach (var m in matches)
        {
            if (m.Result == MatchResult.Draw) d++;
            else if (m.Result == MatchResult.HomeWin)
            { if (m.HomeTeamCanonical == team1) t1w++; else t2w++; }
            else if (m.Result == MatchResult.AwayWin)
            { if (m.AwayTeamCanonical == team1) t1w++; else t2w++; }
        }

        return new HeadToHeadResult
        {
            Team1 = team1,
            Team2 = team2,
            Matches = matches.Take(matchLimit).ToList(),
            Team1Wins = t1w,
            Team2Wins = t2w,
            Draws = d,
        };
    }

    /// <summary>All distinct competitions a team appears in.</summary>
    public List<string> TeamCompetitions(string teamQuery)
    {
        var team = ResolveTeam(teamQuery);
        return _matches
            .Where(m => m.HomeTeamCanonical == team || m.AwayTeamCanonical == team)
            .Select(m => m.Competition)
            .Distinct()
            .OrderBy(c => c, StringComparer.Ordinal)
            .ToList();
    }

    // ---------- 4. Competition queries (standings) ----------

    public sealed record StandingRow
    {
        public required int Position { get; init; }
        public required string Team { get; init; }
        public required int Points { get; init; }
        public required int Wins { get; init; }
        public required int Draws { get; init; }
        public required int Losses { get; init; }
        public required int GoalsFor { get; init; }
        public required int GoalsAgainst { get; init; }
        public int GoalDifference => GoalsFor - GoalsAgainst;
        public int Played => Wins + Draws + Losses;
    }

    public sealed record StandingsResult
    {
        public required string Competition { get; init; }
        public required int Season { get; init; }
        public required List<StandingRow> Rows { get; init; }
        public required string SourceNote { get; init; }
    }

    /// <summary>
    /// Computes a league table from match results. For Brasileirão Série A a single
    /// source is used per season to avoid double counting overlapping datasets:
    /// Brasileirao_Matches (2012+) is preferred, novo_campeonato_brasileiro (2003-2019)
    /// covers earlier seasons.
    /// </summary>
    public StandingsResult GetStandings(string competitionQuery, int season)
    {
        var competition = ResolveCompetition(competitionQuery)
            ?? throw new TeamResolutionException($"Unknown competition '{competitionQuery}'.");

        IEnumerable<MatchRecord> pool = _matches.Where(m => m.Competition == competition && m.Season == season && m.Played);
        var sourceNote = $"source: all '{competition}' data";

        if (competition == DataLoader.BrasileiraoSerieA)
        {
            var preferred = season >= 2012 ? "Brasileirao_Matches" : "novo_campeonato_brasileiro";
            var fromPreferred = pool.Where(m => m.Source == preferred).ToList();
            if (fromPreferred.Count > 0)
            {
                pool = fromPreferred;
                sourceNote = $"source: {preferred}.csv";
            }
            else
            {
                var fallback = pool.Where(m => m.Source != preferred).ToList();
                pool = fallback;
                sourceNote = $"source: {(fallback.FirstOrDefault()?.Source ?? preferred)}.csv";
            }
        }

        // Accumulate per team: [Points, Wins, Draws, Losses, GoalsFor, GoalsAgainst]
        var acc = new Dictionary<string, int[]>(StringComparer.Ordinal);
        int[] AccFor(string team) => acc.TryGetValue(team, out var v) ? v : acc[team] = new int[6];

        foreach (var m in pool)
        {
            var home = AccFor(m.HomeTeamCanonical);
            var away = AccFor(m.AwayTeamCanonical);
            home[4] += m.HomeGoals!.Value; home[5] += m.AwayGoals!.Value;
            away[4] += m.AwayGoals!.Value; away[5] += m.HomeGoals!.Value;
            switch (m.Result)
            {
                case MatchResult.HomeWin: home[0] += 3; home[1]++; away[3]++; break;
                case MatchResult.AwayWin: away[0] += 3; away[1]++; home[3]++; break;
                case MatchResult.Draw: home[0]++; away[0]++; home[2]++; away[2]++; break;
            }
        }

        var rows = acc
            .Select(kv => new StandingRow
            {
                Position = 0,
                Team = kv.Key,
                Points = kv.Value[0],
                Wins = kv.Value[1],
                Draws = kv.Value[2],
                Losses = kv.Value[3],
                GoalsFor = kv.Value[4],
                GoalsAgainst = kv.Value[5],
            })
            .OrderByDescending(r => r.Points)
            .ThenByDescending(r => r.Wins)
            .ThenByDescending(r => r.GoalDifference)
            .ThenByDescending(r => r.GoalsFor)
            .ThenBy(r => r.Team, StringComparer.Ordinal)
            .Select((r, i) => r with { Position = i + 1 })
            .ToList();

        return new StandingsResult { Competition = competition, Season = season, Rows = rows, SourceNote = sourceNote };
    }

    // ---------- 3. Player queries ----------

    public sealed record PlayerFilter
    {
        public string? Name { get; init; }
        public string? Nationality { get; init; }
        public string? Club { get; init; }
        public string? Position { get; init; }
        public int? MinOverall { get; init; }
        public int Limit { get; init; } = 20;
    }

    public List<PlayerRecord> SearchPlayers(PlayerFilter filter)
    {
        IEnumerable<PlayerRecord> q = _players;

        if (!string.IsNullOrWhiteSpace(filter.Name))
            q = q.Where(p => p.Name.Contains(filter.Name, StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(filter.Nationality))
            q = q.Where(p => p.Nationality is not null &&
                p.Nationality.Equals(filter.Nationality, StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(filter.Club))
            q = q.Where(p => p.Club is not null &&
                p.Club.Contains(filter.Club, StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(filter.Position))
            q = q.Where(p => p.Position is not null &&
                p.Position.Equals(filter.Position, StringComparison.OrdinalIgnoreCase));
        if (filter.MinOverall is { } min)
            q = q.Where(p => p.Overall >= min);

        return q.OrderByDescending(p => p.Overall ?? 0)
                .ThenBy(p => p.Name, StringComparer.Ordinal)
                .Take(Math.Clamp(filter.Limit, 1, 200))
                .ToList();
    }

    public int CountPlayers(PlayerFilter filter) =>
        SearchPlayers(filter with { Limit = 200 }).Count;

    public List<PlayerRecord> TopPlayers(string? nationality = null, string? club = null, string? position = null, int limit = 10) =>
        SearchPlayers(new PlayerFilter { Nationality = nationality, Club = club, Position = position, Limit = limit });

    /// <summary>Brazilian players grouped by (Brazilian) club with average rating.</summary>
    public List<(string Club, int Count, double AvgOverall)> BrazilianPlayersByClub(int minCount = 1)
    {
        return _players
            .Where(p => p.Nationality == "Brazil" && p.Club is not null && p.Overall is not null)
            .GroupBy(p => p.Club!)
            .Select(g => (Club: g.Key, Count: g.Count(), Avg: g.Average(p => p.Overall!.Value)))
            .Where(x => x.Count >= minCount)
            .OrderByDescending(x => x.Avg)
            .ToList();
    }

    // ---------- 5. Statistical analysis ----------

    public sealed record AggregateStats
    {
        public required int TotalMatches { get; init; }
        public required int PlayedMatches { get; init; }
        public required double AvgGoalsPerMatch { get; init; }
        public required double HomeWinRate { get; init; }
        public required double DrawRate { get; init; }
        public required double AwayWinRate { get; init; }
        public required List<MatchRecord> BiggestWins { get; init; }
    }

    public AggregateStats GetMatchStatistics(string? competition = null, int? season = null, int biggestWinsCount = 5)
    {
        var resolvedCompetition = ResolveCompetition(competition);
        IEnumerable<MatchRecord> q = _matches;
        if (resolvedCompetition is not null) q = q.Where(m => m.Competition == resolvedCompetition);
        if (season is { } s) q = q.Where(m => m.Season == s);

        var all = q.ToList();
        var played = all.Where(m => m.Played).ToList();
        var homeWins = played.Count(m => m.Result == MatchResult.HomeWin);
        var draws = played.Count(m => m.Result == MatchResult.Draw);
        var awayWins = played.Count(m => m.Result == MatchResult.AwayWin);

        return new AggregateStats
        {
            TotalMatches = all.Count,
            PlayedMatches = played.Count,
            AvgGoalsPerMatch = played.Count == 0 ? 0 : played.Average(m => m.TotalGoals),
            HomeWinRate = played.Count == 0 ? 0 : 100.0 * homeWins / played.Count,
            DrawRate = played.Count == 0 ? 0 : 100.0 * draws / played.Count,
            AwayWinRate = played.Count == 0 ? 0 : 100.0 * awayWins / played.Count,
            BiggestWins = played
                .OrderByDescending(m => m.GoalMargin)
                .ThenByDescending(m => m.TotalGoals)
                .Take(biggestWinsCount)
                .ToList(),
        };
    }

    public List<MatchRecord> BiggestWins(string? competition = null, int? season = null, int limit = 10)
    {
        var resolvedCompetition = ResolveCompetition(competition);
        IEnumerable<MatchRecord> q = _matches.Where(m => m.Played);
        if (resolvedCompetition is not null) q = q.Where(m => m.Competition == resolvedCompetition);
        if (season is { } s) q = q.Where(m => m.Season == s);
        return q.OrderByDescending(m => m.GoalMargin)
                .ThenByDescending(m => m.TotalGoals)
                .Take(Math.Clamp(limit, 1, 100))
                .ToList();
    }

    // ---------- Derbies ----------

    /// <summary>Well-known Brazilian rivalries (canonical team names).</summary>
    public static readonly IReadOnlyDictionary<string, (string Team1, string Team2)> Derbies =
        new Dictionary<string, (string, string)>(StringComparer.Ordinal)
        {
            ["Fla-Flu"] = ("Flamengo", "Fluminense"),
            ["Clássico dos Milhões"] = ("Flamengo", "Vasco da Gama"),
            ["Clássico da Rivalidade"] = ("Flamengo", "Botafogo"),
            ["Flamengo x Palmeiras"] = ("Flamengo", "Palmeiras"),
            ["Derby Paulista"] = ("Corinthians", "Palmeiras"),
            ["Majestoso"] = ("Corinthians", "São Paulo"),
            ["Clássico Alvinegro"] = ("Corinthians", "Santos"),
            ["Choque-Rei"] = ("Palmeiras", "São Paulo"),
            ["San-São"] = ("Santos", "São Paulo"),
            ["Gre-Nal"] = ("Grêmio", "Internacional"),
            ["Clássico Mineiro"] = ("Atlético Mineiro", "Cruzeiro"),
            ["Ba-Vi"] = ("Bahia", "Vitória"),
            ["Clássico-Rei"] = ("Ceará", "Fortaleza"),
            ["Clássico Carioca (Fla x Vasco)"] = ("Flamengo", "Vasco da Gama"),
            ["Atle-Tiba"] = ("Athletico Paranaense", "Coritiba"),
            ["Grenal do Norte (Re-Pa)"] = ("Remo", "Paysandu"),
        };

    public sealed record DerbyMatch(string DerbyName, MatchRecord Match);

    public List<DerbyMatch> FindDerbies(int? season = null, int limit = 50)
    {
        var results = new List<DerbyMatch>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var (derbyName, (t1, t2)) in Derbies)
        {
            foreach (var m in _matches)
            {
                if (!m.Played) continue;
                if (season is { } s && m.Season != s) continue;
                var isPair =
                    (m.HomeTeamCanonical == t1 && m.AwayTeamCanonical == t2) ||
                    (m.HomeTeamCanonical == t2 && m.AwayTeamCanonical == t1);
                if (!isPair) continue;
                var key = $"{derbyName}|{m.Date}|{m.HomeTeamCanonical}|{m.AwayTeamCanonical}|{m.Competition}";
                if (seen.Add(key))
                    results.Add(new DerbyMatch(derbyName, m));
            }
        }
        return results
            .OrderByDescending(d => d.Match.Date)
            .Take(Math.Clamp(limit, 1, 500))
            .ToList();
    }
}

public sealed class TeamResolutionException : Exception
{
    public TeamResolutionException(string message) : base(message) { }
}
