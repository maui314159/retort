using System.Text;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Services;

/// <summary>Head-to-head summary between two teams.</summary>
public sealed record HeadToHead(
    string Team1, string Team2,
    int Team1Wins, int Team2Wins, int Draws,
    int Team1Goals, int Team2Goals,
    IReadOnlyList<Match> Matches);

/// <summary>Aggregated W/D/L record for one team.</summary>
public sealed record TeamRecord(
    string Team, string Venue, int? Season, string? Competition,
    int Matches, int Wins, int Draws, int Losses,
    int GoalsFor, int GoalsAgainst)
{
    public double WinRate => Matches == 0 ? 0 : (double)Wins / Matches * 100.0;
}

/// <summary>One row of a computed league table.</summary>
public sealed record StandingRow(
    int Position, string Team, int Points, int Played,
    int Wins, int Draws, int Losses, int GoalsFor, int GoalsAgainst)
{
    public int GoalDifference => GoalsFor - GoalsAgainst;
}

/// <summary>Dataset-wide (or competition-wide) aggregate statistics.</summary>
public sealed record StatsOverview(
    string? Competition, int? Season,
    int MatchCount, int TotalGoals, double AvgGoalsPerMatch,
    double HomeWinRate, double DrawRate, double AwayWinRate);

/// <summary>
/// In-memory knowledge store over the six Kaggle CSVs plus the query API
/// used by the MCP tools. Matches are deduplicated across overlapping
/// source files by (date, home team, away team).
/// </summary>
public sealed class SoccerDataService
{
    public IReadOnlyList<Match> Matches { get; }
    public IReadOnlyList<Player> Players { get; }

    // distinct canonical team keys present in the data: canonicalKey -> displayName
    private readonly Dictionary<string, string> _teamIndex;

    public SoccerDataService(IEnumerable<Match> matches, IEnumerable<Player> players)
    {
        Matches = Dedupe(matches).OrderByDescending(m => m.Date ?? DateTime.MinValue).ToList();
        Players = players.ToList();
        _teamIndex = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var m in Matches)
        {
            _teamIndex.TryAdd(m.HomeTeamKey, TeamCanon.DisplayName(m.HomeTeamKey));
            _teamIndex.TryAdd(m.AwayTeamKey, TeamCanon.DisplayName(m.AwayTeamKey));
        }
    }

    public static SoccerDataService LoadFromDirectory(string dataDir) =>
        new(DataLoader.LoadMatches(dataDir), DataLoader.LoadPlayers(dataDir));

    /// <summary>
    /// Removes duplicate records of the same real-world match appearing in
    /// several source files. Key: (date, home key, away key), with a ±1 day
    /// tolerance because sources disagree on late-night kickoff dates
    /// (local vs UTC recording). Undated matches are always kept.
    /// </summary>
    private static IEnumerable<Match> Dedupe(IEnumerable<Match> matches)
    {
        // Source priority: canonical files first
        var priority = new Dictionary<string, int>
        {
            ["Brasileirao_Matches.csv"] = 0,
            ["Brazilian_Cup_Matches.csv"] = 1,
            ["Libertadores_Matches.csv"] = 2,
            ["novo_campeonato_brasileiro.csv"] = 3,
            ["BR-Football-Dataset.csv"] = 4,
        };

        var seen = new Dictionary<string, (int Priority, Match Match)>();
        foreach (var m in matches)
        {
            if (m.Date is null) { yield return m; continue; }
            var p = priority.GetValueOrDefault(m.Source, 9);

            // probe date-1, date, date+1 for an already-seen record of this fixture
            string? foundKey = null;
            (int Priority, Match Match) found = default;
            for (var delta = -1; delta <= 1 && foundKey is null; delta++)
            {
                var probe = $"{m.Date.Value.AddDays(delta):yyyy-MM-dd}|{m.HomeTeamKey}|{m.AwayTeamKey}";
                if (seen.TryGetValue(probe, out found))
                    foundKey = probe;
            }

            if (foundKey is null)
            {
                seen[$"{m.Date.Value:yyyy-MM-dd}|{m.HomeTeamKey}|{m.AwayTeamKey}"] = (p, m);
            }
            else if (p < found.Priority)
            {
                // better source: replace the older record
                seen.Remove(foundKey);
                seen[$"{m.Date.Value:yyyy-MM-dd}|{m.HomeTeamKey}|{m.AwayTeamKey}"] = (p, m);
            }
            // else: worse or equal source -> drop
        }
        foreach (var v in seen.Values) yield return v.Match;
    }

    // ------------------------------------------------------------------
    // Discovery
    // ------------------------------------------------------------------

    public IReadOnlyList<string> GetCompetitions() =>
        Matches.Select(m => m.Competition).Distinct(StringComparer.Ordinal)
               .OrderBy(c => c, StringComparer.Ordinal).ToList();

    public IReadOnlyList<string> GetTeams(string? competition = null) =>
        Matches.Where(m => competition is null || CompetitionMatches(m.Competition, competition))
               .SelectMany(m => new[] { m.HomeTeam, m.AwayTeam })
               .Distinct(StringComparer.OrdinalIgnoreCase)
               .OrderBy(t => t, StringComparer.OrdinalIgnoreCase).ToList();

    public IReadOnlyList<string> GetCompetitionsForTeam(string team)
    {
        var keys = ResolveTeamKeys(team);
        return Matches.Where(m => keys.Contains(m.HomeTeamKey) || keys.Contains(m.AwayTeamKey))
                      .Select(m => m.Competition).Distinct(StringComparer.Ordinal)
                      .OrderBy(c => c, StringComparer.Ordinal).ToList();
    }

    // ------------------------------------------------------------------
    // Match queries
    // ------------------------------------------------------------------

    public List<Match> FindMatches(string? team1 = null, string? team2 = null,
        string? competition = null, int? season = null,
        DateTime? from = null, DateTime? to = null, int limit = 50)
    {
        var keys1 = team1 is null ? null : ResolveTeamKeys(team1);
        var keys2 = team2 is null ? null : ResolveTeamKeys(team2);

        IEnumerable<Match> q = Matches;
        if (keys1 is not null)
            q = q.Where(m => keys1.Contains(m.HomeTeamKey) || keys1.Contains(m.AwayTeamKey));
        if (keys2 is not null)
            q = q.Where(m => keys2.Contains(m.HomeTeamKey) || keys2.Contains(m.AwayTeamKey));
        if (competition is not null)
            q = q.Where(m => CompetitionMatches(m.Competition, competition));
        if (season is not null)
            q = q.Where(m => m.Season == season || (m.Season is null && m.Date?.Year == season));
        if (from is not null)
            q = q.Where(m => m.Date >= from);
        if (to is not null)
            q = q.Where(m => m.Date <= to);

        return q.OrderByDescending(m => m.Date ?? DateTime.MinValue).Take(limit).ToList();
    }

    public HeadToHead GetHeadToHead(string team1, string team2)
    {
        var k1 = ResolveTeamKeys(team1);
        var k2 = ResolveTeamKeys(team2);
        var games = Matches.Where(m =>
                (k1.Contains(m.HomeTeamKey) && k2.Contains(m.AwayTeamKey)) ||
                (k2.Contains(m.HomeTeamKey) && k1.Contains(m.AwayTeamKey)))
            .OrderByDescending(m => m.Date ?? DateTime.MinValue).ToList();

        var t1w = 0; var t2w = 0; var d = 0; var t1g = 0; var t2g = 0;
        foreach (var m in games)
        {
            var t1Home = k1.Contains(m.HomeTeamKey);
            var gf = t1Home ? m.HomeGoals : m.AwayGoals;
            var ga = t1Home ? m.AwayGoals : m.HomeGoals;
            t1g += gf; t2g += ga;
            if (gf > ga) t1w++; else if (gf < ga) t2w++; else d++;
        }
        return new HeadToHead(team1, team2, t1w, t2w, d, t1g, t2g, games);
    }

    // ------------------------------------------------------------------
    // Team queries
    // ------------------------------------------------------------------

    public TeamRecord GetTeamRecord(string team, int? season = null,
        string? competition = null, string venue = "all") =>
        GetTeamRecordForKeys(team, ResolveTeamKeys(team), season, competition, venue);

    internal TeamRecord GetTeamRecordForKeys(string displayName, HashSet<string> keys,
        int? season, string? competition, string venue)
    {
        var venueKey = venue.Trim().ToLowerInvariant();

        var q = Matches.Where(m => keys.Contains(m.HomeTeamKey) || keys.Contains(m.AwayTeamKey));
        if (competition is not null)
            q = q.Where(m => CompetitionMatches(m.Competition, competition));
        if (season is not null)
            q = q.Where(m => m.Season == season || (m.Season is null && m.Date?.Year == season));
        if (venueKey is "home")
            q = q.Where(m => keys.Contains(m.HomeTeamKey));
        else if (venueKey is "away")
            q = q.Where(m => keys.Contains(m.AwayTeamKey));

        var played = 0; var w = 0; var d = 0; var l = 0; var gf = 0; var ga = 0;
        foreach (var m in q)
        {
            var home = keys.Contains(m.HomeTeamKey);
            var f = home ? m.HomeGoals : m.AwayGoals;
            var a = home ? m.AwayGoals : m.HomeGoals;
            played++; gf += f; ga += a;
            if (f > a) w++; else if (f < a) l++; else d++;
        }
        return new TeamRecord(displayName, venueKey, season, competition, played, w, d, l, gf, ga);
    }

    // ------------------------------------------------------------------
    // Competition queries
    // ------------------------------------------------------------------

    public List<StandingRow> GetStandings(string competition, int season)
    {
        var table = new Dictionary<string, (int P, int W, int D, int L, int GF, int GA, string Name)>();
        var q = Matches.Where(m => CompetitionMatches(m.Competition, competition)
                                   && (m.Season == season || (m.Season is null && m.Date?.Year == season)));

        foreach (var m in q)
        {
            AddSide(m.HomeTeamKey, m.HomeGoals, m.AwayGoals);
            AddSide(m.AwayTeamKey, m.AwayGoals, m.HomeGoals);

            void AddSide(string key, int f, int a)
            {
                var name = TeamCanon.DisplayName(key);
                var cur = table.GetValueOrDefault(key,
                    (P: 0, W: 0, D: 0, L: 0, GF: 0, GA: 0, Name: name));
                cur.P++;
                cur.GF += f; cur.GA += a;
                if (f > a) cur.W++; else if (f < a) cur.L++; else cur.D++;
                cur.Name = name;
                table[key] = cur;
            }
        }

        var rows = table
            .Select(kv => new StandingRow(0, kv.Value.Name, kv.Value.W * 3 + kv.Value.D,
                kv.Value.P, kv.Value.W, kv.Value.D, kv.Value.L, kv.Value.GF, kv.Value.GA))
            .OrderByDescending(r => r.Points)
            .ThenByDescending(r => r.Wins)
            .ThenByDescending(r => r.GoalDifference)
            .ThenByDescending(r => r.GoalsFor)
            .ToList();

        for (var i = 0; i < rows.Count; i++)
            rows[i] = rows[i] with { Position = i + 1 };
        return rows;
    }

    // ------------------------------------------------------------------
    // Statistical analysis
    // ------------------------------------------------------------------

    public StatsOverview GetOverview(string? competition = null, int? season = null)
    {
        var q = Matches.AsEnumerable();
        if (competition is not null)
            q = q.Where(m => CompetitionMatches(m.Competition, competition));
        if (season is not null)
            q = q.Where(m => m.Season == season || (m.Season is null && m.Date?.Year == season));

        var count = 0; var goals = 0; var homeW = 0; var draws = 0; var awayW = 0;
        foreach (var m in q)
        {
            count++; goals += m.TotalGoals;
            if (m.HomeGoals > m.AwayGoals) homeW++;
            else if (m.HomeGoals < m.AwayGoals) awayW++;
            else draws++;
        }

        return new StatsOverview(competition, season, count, goals,
            count == 0 ? 0 : Math.Round((double)goals / count, 2),
            count == 0 ? 0 : Math.Round((double)homeW / count * 100, 1),
            count == 0 ? 0 : Math.Round((double)draws / count * 100, 1),
            count == 0 ? 0 : Math.Round((double)awayW / count * 100, 1));
    }

    public List<Match> GetBiggestWins(string? competition = null, int? season = null, int limit = 10)
    {
        var q = Matches.AsEnumerable();
        if (competition is not null)
            q = q.Where(m => CompetitionMatches(m.Competition, competition));
        if (season is not null)
            q = q.Where(m => m.Season == season || (m.Season is null && m.Date?.Year == season));
        return q.OrderByDescending(m => m.GoalMargin)
                .ThenByDescending(m => m.TotalGoals)
                .Take(limit).ToList();
    }

    /// <summary>Best home records (min 10 home matches), best away records.</summary>
    public List<(string Team, TeamRecord Record)> GetBestRecords(string venue, int? season = null, int limit = 10, int minMatches = 10)
    {
        var rows = new List<(string, TeamRecord)>();
        foreach (var (key, display) in _teamIndex)
        {
            var keys = new HashSet<string> { key };
            var r = GetTeamRecordForKeys(display, keys, season, null, venue);
            if (r.Matches >= minMatches) rows.Add((display, r));
        }
        return rows.OrderByDescending(r => r.Item2.WinRate)
                   .ThenByDescending(r => r.Item2.Wins)
                   .Take(limit).ToList();
    }

    // ------------------------------------------------------------------
    // Derbies
    // ------------------------------------------------------------------

    private static readonly (string A, string B, string Name)[] ClassicDerbies =
    [
        ("Flamengo", "Fluminense", "Fla-Flu"),
        ("Flamengo", "Vasco", "Clássico dos Milhões"),
        ("Flamengo", "Botafogo", "Clássico da Rivalidade"),
        ("Fluminense", "Botafogo", "Clássico Vovô"),
        ("Corinthians", "Palmeiras", "Derby Paulista"),
        ("Corinthians", "São Paulo", "Majestoso"),
        ("Palmeiras", "São Paulo", "Choque-Rei"),
        ("Santos", "Corinthians", "Clássico Alvinegro"),
        ("Santos", "Palmeiras", "Clássico da Saudade"),
        ("Grêmio", "Internacional", "Grenal"),
        ("Atlético Mineiro", "Cruzeiro", "Clássico Mineiro"),
        ("Bahia", "Vitória", "Ba-Vi"),
        ("Athletico Paranaense", "Coritiba", "Atletiba"),
        ("Ceará", "Fortaleza", "Clássico-Rei"),
        ("Sport", "Náutico", "Clássico dos Clássicos"),
        ("Goiás", "Vila Nova", "Clássico do Equilíbrio"),
    ];

    public List<(Match Match, string DerbyName)> FindDerbies(int? season = null, int limit = 50)
    {
        var derbyKeys = ClassicDerbies
            .Select(d => (ResolveTeamKeys(d.A), ResolveTeamKeys(d.B), d.Name))
            .ToList();

        var result = new List<(Match, string)>();
        foreach (var m in Matches)
        {
            if (season is not null && !(m.Season == season || (m.Season is null && m.Date?.Year == season)))
                continue;
            foreach (var (ka, kb, name) in derbyKeys)
            {
                var isDerby =
                    (ka.Contains(m.HomeTeamKey) && kb.Contains(m.AwayTeamKey)) ||
                    (kb.Contains(m.HomeTeamKey) && ka.Contains(m.AwayTeamKey));
                if (isDerby)
                {
                    result.Add((m, name));
                    break;
                }
            }
        }
        return result.OrderByDescending(r => r.Item1.Date ?? DateTime.MinValue).Take(limit).ToList();
    }

    // ------------------------------------------------------------------
    // Player queries
    // ------------------------------------------------------------------

    public List<Player> SearchPlayers(string? name = null, string? nationality = null,
        string? club = null, string? position = null, int? minOverall = null, int limit = 20)
    {
        IEnumerable<Player> q = Players;

        if (!string.IsNullOrWhiteSpace(name))
        {
            var needle = TeamNameNormalizer.RemoveDiacritics(name).ToLowerInvariant();
            q = q.Where(p => TeamNameNormalizer.RemoveDiacritics(p.Name)
                .Contains(needle, StringComparison.OrdinalIgnoreCase));
        }
        if (!string.IsNullOrWhiteSpace(nationality))
            q = q.Where(p => string.Equals(p.Nationality, nationality, StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(club))
        {
            var needle = TeamNameNormalizer.RemoveDiacritics(club).ToLowerInvariant();
            q = q.Where(p => p.Club is not null &&
                             TeamNameNormalizer.RemoveDiacritics(p.Club)
                                 .Contains(needle, StringComparison.OrdinalIgnoreCase));
        }
        if (!string.IsNullOrWhiteSpace(position))
            q = q.Where(p => p.Position is not null &&
                             p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));
        if (minOverall is not null)
            q = q.Where(p => p.Overall >= minOverall);

        return q.OrderByDescending(p => p.Overall ?? 0).ThenBy(p => p.Name).Take(limit).ToList();
    }

    /// <summary>Counts and average rating of players grouped by club (for a nationality filter).</summary>
    public List<(string Club, int Count, double AvgOverall)> GetClubPlayerSummary(string? nationality = null, int limit = 20)
    {
        IEnumerable<Player> q = Players.Where(p => p.Club is not null && p.Overall is not null);
        if (!string.IsNullOrWhiteSpace(nationality))
            q = q.Where(p => string.Equals(p.Nationality, nationality, StringComparison.OrdinalIgnoreCase));

        return q.GroupBy(p => p.Club!, StringComparer.OrdinalIgnoreCase)
                .Select(g => (g.Key, g.Count(), Math.Round(g.Average(p => p.Overall ?? 0), 1)))
                .OrderByDescending(x => x.Item2)
                .Take(limit).ToList();
    }

    // ------------------------------------------------------------------
    // Name / competition matching helpers
    // ------------------------------------------------------------------

    /// <summary>
    /// Resolves a user-supplied team name to the set of canonical keys used in
    /// the dataset. The query goes through the same canonicalization as the
    /// data, so "Palmeiras-SP", "palmeiras" and "Sociedade Esportiva Palmeiras"
    /// all resolve identically. Falls back to legal-form stripping and
    /// containment for exotic phrasings.
    /// </summary>
    public HashSet<string> ResolveTeamKeys(string team)
    {
        var keys = new HashSet<string>(StringComparer.Ordinal);

        var canonical = TeamCanon.CanonicalKey(team);
        if (canonical.Length == 0) return keys;
        if (_teamIndex.ContainsKey(canonical)) keys.Add(canonical);

        if (keys.Count > 0) return keys;

        // fallback 1: legal-form-stripped query ("São Paulo Futebol Clube" -> "sao paulo")
        var loose = TeamNameNormalizer.LooseKey(team);
        if (loose.Length > 0)
        {
            var strippedCanon = TeamCanon.CanonicalKey(loose);
            if (_teamIndex.ContainsKey(strippedCanon)) keys.Add(strippedCanon);
            if (_teamIndex.ContainsKey(loose)) keys.Add(loose);
        }
        if (keys.Count > 0) return keys;

        // fallback 2: containment against known canonical keys
        foreach (var kv in _teamIndex)
        {
            var strict = kv.Key;
            if (canonical.Length >= 4 && strict.Contains(canonical, StringComparison.Ordinal)) keys.Add(strict);
            else if (strict.Length >= 4 && canonical.Contains(strict, StringComparison.Ordinal)) keys.Add(strict);
        }
        return keys;
    }

    /// <summary>Diacritics/case-insensitive containment match for competition names.</summary>
    public static bool CompetitionMatches(string competition, string filter)
    {
        var c = TeamNameNormalizer.RemoveDiacritics(competition).ToLowerInvariant();
        var f = TeamNameNormalizer.RemoveDiacritics(filter).ToLowerInvariant().Trim();
        if (c == f || c.Contains(f, StringComparison.Ordinal)) return true;
        // synonyms
        var synonyms = new Dictionary<string, string[]>
        {
            ["brasileirao"] = ["serie a", "campeonato brasileiro"],
            ["serie a"] = ["brasileirao"],
            ["copa do brasil"] = ["brazilian cup"],
            ["libertadores"] = ["copa libertadores"],
        };
        if (synonyms.TryGetValue(f, out var alts))
            return alts.Any(a => c.Contains(a, StringComparison.Ordinal));
        return false;
    }

    // ------------------------------------------------------------------
    // Formatting helpers (shared by tools)
    // ------------------------------------------------------------------

    public static string FormatMatch(Match m) => m.ToString();

    public static string FormatMatches(IEnumerable<Match> matches, int shown, int total)
    {
        var sb = new StringBuilder();
        foreach (var m in matches) sb.AppendLine($"- {m}");
        if (total > shown) sb.AppendLine($"... ({total - shown} more matches in dataset)");
        return sb.ToString();
    }
}
