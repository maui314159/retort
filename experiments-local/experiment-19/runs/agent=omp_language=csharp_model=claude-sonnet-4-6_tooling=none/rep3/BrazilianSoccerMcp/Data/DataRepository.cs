using System.Text.RegularExpressions;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Loads all six CSV datasets on construction and exposes query methods used
/// by the MCP tools.  All queries are in-memory; thread-safe for concurrent
/// read access after construction.
/// </summary>
public class DataRepository
{
    public IReadOnlyList<Match> Matches { get; }
    public IReadOnlyList<Player> Players { get; }

    // Distinct values cached for list-tools
    public IReadOnlyList<string> Competitions { get; }
    public IReadOnlyList<int> Seasons { get; }

    public DataRepository(string dataDir)
    {
        var matches = new List<Match>();

        string P(string name) => Path.Combine(dataDir, name);

        if (File.Exists(P("Brasileirao_Matches.csv")))
            matches.AddRange(CsvLoader.LoadBrasileirao(P("Brasileirao_Matches.csv")));

        if (File.Exists(P("Brazilian_Cup_Matches.csv")))
            matches.AddRange(CsvLoader.LoadCopa(P("Brazilian_Cup_Matches.csv")));

        if (File.Exists(P("Libertadores_Matches.csv")))
            matches.AddRange(CsvLoader.LoadLibertadores(P("Libertadores_Matches.csv")));

        if (File.Exists(P("BR-Football-Dataset.csv")))
            matches.AddRange(CsvLoader.LoadBrFootball(P("BR-Football-Dataset.csv")));

        if (File.Exists(P("novo_campeonato_brasileiro.csv")))
            matches.AddRange(CsvLoader.LoadHistorical(P("novo_campeonato_brasileiro.csv")));

        Matches = matches;

        Players = File.Exists(P("fifa_data.csv"))
            ? CsvLoader.LoadFifa(P("fifa_data.csv"))
            : Array.Empty<Player>();

        Competitions = matches
            .Select(m => m.Competition)
            .Where(c => !string.IsNullOrWhiteSpace(c))
            .Distinct()
            .OrderBy(c => c)
            .ToList();

        Seasons = matches
            .Where(m => m.Season.HasValue)
            .Select(m => m.Season!.Value)
            .Distinct()
            .OrderDescending()
            .ToList();
    }

    // -----------------------------------------------------------------------
    // Team name normalisation
    // -----------------------------------------------------------------------

    private static readonly Regex StateSuffixRx =
        new(@"\s*-\s*[A-Z]{2}\s*$", RegexOptions.Compiled);

    public static string NormalizeTeam(string name)
    {
        if (string.IsNullOrWhiteSpace(name)) return string.Empty;
        return StateSuffixRx.Replace(name.Trim(), string.Empty).Trim();
    }

    /// <summary>
    /// Returns true when <paramref name="teamInData"/> is a reasonable match
    /// for the user-supplied <paramref name="query"/>, after normalisation.
    /// Supports partial matching so "Flamengo" matches "Flamengo-RJ".
    /// </summary>
    public static bool TeamMatches(string teamInData, string query)
    {
        if (string.IsNullOrWhiteSpace(query)) return true;
        var a = NormalizeTeam(teamInData);
        var b = NormalizeTeam(query);
        return a.Contains(b, StringComparison.OrdinalIgnoreCase)
            || b.Contains(a, StringComparison.OrdinalIgnoreCase);
    }

    private static bool CompetitionMatches(string competition, string? filter)
    {
        if (string.IsNullOrWhiteSpace(filter) || filter.Equals("all", StringComparison.OrdinalIgnoreCase))
            return true;
        return competition.Contains(filter, StringComparison.OrdinalIgnoreCase);
    }

    // -----------------------------------------------------------------------
    // Match queries
    // -----------------------------------------------------------------------

    /// <summary>
    /// Search matches with optional filters.  When both <paramref name="team"/>
    /// and <paramref name="opponent"/> are provided returns only matches where
    /// the two teams faced each other.
    /// </summary>
    public IReadOnlyList<Match> SearchMatches(
        string? team = null,
        string? opponent = null,
        string? competition = null,
        int? season = null,
        DateTime? dateFrom = null,
        DateTime? dateTo = null,
        int limit = 50)
    {
        var q = Matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(team) && !string.IsNullOrWhiteSpace(opponent))
        {
            // Head-to-head: both orders
            q = q.Where(m =>
                (TeamMatches(m.HomeTeam, team) && TeamMatches(m.AwayTeam, opponent)) ||
                (TeamMatches(m.HomeTeam, opponent) && TeamMatches(m.AwayTeam, team)));
        }
        else if (!string.IsNullOrWhiteSpace(team))
        {
            q = q.Where(m => TeamMatches(m.HomeTeam, team) || TeamMatches(m.AwayTeam, team));
        }

        if (!string.IsNullOrWhiteSpace(competition))
            q = q.Where(m => CompetitionMatches(m.Competition, competition));

        if (season.HasValue)
            q = q.Where(m => m.Season == season);

        if (dateFrom.HasValue)
            q = q.Where(m => m.Date >= dateFrom.Value);

        if (dateTo.HasValue)
            q = q.Where(m => m.Date <= dateTo.Value);

        return q.OrderByDescending(m => m.Date).Take(limit).ToList();
    }

    /// <summary>Compute head-to-head record between two teams across all matches.</summary>
    public (int team1Wins, int team2Wins, int draws, int total) GetHeadToHead(
        string team1, string team2, string? competition = null, int? season = null)
    {
        var matches = SearchMatches(team1, team2, competition, season, limit: int.MaxValue);
        int t1wins = 0, t2wins = 0, draws = 0;
        foreach (var m in matches)
        {
            if (m.IsDraw) { draws++; continue; }
            bool team1IsHome = TeamMatches(m.HomeTeam, team1);
            bool team1Won = (team1IsHome && m.HomeGoals > m.AwayGoals) ||
                            (!team1IsHome && m.AwayGoals > m.HomeGoals);
            if (team1Won) t1wins++; else t2wins++;
        }
        return (t1wins, t2wins, draws, matches.Count);
    }

    // -----------------------------------------------------------------------
    // Team statistics
    // -----------------------------------------------------------------------

    public TeamStats GetTeamStats(
        string team,
        string? competition = null,
        int? season = null,
        bool homeOnly = false)
    {
        var q = Matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
            q = q.Where(m => CompetitionMatches(m.Competition, competition));
        if (season.HasValue)
            q = q.Where(m => m.Season == season);

        IEnumerable<(bool asHome, Match m)> relevant;
        if (homeOnly)
        {
            relevant = q
                .Where(m => TeamMatches(m.HomeTeam, team))
                .Select(m => (true, m));
        }
        else
        {
            relevant = q
                .Where(m => TeamMatches(m.HomeTeam, team) || TeamMatches(m.AwayTeam, team))
                .Select(m => (TeamMatches(m.HomeTeam, team), m));
        }

        int played = 0, wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
        foreach (var (asHome, m) in relevant)
        {
            played++;
            int myGoals = asHome ? m.HomeGoals : m.AwayGoals;
            int theirGoals = asHome ? m.AwayGoals : m.HomeGoals;
            gf += myGoals;
            ga += theirGoals;
            if (myGoals > theirGoals) wins++;
            else if (myGoals == theirGoals) draws++;
            else losses++;
        }

        return new TeamStats(
            Team: team,
            Competition: competition,
            Season: season,
            HomeOnly: homeOnly,
            Played: played,
            Wins: wins,
            Draws: draws,
            Losses: losses,
            GoalsFor: gf,
            GoalsAgainst: ga
        );
    }

    // -----------------------------------------------------------------------
    // League standings
    // -----------------------------------------------------------------------

    /// <summary>
    /// Calculates a league table for Brasileirão using match results.
    /// For seasons from 2012 onward uses the primary Brasileirão dataset;
    /// for 2003-2011 uses the historical dataset.
    /// </summary>
    public IReadOnlyList<Standing> GetStandings(string competition, int season, int topN = 30)
    {
        var source = Matches
            .Where(m => m.Season == season && CompetitionMatches(m.Competition, competition))
            .ToList();

        // If both "Brasileirão" and "Brasileirão Histórico" have data for the
        // same season, prefer the primary source.
        bool hasPrimary = source.Any(m => m.Competition == "Brasileirão");
        bool hasHistoric = source.Any(m => m.Competition == "Brasileirão Histórico");
        if (hasPrimary && hasHistoric)
            source = source.Where(m => m.Competition == "Brasileirão").ToList();

        var table = new Dictionary<string, (int p, int w, int d, int l, int gf, int ga)>(
            StringComparer.OrdinalIgnoreCase);

        void AddTeam(string t)
        {
            var key = NormalizeTeam(t);
            if (!table.ContainsKey(key)) table[key] = default;
        }

        foreach (var m in source)
        {
            var home = NormalizeTeam(m.HomeTeam);
            var away = NormalizeTeam(m.AwayTeam);
            AddTeam(home);
            AddTeam(away);

            var h = table[home];
            var a = table[away];

            h.p++; a.p++;
            h.gf += m.HomeGoals; h.ga += m.AwayGoals;
            a.gf += m.AwayGoals; a.ga += m.HomeGoals;

            if (m.HomeGoals > m.AwayGoals) { h.w++; a.l++; }
            else if (m.HomeGoals < m.AwayGoals) { h.l++; a.w++; }
            else { h.d++; a.d++; }

            table[home] = h;
            table[away] = a;
        }

        return table
            .Select((kv, _) =>
            {
                var (p, w, d, l, gf, ga) = kv.Value;
                int pts = w * 3 + d;
                return (Team: kv.Key, Played: p, Wins: w, Draws: d, Losses: l,
                        GoalsFor: gf, GoalsAgainst: ga, Points: pts,
                        GD: gf - ga);
            })
            .Where(t => t.Played > 0)
            .OrderByDescending(t => t.Points)
            .ThenByDescending(t => t.GD)
            .ThenByDescending(t => t.GoalsFor)
            .Take(topN)
            .Select((t, i) => new Standing(
                Rank: i + 1,
                Team: t.Team,
                Played: t.Played,
                Wins: t.Wins,
                Draws: t.Draws,
                Losses: t.Losses,
                GoalsFor: t.GoalsFor,
                GoalsAgainst: t.GoalsAgainst,
                Points: t.Points))
            .ToList();
    }

    // -----------------------------------------------------------------------
    // Player queries
    // -----------------------------------------------------------------------

    public IReadOnlyList<Player> SearchPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minOverall = null,
        int limit = 30)
    {
        var q = Players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(name))
            q = q.Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(nationality))
            q = q.Where(p => p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(club))
            q = q.Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(position))
            q = q.Where(p => p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));

        if (minOverall.HasValue)
            q = q.Where(p => p.Overall >= minOverall.Value);

        return q.OrderByDescending(p => p.Overall).Take(limit).ToList();
    }

    // -----------------------------------------------------------------------
    // Statistical aggregates
    // -----------------------------------------------------------------------

    public IReadOnlyList<Match> GetBiggestWins(
        string? competition = null,
        int? season = null,
        int count = 10)
    {
        var q = Matches.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(competition))
            q = q.Where(m => CompetitionMatches(m.Competition, competition));
        if (season.HasValue)
            q = q.Where(m => m.Season == season);

        return q
            .OrderByDescending(m => m.GoalDifference)
            .ThenByDescending(m => m.HomeGoals + m.AwayGoals)
            .Take(count)
            .ToList();
    }

    public (double avgGoals, double homeWinRate, double awayWinRate, double drawRate, int totalMatches)
        GetAggregateStats(string? competition = null, int? season = null)
    {
        var q = Matches.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(competition))
            q = q.Where(m => CompetitionMatches(m.Competition, competition));
        if (season.HasValue)
            q = q.Where(m => m.Season == season);

        var list = q.ToList();
        if (list.Count == 0) return (0, 0, 0, 0, 0);

        double totalGoals = list.Sum(m => m.HomeGoals + m.AwayGoals);
        int homeWins = list.Count(m => m.HomeGoals > m.AwayGoals);
        int awayWins = list.Count(m => m.AwayGoals > m.HomeGoals);
        int draws = list.Count(m => m.IsDraw);

        return (
            avgGoals: Math.Round(totalGoals / list.Count, 2),
            homeWinRate: Math.Round((double)homeWins / list.Count * 100, 1),
            awayWinRate: Math.Round((double)awayWins / list.Count * 100, 1),
            drawRate: Math.Round((double)draws / list.Count * 100, 1),
            totalMatches: list.Count
        );
    }

    /// <summary>
    /// Returns the teams with the best home win rate (min 5 home games to qualify).
    /// </summary>
    public IReadOnlyList<(string Team, int Played, int Wins, double WinRate)>
        GetBestHomeRecords(string? competition = null, int? season = null, int topN = 10)
    {
        var q = Matches.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(competition))
            q = q.Where(m => CompetitionMatches(m.Competition, competition));
        if (season.HasValue)
            q = q.Where(m => m.Season == season);

        return q
            .GroupBy(m => NormalizeTeam(m.HomeTeam))
            .Where(g => g.Count() >= 5)
            .Select(g =>
            {
                int played = g.Count();
                int wins = g.Count(m => m.HomeGoals > m.AwayGoals);
                return (Team: g.Key, Played: played, Wins: wins,
                        WinRate: Math.Round((double)wins / played * 100, 1));
            })
            .OrderByDescending(t => t.WinRate)
            .ThenByDescending(t => t.Played)
            .Take(topN)
            .ToList();
    }
}
