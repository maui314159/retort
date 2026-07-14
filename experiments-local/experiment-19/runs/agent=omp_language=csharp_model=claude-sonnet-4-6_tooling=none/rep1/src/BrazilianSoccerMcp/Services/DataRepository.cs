using System.Text;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Services;

/// <summary>
/// In-memory store for all CSV data, with query helpers used by MCP tools.
/// Constructed once at startup; all methods are thread-safe (read-only after init).
/// </summary>
public sealed class DataRepository
{
    public IReadOnlyList<MatchRecord> Matches { get; }
    public IReadOnlyList<FifaPlayer>  Players { get; }

    // ─── construction ─────────────────────────────────────────────────────────

    public DataRepository(IReadOnlyList<MatchRecord> matches, IReadOnlyList<FifaPlayer> players)
    {
        Matches = matches;
        Players = players;
    }

    /// <summary>
    /// Loads all six CSVs from <paramref name="dataPath"/> and returns a populated
    /// <see cref="DataRepository"/>.  Duplicate matches between Brasileirao files
    /// are deduplicated by (date, homeTeamKey, awayTeamKey).
    /// </summary>
    public static DataRepository LoadFromCsvs(string dataPath)
    {
        var all = new List<MatchRecord>();

        TryLoad(() => CsvLoaders.LoadBrasileirao(Path.Combine(dataPath, "Brasileirao_Matches.csv")), all);
        TryLoad(() => CsvLoaders.LoadCopaDoBrasil(Path.Combine(dataPath, "Brazilian_Cup_Matches.csv")), all);
        TryLoad(() => CsvLoaders.LoadLibertadores(Path.Combine(dataPath, "Libertadores_Matches.csv")), all);
        TryLoad(() => CsvLoaders.LoadBrFootball(Path.Combine(dataPath, "BR-Football-Dataset.csv")), all);
        TryLoad(() => CsvLoaders.LoadHistoricalBrasileirao(Path.Combine(dataPath, "novo_campeonato_brasileiro.csv")), all);

        // De-duplicate: keep the first occurrence per (date, home, away) within same competition
        var seen    = new HashSet<string>();
        var matches = new List<MatchRecord>(all.Count);
        foreach (var m in all)
        {
            var key = $"{m.Date:yyyy-MM-dd}|{m.HomeTeamSearchKey}|{m.AwayTeamSearchKey}|{m.Competition}";
            if (seen.Add(key)) matches.Add(m);
        }

        var players = new List<FifaPlayer>();
        TryLoad(() => CsvLoaders.LoadFifaPlayers(Path.Combine(dataPath, "fifa_data.csv")), players);

        return new DataRepository(matches, players);

        static void TryLoad<T>(Func<List<T>> loader, List<T> target)
        {
            try { target.AddRange(loader()); }
            catch (Exception ex) { Console.Error.WriteLine($"Warning: {ex.Message}"); }
        }
    }

    // ─── match queries ────────────────────────────────────────────────────────

    /// <summary>
    /// Returns matches where either side matches <paramref name="teamQuery"/>.
    /// Optionally filters by opponent, competition, season, and date range.
    /// </summary>
    public IEnumerable<MatchRecord> FindMatches(
        string?   team        = null,
        string?   opponent    = null,
        string?   competition = null,
        int?      season      = null,
        DateTime? dateFrom    = null,
        DateTime? dateTo      = null)
    {
        var q = Matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(team))
        {
            var tk = TeamNameNormalizer.NormalizeForSearch(team);
            q = q.Where(m => m.HomeTeamSearchKey.Contains(tk, StringComparison.OrdinalIgnoreCase)
                           || m.AwayTeamSearchKey.Contains(tk, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(opponent))
        {
            var ok = TeamNameNormalizer.NormalizeForSearch(opponent);
            q = q.Where(m => m.HomeTeamSearchKey.Contains(ok, StringComparison.OrdinalIgnoreCase)
                           || m.AwayTeamSearchKey.Contains(ok, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(competition))
        {
            var ck = competition.ToLowerInvariant();
            q = q.Where(m => m.Competition.Contains(ck, StringComparison.OrdinalIgnoreCase));
        }

        if (season.HasValue)
            q = q.Where(m => m.Season == season.Value);

        if (dateFrom.HasValue)
            q = q.Where(m => m.Date >= dateFrom.Value);

        if (dateTo.HasValue)
            q = q.Where(m => m.Date <= dateTo.Value);

        return q.OrderByDescending(m => m.Date);
    }

    // ─── team statistics ──────────────────────────────────────────────────────

    public record TeamStats(
        string Team, string Competition, int? Season,
        int Matches, int Wins, int Draws, int Losses,
        int GoalsFor, int GoalsAgainst, int Points)
    {
        public double WinRate => Matches == 0 ? 0 : (double)Wins / Matches * 100;
        public int GoalDifference => GoalsFor - GoalsAgainst;
    }

    public TeamStats GetTeamStats(string team, string? competition = null, int? season = null)
    {
        var tk = TeamNameNormalizer.NormalizeForSearch(team);
        var matches = FindMatches(team, competition: competition, season: season).ToList();

        int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;

        foreach (var m in matches)
        {
            bool isHome = m.HomeTeamSearchKey.Contains(tk, StringComparison.OrdinalIgnoreCase);
            int myGoals    = isHome ? m.HomeGoals : m.AwayGoals;
            int theirGoals = isHome ? m.AwayGoals : m.HomeGoals;

            gf += myGoals;
            ga += theirGoals;

            if      (myGoals > theirGoals) wins++;
            else if (myGoals == theirGoals) draws++;
            else                           losses++;
        }

        int pts = wins * 3 + draws;
        return new TeamStats(team, competition ?? "All", season,
                             matches.Count, wins, draws, losses, gf, ga, pts);
    }

    public TeamStats GetHomeStats(string team, string? competition = null, int? season = null)
    {
        var tk = TeamNameNormalizer.NormalizeForSearch(team);
        var matches = FindMatches(competition: competition, season: season)
            .Where(m => m.HomeTeamSearchKey.Contains(tk, StringComparison.OrdinalIgnoreCase))
            .ToList();

        int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
        foreach (var m in matches)
        {
            gf += m.HomeGoals; ga += m.AwayGoals;
            if      (m.HomeGoals > m.AwayGoals) wins++;
            else if (m.HomeGoals < m.AwayGoals) losses++;
            else                                draws++;
        }
        return new TeamStats(team, competition ?? "All", season,
                             matches.Count, wins, draws, losses, gf, ga, wins * 3 + draws);
    }

    public TeamStats GetAwayStats(string team, string? competition = null, int? season = null)
    {
        var tk = TeamNameNormalizer.NormalizeForSearch(team);
        var matches = FindMatches(competition: competition, season: season)
            .Where(m => m.AwayTeamSearchKey.Contains(tk, StringComparison.OrdinalIgnoreCase))
            .ToList();

        int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
        foreach (var m in matches)
        {
            gf += m.AwayGoals; ga += m.HomeGoals;
            if      (m.AwayGoals > m.HomeGoals) wins++;
            else if (m.AwayGoals < m.HomeGoals) losses++;
            else                                draws++;
        }
        return new TeamStats(team, competition ?? "All", season,
                             matches.Count, wins, draws, losses, gf, ga, wins * 3 + draws);
    }

    // ─── standings ────────────────────────────────────────────────────────────

    public record StandingsRow(
        int Rank, string Team,
        int Played, int Wins, int Draws, int Losses,
        int GoalsFor, int GoalsAgainst, int Points)
    {
        public int GoalDifference => GoalsFor - GoalsAgainst;
    }

    public List<StandingsRow> GetStandings(int season, string competition = "Brasileirao")
    {
        var matches = FindMatches(competition: competition, season: season).ToList();

        // Collect all teams
        var teams = matches
            .SelectMany(m => new[] { m.HomeTeamKey })
            .Concat(matches.SelectMany(m => new[] { m.AwayTeamKey }))
            .Distinct()
            .ToHashSet();

        // Build lookup: key → display name (keep first seen)
        var displayName = new Dictionary<string, string>();
        foreach (var m in matches)
        {
            displayName.TryAdd(m.HomeTeamKey, m.HomeTeam);
            displayName.TryAdd(m.AwayTeamKey, m.AwayTeam);
        }

        // pts, wins, draws, losses, gf, ga — played = w+d+l
        var table = new Dictionary<string, (int pts, int w, int d, int l, int gf, int ga)>();
        foreach (var t in teams) table[t] = (0, 0, 0, 0, 0, 0);

        foreach (var m in matches)
        {
            var (hpts, hw, hd, hl, hgf, hga) = table[m.HomeTeamKey];
            var (apts, aw, ad, al, agf, aga) = table[m.AwayTeamKey];

            hgf += m.HomeGoals; hga += m.AwayGoals;
            agf += m.AwayGoals; aga += m.HomeGoals;

            if      (m.HomeGoals > m.AwayGoals) { hw++; al++; hpts += 3; }
            else if (m.HomeGoals < m.AwayGoals) { hl++; aw++; apts += 3; }
            else                                { hd++; ad++; hpts += 1; apts += 1; }

            table[m.HomeTeamKey] = (hpts, hw, hd, hl, hgf, hga);
            table[m.AwayTeamKey] = (apts, aw, ad, al, agf, aga);
        }

        return table
            .Select((kv, _) =>
            {
                var (pts, w, d, l, gf, ga) = kv.Value;
                return new StandingsRow(0,
                    displayName.GetValueOrDefault(kv.Key, kv.Key),
                    w + d + l, w, d, l, gf, ga, pts);
            })
            .OrderByDescending(r => r.Points)
            .ThenByDescending(r => r.GoalDifference)
            .ThenByDescending(r => r.GoalsFor)
            .Select((r, i) => r with { Rank = i + 1 })
            .ToList();
    }

    // ─── player queries ───────────────────────────────────────────────────────

    public IEnumerable<FifaPlayer> FindPlayers(
        string? name        = null,
        string? nationality = null,
        string? club        = null,
        string? position    = null,
        int?    minRating   = null)
    {
        var q = Players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(name))
        {
            var nk = TeamNameNormalizer.NormalizeForSearch(name);
            q = q.Where(p => p.NameKey.Contains(nk, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(nationality))
        {
            var nk = TeamNameNormalizer.NormalizeForSearch(nationality);
            q = q.Where(p => p.NationalityKey.Contains(nk, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(club))
        {
            var ck = TeamNameNormalizer.NormalizeForSearch(club);
            q = q.Where(p => p.ClubKey.Contains(ck, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(position))
            q = q.Where(p => p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));

        if (minRating.HasValue)
            q = q.Where(p => p.Overall >= minRating.Value);

        return q.OrderByDescending(p => p.Overall);
    }

    // ─── aggregated stats ─────────────────────────────────────────────────────

    public double AverageGoalsPerMatch(string? competition = null, int? season = null)
    {
        var ms = FindMatches(competition: competition, season: season).ToList();
        if (ms.Count == 0) return 0;
        return (double)(ms.Sum(m => m.HomeGoals + m.AwayGoals)) / ms.Count;
    }

    public double HomeWinRate(string? competition = null, int? season = null)
    {
        var ms = FindMatches(competition: competition, season: season).ToList();
        if (ms.Count == 0) return 0;
        return (double)ms.Count(m => m.IsHomeWin) / ms.Count * 100;
    }

    public IEnumerable<MatchRecord> BiggestWins(
        string? competition = null, int? season = null, int limit = 10)
    {
        return FindMatches(competition: competition, season: season)
               .OrderByDescending(m => m.GoalDifference)
               .ThenByDescending(m => m.HomeGoals + m.AwayGoals)
               .Take(limit);
    }

    public IEnumerable<(string Team, int Goals, int MatchCount)> TopScoringTeams(
        string? competition = null, int? season = null, int limit = 10)
    {
        var ms = FindMatches(competition: competition, season: season).ToList();
        return ms
            .SelectMany(m => new[]
            {
                (Team: m.HomeTeam, Key: m.HomeTeamKey, Goals: m.HomeGoals),
                (Team: m.AwayTeam, Key: m.AwayTeamKey, Goals: m.AwayGoals),
            })
            .GroupBy(x => x.Key)
            .Select(g =>
            {
                var team = g.First().Team;
                var goals = g.Sum(x => x.Goals);
                return (Team: team, Goals: goals, MatchCount: g.Count());
            })
            .OrderByDescending(x => x.Goals)
            .Take(limit);
    }

    public IEnumerable<(string Team, double WinRate, int Played)> BestHomeRecords(
        string? competition = null, int? season = null, int limit = 10, int minGames = 5)
    {
        var ms = FindMatches(competition: competition, season: season).ToList();
        return ms
            .GroupBy(m => m.HomeTeamKey)
            .Where(g => g.Count() >= minGames)
            .Select(g =>
            {
                var team = g.First().HomeTeam;
                var played = g.Count();
                var wins = g.Count(m => m.IsHomeWin);
                return (Team: team, WinRate: (double)wins / played * 100, Played: played);
            })
            .OrderByDescending(x => x.WinRate)
            .Take(limit);
    }

    public IEnumerable<(string Team, double WinRate, int Played)> BestAwayRecords(
        string? competition = null, int? season = null, int limit = 10, int minGames = 5)
    {
        var ms = FindMatches(competition: competition, season: season).ToList();
        return ms
            .GroupBy(m => m.AwayTeamKey)
            .Where(g => g.Count() >= minGames)
            .Select(g =>
            {
                var team = g.First().AwayTeam;
                var played = g.Count();
                var wins = g.Count(m => m.IsAwayWin);
                return (Team: team, WinRate: (double)wins / played * 100, Played: played);
            })
            .OrderByDescending(x => x.WinRate)
            .Take(limit);
    }
}
