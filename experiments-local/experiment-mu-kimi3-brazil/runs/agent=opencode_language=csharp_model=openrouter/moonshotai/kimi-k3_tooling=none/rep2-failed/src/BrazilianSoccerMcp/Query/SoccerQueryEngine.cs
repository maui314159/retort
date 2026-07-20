// Context: Brazilian Soccer MCP Server.
// Query engine over the knowledge graph. All MCP tools and all BDD tests go
// through this class, so transport and tests exercise identical logic.
// Team resolution: a free-text query ("Palmeiras", "palmeiras-sp",
// "Sport Club Corinthians Paulista") is folded and mapped to one or more
// canonical team identities; ambiguous base names (e.g. "Atlético") match
// every identity with that base so results are complete rather than wrong.
namespace BrazilianSoccerMcp.Query;

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Graph;

public sealed class ResolvedTeam
{
    public required string Query { get; init; }
    public required List<TeamNode> Matches { get; init; }
    public bool Found => Matches.Count > 0;
    public bool Ambiguous => Matches.Count > 1;
    public string DisplayName => Matches.Count == 0 ? Query : Matches[0].DisplayName;
}

public sealed class SoccerQueryEngine
{
    private readonly SoccerKnowledgeGraph _graph;

    public SoccerQueryEngine(SoccerKnowledgeGraph graph) => _graph = graph;

    /// <summary>All seasons covered by the dataset, ascending.</summary>
    public IReadOnlyCollection<int> Seasons => _graph.Seasons;

    /// <summary>Competition name -> total match count.</summary>
    public IReadOnlyDictionary<string, int> CompetitionMatchCounts =>
        _graph.Competitions.ToDictionary(kv => kv.Key, kv => kv.Value.Seasons.Values.Sum(s => s.Count));

    /// <summary>Classic Brazilian derbies as unordered identity-key pairs.</summary>
    public static readonly (string Name, string KeyA, string KeyB)[] Derbies =
    [
        ("Fla-Flu", "flamengo|RJ", "fluminense|RJ"),
        ("Clássico dos Milhões", "flamengo|RJ", "vasco|RJ"),
        ("Clássico Vovô", "botafogo|RJ", "fluminense|RJ"),
        ("Clássico Majestoso", "corinthians|SP", "sao paulo|SP"),
        ("Derby Paulista", "corinthians|SP", "palmeiras|SP"),
        ("Choque-Rei", "palmeiras|SP", "sao paulo|SP"),
        ("San-São", "santos|SP", "sao paulo|SP"),
        ("Gre-Nal", "gremio|RS", "internacional|RS"),
        ("Clássico Mineiro", "atletico|MG", "cruzeiro|MG"),
        ("Clássico das Multidões", "america|MG", "cruzeiro|MG"),
        ("Ba-Vi", "bahia|BA", "vitoria|BA"),
        ("Clássico Cearense", "ceara|CE", "fortaleza|CE"),
        ("Atletiba", "atletico|PR", "coritiba|PR"),
        ("Clássico Goiano", "atletico|GO", "goias|GO"),
    ];

    /// <summary>Resolves a free-text team query to canonical team node(s).</summary>
    public ResolvedTeam ResolveTeam(string query)
    {
        var matches = new List<TeamNode>();
        if (!string.IsNullOrWhiteSpace(query))
        {
            var (baseName, region) = TeamNameNormalizer.Parse(query);
            var folded = TeamNameNormalizer.Fold(baseName);

            // 1) Exact identity lookup (query included a state, or hits a stateless default).
            var key = TeamNameNormalizer.IdentityKey(query);
            if (_graph.Teams.TryGetValue(key, out var exact))
                matches.Add(exact);

            // 2) All identities sharing this base name (covers stateless queries
            //    like "Atlético" that map to MG + GO + PR clubs).
            if (matches.Count == 0)
            {
                var prefix = folded + "|";
                foreach (var (k, node) in _graph.Teams)
                    if (k == folded || k.StartsWith(prefix, StringComparison.Ordinal))
                        matches.Add(node);
            }

            // 3) Contains fallback ("Sport Club Corinthians Paulista" -> corinthians).
            if (matches.Count == 0)
            {
                foreach (var (k, node) in _graph.Teams)
                {
                    var nodeBase = k.Split('|')[0];
                    if (folded.Contains(nodeBase, StringComparison.Ordinal) && nodeBase.Length >= 4
                        || nodeBase.Contains(folded, StringComparison.Ordinal) && folded.Length >= 4)
                        matches.Add(node);
                }
                matches = matches.OrderBy(m => m.Key.Length).Take(4).ToList();
            }
        }
        return new ResolvedTeam { Query = query, Matches = matches };
    }

    /// <summary>Match search with optional filters. Results ascending by date; pass mostRecentFirst to invert.</summary>
    public List<MatchRecord> FindMatches(
        string? team = null, string? opponent = null, string? competition = null,
        int? season = null, DateOnly? from = null, DateOnly? to = null,
        int limit = 20, bool mostRecentFirst = false)
    {
        var teamKeys = team is null ? null : ResolveTeam(team).Matches.Select(t => t.Key).ToHashSet();
        var opponentKeys = opponent is null ? null : ResolveTeam(opponent).Matches.Select(t => t.Key).ToHashSet();
        var comp = competition is null ? null : Competitions.Normalize(competition) ?? competition;

        IEnumerable<MatchRecord> q = _graph.AllMatches;
        if (teamKeys is not null)
            q = q.Where(m => teamKeys.Contains(m.HomeTeamKey) || teamKeys.Contains(m.AwayTeamKey));
        if (opponentKeys is not null)
            q = q.Where(m => (teamKeys is null || teamKeys.Contains(m.HomeTeamKey) || teamKeys.Contains(m.AwayTeamKey))
                          && (opponentKeys.Contains(m.HomeTeamKey) || opponentKeys.Contains(m.AwayTeamKey))
                          && m.HomeTeamKey != m.AwayTeamKey);
        if (comp is not null)
            q = q.Where(m => m.Competition.Equals(comp, StringComparison.OrdinalIgnoreCase));
        if (season is not null) q = q.Where(m => m.Season == season.Value);
        if (from is not null) q = q.Where(m => m.Date >= from.Value);
        if (to is not null) q = q.Where(m => m.Date <= to.Value);

        q = mostRecentFirst ? q.OrderByDescending(m => m.Date) : q.OrderBy(m => m.Date);
        return q.Take(limit).ToList();
    }

    /// <summary>Full head-to-head record between two teams.</summary>
    public HeadToHead? HeadToHead(string teamA, string teamB)
    {
        var a = ResolveTeam(teamA);
        var b = ResolveTeam(teamB);
        if (!a.Found || !b.Found) return null;

        var keysA = a.Matches.Select(t => t.Key).ToHashSet();
        var keysB = b.Matches.Select(t => t.Key).ToHashSet();
        var games = _graph.AllMatches
            .Where(m => (keysA.Contains(m.HomeTeamKey) && keysB.Contains(m.AwayTeamKey))
                     || (keysB.Contains(m.HomeTeamKey) && keysA.Contains(m.AwayTeamKey)))
            .OrderByDescending(m => m.Date)
            .ToList();

        int winsA = 0, winsB = 0, draws = 0, goalsA = 0, goalsB = 0;
        foreach (var g in games)
        {
            var aIsHome = keysA.Contains(g.HomeTeamKey);
            var (gf, ga) = aIsHome ? (g.HomeGoals, g.AwayGoals) : (g.AwayGoals, g.HomeGoals);
            goalsA += gf; goalsB += ga;
            if (gf > ga) winsA++; else if (gf < ga) winsB++; else draws++;
        }
        return new HeadToHead(a.DisplayName, b.DisplayName, winsA, winsB, draws, goalsA, goalsB, games);
    }

    /// <summary>W/D/L and goals for a team, optionally filtered by competition, season, venue.</summary>
    public TeamRecord? TeamStatistics(string team, string? competition = null, int? season = null, string venue = "all")
    {
        var resolved = ResolveTeam(team);
        if (!resolved.Found) return null;
        var keys = resolved.Matches.Select(t => t.Key).ToHashSet();
        var comp = competition is null ? null : Competitions.Normalize(competition) ?? competition;

        var record = new TeamRecord();
        foreach (var m in _graph.AllMatches)
        {
            var isHome = keys.Contains(m.HomeTeamKey);
            var isAway = keys.Contains(m.AwayTeamKey);
            if (!isHome && !isAway) continue;
            if (comp is not null && !m.Competition.Equals(comp, StringComparison.OrdinalIgnoreCase)) continue;
            if (season is not null && m.Season != season.Value) continue;
            if (venue.Equals("home", StringComparison.OrdinalIgnoreCase) && !isHome) continue;
            if (venue.Equals("away", StringComparison.OrdinalIgnoreCase) && !isAway) continue;

            var (gf, ga) = isHome ? (m.HomeGoals, m.AwayGoals) : (m.AwayGoals, m.HomeGoals);
            record.Played++;
            record.GoalsFor += gf;
            record.GoalsAgainst += ga;
            if (gf > ga) record.Wins++; else if (gf < ga) record.Losses++; else record.Draws++;
        }
        return record;
    }

    /// <summary>Standings for a competition season, calculated from match results
    /// (3 pts win, 1 pt draw; tie-break: wins, goal difference, goals for).</summary>
    public List<(string Team, TeamRecord Record)>? Standings(string competition, int season)
    {
        var comp = Competitions.Normalize(competition) ?? competition;
        if (!_graph.Competitions.TryGetValue(comp, out var node)) return null;
        if (!node.Seasons.TryGetValue(season, out var games)) return null;

        var table = new Dictionary<string, TeamRecord>();
        void Apply(string key, int gf, int ga)
        {
            if (!table.TryGetValue(key, out var r)) table[key] = r = new TeamRecord();
            r.Played++; r.GoalsFor += gf; r.GoalsAgainst += ga;
            if (gf > ga) r.Wins++; else if (gf < ga) r.Losses++; else r.Draws++;
        }
        foreach (var m in games) { Apply(m.HomeTeamKey, m.HomeGoals, m.AwayGoals); Apply(m.AwayTeamKey, m.AwayGoals, m.HomeGoals); }

        return table
            .OrderByDescending(kv => kv.Value.Points)
            .ThenByDescending(kv => kv.Value.Wins)
            .ThenByDescending(kv => kv.Value.GoalDifference)
            .ThenByDescending(kv => kv.Value.GoalsFor)
            .Select(kv => (DisplayName(kv.Key), kv.Value))
            .ToList();

        string DisplayName(string key) =>
            _graph.Teams.TryGetValue(key, out var t) ? t.DisplayName : TeamNameNormalizer.DisplayFor(key);
    }

    /// <summary>Player search across the FIFA dataset (name/nationality/club/position/overall filters).</summary>
    public List<PlayerRecord> SearchPlayers(
        string? name = null, string? nationality = null, string? club = null,
        string? position = null, int? minOverall = null, int limit = 20)
    {
        IEnumerable<PlayerRecord> q = _graph.AllPlayers;
        if (!string.IsNullOrWhiteSpace(name))
        {
            var folded = TeamNameNormalizer.Fold(name);
            q = q.Where(p => TeamNameNormalizer.Fold(p.Name).Contains(folded));
        }
        if (!string.IsNullOrWhiteSpace(nationality))
        {
            var folded = TeamNameNormalizer.Fold(nationality);
            q = q.Where(p => TeamNameNormalizer.Fold(p.Nationality) == folded);
        }
        if (!string.IsNullOrWhiteSpace(club)) q = FilterByClub(q, club);
        if (!string.IsNullOrWhiteSpace(position))
        {
            var wanted = ExpandPosition(position);
            q = q.Where(p => p.Position is not null && wanted.Contains(p.Position));
        }
        if (minOverall is not null) q = q.Where(p => p.Overall >= minOverall.Value);
        return q.OrderByDescending(p => p.Overall).ThenBy(p => p.Name).Take(limit).ToList();
    }

    /// <summary>Top-rated players, optionally filtered by nationality and/or club.</summary>
    public List<PlayerRecord> TopPlayers(string? nationality = null, string? club = null, int limit = 10)
    {
        IEnumerable<PlayerRecord> q = _graph.AllPlayers;
        if (!string.IsNullOrWhiteSpace(nationality))
        {
            var folded = TeamNameNormalizer.Fold(nationality);
            q = q.Where(p => TeamNameNormalizer.Fold(p.Nationality) == folded);
        }
        if (!string.IsNullOrWhiteSpace(club)) q = FilterByClub(q, club);
        return q.OrderByDescending(p => p.Overall).ThenByDescending(p => p.Potential).Take(limit).ToList();
    }

    /// <summary>Players grouped by Brazilian club (clubs that are team nodes in the graph).</summary>
    public List<(string Club, int PlayerCount, double AvgOverall)> BrazilianClubRosters(int minPlayers = 3)
    {
        return _graph.Teams.Values
            .Where(t => t.Players.Count >= minPlayers)
            .Select(t => (Club: t.DisplayName, PlayerCount: t.Players.Count,
                          AvgOverall: t.Players.Average(p => (double)p.Overall)))
            .OrderByDescending(t => t.PlayerCount)
            .ToList();
    }

    /// <summary>Biggest victories by goal margin (ties broken by total goals, recency).</summary>
    public List<MatchRecord> BiggestWins(string? competition = null, int? season = null, int limit = 10)
    {
        var comp = competition is null ? null : Competitions.Normalize(competition) ?? competition;
        IEnumerable<MatchRecord> q = _graph.AllMatches.Where(m => m.GoalMargin > 0);
        if (comp is not null) q = q.Where(m => m.Competition.Equals(comp, StringComparison.OrdinalIgnoreCase));
        if (season is not null) q = q.Where(m => m.Season == season.Value);
        return q.OrderByDescending(m => m.GoalMargin)
                .ThenByDescending(m => m.TotalGoals)
                .ThenByDescending(m => m.Date)
                .Take(limit).ToList();
    }

    /// <summary>Aggregate stats: averages and home/away/draw rates.</summary>
    public (int Matches, double AvgGoals, double HomeWinRate, double DrawRate, double AwayWinRate)?
        CompetitionStats(string? competition = null, int? season = null)
    {
        var comp = competition is null ? null : Competitions.Normalize(competition) ?? competition;
        IEnumerable<MatchRecord> q = _graph.AllMatches;
        if (comp is not null) q = q.Where(m => m.Competition.Equals(comp, StringComparison.OrdinalIgnoreCase));
        if (season is not null) q = q.Where(m => m.Season == season.Value);
        var list = q.ToList();
        if (list.Count == 0) return null;
        var homeWins = list.Count(m => m.HomeWin);
        var draws = list.Count(m => m.IsDraw);
        return (
            list.Count,
            list.Average(m => (double)m.TotalGoals),
            homeWins * 100.0 / list.Count,
            draws * 100.0 / list.Count,
            (list.Count - homeWins - draws) * 100.0 / list.Count);
    }

    /// <summary>Matches between traditional rivals, optionally filtered by season/competition.</summary>
    public List<(string DerbyName, MatchRecord Match)> FindDerbies(int? season = null, string? competition = null, int limit = 30)
    {
        var comp = competition is null ? null : Competitions.Normalize(competition) ?? competition;
        var pairs = Derbies.Select(d => (d.Name, Pair(d.KeyA, d.KeyB))).ToList();
        var result = new List<(string, MatchRecord)>();
        foreach (var m in _graph.AllMatches)
        {
            if (season is not null && m.Season != season.Value) continue;
            if (comp is not null && !m.Competition.Equals(comp, StringComparison.OrdinalIgnoreCase)) continue;
            foreach (var (name, pair) in pairs)
                if (pair.Equals(Pair(m.HomeTeamKey, m.AwayTeamKey)))
                { result.Add((name, m)); break; }
        }
        return result.OrderByDescending(r => r.Item2.Date).Take(limit).ToList();

        static string Pair(string a, string b) => string.CompareOrdinal(a, b) < 0 ? a + "~" + b : b + "~" + a;
    }

    /// <summary>Best home/away records across teams in a competition season.</summary>
    public List<(string Team, TeamRecord Record)> BestRecords(
        string competition, int season, string venue = "home", int limit = 10, int minPlayed = 5)
    {
        var comp = Competitions.Normalize(competition) ?? competition;
        var table = new Dictionary<string, TeamRecord>();
        if (!_graph.Competitions.TryGetValue(comp, out var node)
            || !node.Seasons.TryGetValue(season, out var games)) return [];
        foreach (var m in games)
        {
            var key = venue.Equals("away", StringComparison.OrdinalIgnoreCase) ? m.AwayTeamKey : m.HomeTeamKey;
            var gf = venue.Equals("away", StringComparison.OrdinalIgnoreCase) ? m.AwayGoals : m.HomeGoals;
            var ga = venue.Equals("away", StringComparison.OrdinalIgnoreCase) ? m.HomeGoals : m.AwayGoals;
            if (!table.TryGetValue(key, out var r)) table[key] = r = new TeamRecord();
            r.Played++; r.GoalsFor += gf; r.GoalsAgainst += ga;
            if (gf > ga) r.Wins++; else if (gf < ga) r.Losses++; else r.Draws++;
        }
        return table.Where(kv => kv.Value.Played >= minPlayed)
            .OrderByDescending(kv => kv.Value.Points)
            .ThenByDescending(kv => kv.Value.GoalDifference)
            .Take(limit)
            .Select(kv => (_graph.Teams.TryGetValue(kv.Key, out var t) ? t.DisplayName : kv.Key, kv.Value))
            .ToList();
    }

    private IEnumerable<PlayerRecord> FilterByClub(IEnumerable<PlayerRecord> q, string club)
    {
        var folded = TeamNameNormalizer.Fold(club);
        // Prefer exact folded club equality so "Santos" does not pull in "Santos Laguna".
        var exact = q.Where(p => TeamNameNormalizer.Fold(p.Club) == folded).ToList();
        if (exact.Count > 0) return exact;
        return q.Where(p => p.Club is not null && TeamNameNormalizer.Fold(p.Club).Contains(folded));
    }

    private static HashSet<string> ExpandPosition(string position)
    {
        var folded = TeamNameNormalizer.Fold(position);
        return folded switch
        {
            "forward" or "attacker" or "striker" =>
                ["ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"],
            "midfielder" or "midfield" =>
                ["CM", "CAM", "CDM", "LM", "RM", "LAM", "RAM", "LCM", "RCM", "LDM", "RDM"],
            "defender" or "defence" or "defense" =>
                ["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"],
            "goalkeeper" or "keeper" => ["GK"],
            _ => [position.ToUpperInvariant()],
        };
    }
}
