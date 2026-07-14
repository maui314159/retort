// BrazilianSoccerMcp.Core - Query service.
// The single entry point for all MCP tools. It indexes all loaded matches and
// players by full team identity (base+state) so distinct same-base clubs
// (Atletico-MG vs Atletico-PR) stay separate in standings, while bare-name
// queries ("all Atletico matches") aggregate across states as users expect.
using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Models;

namespace BrazilianSoccerMcp.Core.Services;

public sealed class SoccerQueryService
{
    private readonly IReadOnlyList<Match> _matches;
    private readonly IReadOnlyList<Player> _players;

    // fullKey -> display ("Atletico-MG"), keyed by canonical identity.
    private readonly Dictionary<string, string> _fullDisplay = new(StringComparer.Ordinal);
    // fullKey -> matches involving that team.
    private readonly Dictionary<string, List<Match>> _byFull = new(StringComparer.Ordinal);
    // baseKey -> set of fullKeys (for resolving bare-name queries & derbies).
    private readonly Dictionary<string, HashSet<string>> _baseToFulls = new(StringComparer.Ordinal);
    // baseKey -> display base name ("Atletico").
    private readonly Dictionary<string, string> _baseDisplay = new(StringComparer.Ordinal);

    public SoccerQueryService(IReadOnlyList<Match> matches, IReadOnlyList<Player> players)
    {
        _matches = matches;
        _players = players;

        foreach (var m in matches)
        {
            IndexTeam(m.HomeTeam, m);
            IndexTeam(m.AwayTeam, m);
        }

        // Finalize display names: use the bare base name when the base maps to
        // exactly one club (e.g. "Flamengo"); keep the state suffix only for
        // same-base clubs that need disambiguation (e.g. "Atletico-MG").
        foreach (var (baseKey, fulls) in _baseToFulls)
        {
            var bare = _baseDisplay[baseKey];
            foreach (var full in fulls)
            {
                if (fulls.Count == 1) _fullDisplay[full] = bare;
                else _fullDisplay[full] = TeamNameNormalizer.DisplayName(_fullDisplay[full]);
            }
        }
    }

    public IReadOnlyList<Match> AllMatches => _matches;
    public IReadOnlyList<Player> AllPlayers => _players;
    public IEnumerable<string> KnownTeams => _fullDisplay.Values;

    private void IndexTeam(string rawName, Match m)
    {
        if (string.IsNullOrWhiteSpace(rawName)) return;
        var full = TeamNameNormalizer.FullKey(rawName);
        if (full.Length == 0 || full == "|") return;

        if (!_byFull.TryGetValue(full, out var list))
        {
            list = new List<Match>();
            _byFull[full] = list;
        }
        list.Add(m);

        var display = TeamNameNormalizer.DisplayName(rawName);
        var baseName = TeamNameNormalizer.BaseName(rawName);
        var baseKey = TeamNameNormalizer.BaseKey(rawName);

        _fullDisplay.TryGetValue(full, out var existing);
        if (existing is null || display.Length < existing.Length) _fullDisplay[full] = display;
        if (baseKey.Length > 0)
        {
            if (!_baseToFulls.TryGetValue(baseKey, out var set)) { set = new HashSet<string>(StringComparer.Ordinal); _baseToFulls[baseKey] = set; }
            set.Add(full);
            if (!_baseDisplay.TryGetValue(baseKey, out var b) || baseName.Length < b.Length) _baseDisplay[baseKey] = baseName;
        }
    }

    // ---------------------------------------------------------------------
    // Resolution helpers
    // ---------------------------------------------------------------------

    /// <summary>
    /// Resolves a user-supplied team name to a canonical display name.
    /// If the name carries a state, the unique full identity is used. If the
    /// bare name maps to exactly one club, that club is used. Otherwise the
    /// bare display name is returned (queries will aggregate across states).
    /// </summary>
    public string ResolveTeam(string teamName)
    {
        var full = TeamNameNormalizer.FullKey(teamName);
        var state = TeamNameNormalizer.StateCode(teamName);
        if (state.Length > 0 && _fullDisplay.TryGetValue(full, out var d)) return d;
        var baseKey = TeamNameNormalizer.BaseKey(teamName);
        if (baseKey.Length > 0 && _baseToFulls.TryGetValue(baseKey, out var fulls))
        {
            if (fulls.Count == 1) return _fullDisplay[fulls.First()];
            return _baseDisplay.TryGetValue(baseKey, out var b) ? b : TeamNameNormalizer.BaseName(teamName);
        }
        return TeamNameNormalizer.DisplayName(teamName);
    }

    /// <summary>Returns the set of full team identities matching a (possibly bare) name.</summary>
    private IEnumerable<string> ResolveFulls(string teamName)
    {
        var full = TeamNameNormalizer.FullKey(teamName);
        var state = TeamNameNormalizer.StateCode(teamName);
        if (state.Length > 0)
        {
            if (_byFull.ContainsKey(full)) return new[] { full };
            return Array.Empty<string>();
        }
        var baseKey = TeamNameNormalizer.BaseKey(teamName);
        return _baseToFulls.TryGetValue(baseKey, out var set) ? set.ToArray() : Array.Empty<string>();
    }

    // ---------------------------------------------------------------------
    // Match queries
    // ---------------------------------------------------------------------

    public IReadOnlyList<Match> FindMatchesByTeam(
        string teamName,
        Competition? competition = null, int? season = null,
        DateTime? from = null, DateTime? to = null)
    {
        var matches = new List<Match>();
        foreach (var full in ResolveFulls(teamName))
        {
            if (_byFull.TryGetValue(full, out var list))
                matches.AddRange(list.Where(m => PassesFilters(m, competition, season, from, to)));
        }
        return matches.OrderBy(m => m.Date).ToList();
    }

    public IReadOnlyList<Match> FindMatchesBetweenTeams(
        string teamA, string teamB,
        Competition? competition = null, int? season = null)
    {
        var fullsA = ResolveFulls(teamA);
        var fullsB = ResolveFulls(teamB);
        var setA = new HashSet<string>(fullsA, StringComparer.Ordinal);
        var setB = new HashSet<string>(fullsB, StringComparer.Ordinal);
        return _matches.Where(m =>
            {
                var h = TeamNameNormalizer.FullKey(m.HomeTeam);
                var a = TeamNameNormalizer.FullKey(m.AwayTeam);
                return (setA.Contains(h) && setB.Contains(a)) ||
                       (setA.Contains(a) && setB.Contains(h));
            })
            .Where(m => PassesFilters(m, competition, season))
            .OrderBy(m => m.Date).ToList();
    }

    public Match? FindMostRecentMatch(string teamA, string teamB)
        => FindMatchesBetweenTeams(teamA, teamB).MaxBy(m => m.Date);

    // ---------------------------------------------------------------------
    // Team stats
    // ---------------------------------------------------------------------

    public TeamStats GetTeamStats(
        string teamName, Competition? competition = null, int? season = null)
    {
        var fulls = ResolveFulls(teamName).ToList();
        var matches = FindMatchesByTeam(teamName, competition, season);
        int w = 0, d = 0, l = 0, gf = 0, ga = 0;
        int hw = 0, hd = 0, hl = 0, aw = 0, ad = 0, al = 0;
        foreach (var m in matches)
        {
            bool isHome = fulls.Contains(TeamNameNormalizer.FullKey(m.HomeTeam));
            int forGoals = isHome ? m.HomeGoal : m.AwayGoal;
            int against = isHome ? m.AwayGoal : m.HomeGoal;
            gf += forGoals; ga += against;
            if (forGoals > against) { w++; if (isHome) hw++; else aw++; }
            else if (forGoals == against) { d++; if (isHome) hd++; else ad++; }
            else { l++; if (isHome) hl++; else al++; }
        }
        return new TeamStats
        {
            Team = ResolveTeam(teamName),
            Matches = matches.Count,
            Wins = w, Draws = d, Losses = l,
            GoalsFor = gf, GoalsAgainst = ga,
            HomeMatches = hw + hd + hl, HomeWins = hw, HomeDraws = hd, HomeLosses = hl,
            AwayMatches = aw + ad + al, AwayWins = aw, AwayDraws = ad, AwayLosses = al,
            Points = w * 3 + d
        };
    }

    public HeadToHead GetHeadToHead(string teamA, string teamB)
    {
        var fullsA = ResolveFulls(teamA).ToHashSet(StringComparer.Ordinal);
        var fullsB = ResolveFulls(teamB).ToHashSet(StringComparer.Ordinal);
        var matches = FindMatchesBetweenTeams(teamA, teamB);
        int aw = 0, bw = 0, dr = 0;
        foreach (var m in matches)
        {
            var hFull = TeamNameNormalizer.FullKey(m.HomeTeam);
            var aFull = TeamNameNormalizer.FullKey(m.AwayTeam);
            bool aHome = fullsA.Contains(hFull);
            int aGoals = aHome ? m.HomeGoal : m.AwayGoal;
            int bGoals = aHome ? m.AwayGoal : m.HomeGoal;
            if (aGoals > bGoals) aw++;
            else if (aGoals < bGoals) bw++;
            else dr++;
        }
        return new HeadToHead
        {
            TeamA = ResolveTeam(teamA), TeamB = ResolveTeam(teamB),
            TeamAWins = aw, TeamBWins = bw, Draws = dr,
            Matches = matches.Count, MatchesList = matches
        };
    }

    // ---------------------------------------------------------------------
    // Standings
    // ---------------------------------------------------------------------

    public IEnumerable<int> AvailableSeasons(Competition? competition = null) =>
        _matches.Where(m => competition == null || m.Competition == competition)
                .Select(m => m.Season).Distinct().OrderBy(s => s);

    public IReadOnlyList<StandingsRow> GetStandings(int season, Competition competition)
    {
        var seasonMatches = _matches.Where(m => m.Season == season && m.Competition == competition).ToList();
        var table = new Dictionary<string, StandingsAcc>(StringComparer.Ordinal);
        foreach (var m in seasonMatches)
        {
            Acc(table, m.HomeTeam, m.HomeGoal, m.AwayGoal);
            Acc(table, m.AwayTeam, m.AwayGoal, m.HomeGoal);
        }

        // Local display: within this season/competition table, show the bare
        // base name when only one club with that base name appears (e.g.
        // "Flamengo"); keep the state suffix when two same-base clubs are both
        // in the table (e.g. "Atletico-MG" vs "Atletico-PR").
        var baseCounts = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var full in table.Keys)
        {
            var baseKey = BaseKeyOf(full);
            if (baseKey.Length == 0) continue;
            baseCounts[baseKey] = baseCounts.TryGetValue(baseKey, out var c) ? c + 1 : 1;
        }

        string DisplayFor(string full)
        {
            var baseKey = BaseKeyOf(full);
            if (baseKey.Length > 0 &&
                baseCounts.TryGetValue(baseKey, out var c) && c == 1 &&
                _baseDisplay.TryGetValue(baseKey, out var bare))
                return bare;
            return _fullDisplay.TryGetValue(full, out var d) ? d
                : TeamNameNormalizer.DisplayName(full);
        }

        var rows = table.Select(kv =>
            {
                var a = kv.Value;
                return new StandingsRow
                {
                    Team = DisplayFor(kv.Key),
                    Played = a.Played, Wins = a.Wins, Draws = a.Draws, Losses = a.Losses,
                    GoalsFor = a.GoalsFor, GoalsAgainst = a.GoalsAgainst,
                    Points = a.Wins * 3 + a.Draws
                };
            })
            .OrderByDescending(r => r.Points)
            .ThenByDescending(r => r.GoalDifference)
            .ThenByDescending(r => r.GoalsFor)
            .ThenBy(r => r.Team)
            .Select((r, i) => r with { Position = i + 1 })
            .ToList();

        if (rows.Count > 0) rows[0] = rows[0] with { Champion = true };
        return rows;
    }

    private static string BaseKeyOf(string fullKey)
    {
        var bar = fullKey.IndexOf('|');
        return bar < 0 ? fullKey : fullKey.Substring(0, bar);
    }

    private void Acc(Dictionary<string, StandingsAcc> table, string team, int gf, int ga)
    {
        var full = TeamNameNormalizer.FullKey(team);
        if (full.Length == 0 || full == "|") return;
        if (!table.TryGetValue(full, out var acc)) { acc = new StandingsAcc(); table[full] = acc; }
        acc.Played++;
        acc.GoalsFor += gf; acc.GoalsAgainst += ga;
        if (gf > ga) acc.Wins++; else if (gf == ga) acc.Draws++; else acc.Losses++;
    }

    private sealed class StandingsAcc
    {
        public int Played, Wins, Draws, Losses, GoalsFor, GoalsAgainst;
    }

    // ---------------------------------------------------------------------
    // Statistics
    // ---------------------------------------------------------------------

    public double AverageGoalsPerMatch(Competition? competition = null, int? season = null)
    {
        var subset = _matches.Where(m => PassesFilters(m, competition, season)).ToList();
        if (subset.Count == 0) return 0;
        return (double)subset.Sum(m => m.HomeGoal + m.AwayGoal) / subset.Count;
    }

    public (double HomeWinRate, double DrawRate, double AwayWinRate) WinRateBreakdown(
        Competition? competition = null, int? season = null)
    {
        var subset = _matches.Where(m => PassesFilters(m, competition, season)).ToList();
        if (subset.Count == 0) return (0, 0, 0);
        int hw = subset.Count(m => m.HomeGoal > m.AwayGoal);
        int dr = subset.Count(m => m.HomeGoal == m.AwayGoal);
        int aw = subset.Count(m => m.HomeGoal < m.AwayGoal);
        double n = subset.Count;
        return (hw / n, dr / n, aw / n);
    }

    public IReadOnlyList<Match> BiggestWins(
        Competition? competition = null, int? season = null, int top = 10)
        => _matches.Where(m => PassesFilters(m, competition, season))
                   .OrderByDescending(m => m.GoalDifference)
                   .ThenByDescending(m => m.HomeGoal + m.AwayGoal)
                   .Take(top).ToList();

    public IReadOnlyList<TeamStats> BestAwayRecords(
        Competition? competition = null, int? season = null, int minMatches = 10)
        => _fullDisplay.Keys
            .Select(k => GetTeamStats(_fullDisplay[k], competition, season))
            .Where(s => s.AwayMatches >= minMatches)
            .OrderByDescending(s => s.AwayWinRate).ThenByDescending(s => s.AwayWins).ToList();

    public IReadOnlyList<TeamStats> BestHomeRecords(
        Competition? competition = null, int? season = null, int minMatches = 10)
        => _fullDisplay.Keys
            .Select(k => GetTeamStats(_fullDisplay[k], competition, season))
            .Where(s => s.HomeMatches >= minMatches)
            .OrderByDescending(s => s.HomeWinRate).ThenByDescending(s => s.HomeWins).ToList();

    public TeamStats? TopScoringTeam(
        Competition? competition = null, int? season = null)
        => _fullDisplay.Keys
            .Select(k => GetTeamStats(_fullDisplay[k], competition, season))
            .OrderByDescending(s => s.GoalsFor).FirstOrDefault();

    // ---------------------------------------------------------------------
    // Players
    // ---------------------------------------------------------------------

    public IReadOnlyList<Player> FindPlayers(
        string? name = null, string? nationality = null, string? club = null,
        string? position = null, int? minOverall = null, int? maxOverall = null, int? top = null)
    {
        var q = _players.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(name))
        {
            var nm = name.Trim();
            q = q.Where(p => p.Name.Contains(nm, StringComparison.OrdinalIgnoreCase));
        }
        if (!string.IsNullOrWhiteSpace(nationality))
            q = q.Where(p => p.Nationality.Equals(nationality, StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(club))
        {
            var c = club.Trim();
            q = q.Where(p => p.Club.Contains(c, StringComparison.OrdinalIgnoreCase));
        }
        if (!string.IsNullOrWhiteSpace(position))
            q = q.Where(p => p.Position.Equals(position, StringComparison.OrdinalIgnoreCase));
        if (minOverall.HasValue) q = q.Where(p => p.Overall >= minOverall.Value);
        if (maxOverall.HasValue) q = q.Where(p => p.Overall <= maxOverall.Value);
        q = q.OrderByDescending(p => p.Overall);
        if (top.HasValue) q = q.Take(top.Value);
        return q.ToList();
    }

    public IReadOnlyList<Player> TopBrazilianPlayers(int top = 10)
        => _players.Where(p => p.IsBrazilian)
                   .OrderByDescending(p => p.Overall).Take(top).ToList();

    public IReadOnlyList<Player> PlayersAtClub(string club, int? top = null)
        => FindPlayers(club: club, top: top);

    public IReadOnlyList<(string Club, int Count, double AvgRating)> BrazilianPlayersAtBrazilianClubs()
    {
        var clubFulls = new HashSet<string>(_fullDisplay.Keys, StringComparer.Ordinal);
        return _players
            .Where(p => p.IsBrazilian && !string.IsNullOrWhiteSpace(p.Club))
            .GroupBy(p => p.Club)
            .Where(g => clubFulls.Contains(TeamNameNormalizer.FullKey(g.Key)))
            .Select(g => (Club: g.Key, Count: g.Count(), AvgRating: g.Average(p => p.Overall)))
            .OrderByDescending(t => t.Count).ToList();
    }

    // ---------------------------------------------------------------------
    // Derbies
    // ---------------------------------------------------------------------

    private static readonly (string A, string B)[] DerbyRivals =
    {
        ("Flamengo","Fluminense"), ("Flamengo","Vasco"), ("Vasco","Flamengo"),
        ("Corinthians","Palmeiras"), ("Corinthians","São Paulo"), ("Palmeiras","São Paulo"),
        ("Santos","São Paulo"), ("Santos","Corinthians"),
        ("Grêmio","Internacional"), ("Internacional","Grêmio"),
        ("Atlético-MG","Cruzeiro"), ("Cruzeiro","Atlético Mineiro"),
        ("Bahia","Vitória"), ("Fortaleza","Ceará"),
        ("Sport","Náutico"), ("Coritiba","Athletico-PR"),
    };

    public IReadOnlyList<Match> FindDerbies(int? season = null, Competition? competition = null)
    {
        var rivalBases = DerbyRivals
            .Select(p => (A: TeamNameNormalizer.BaseKey(p.A), B: TeamNameNormalizer.BaseKey(p.B)))
            .Where(p => p.A.Length > 0 && p.B.Length > 0)
            .ToHashSet();

        bool IsDerby(Match m)
        {
            var h = TeamNameNormalizer.BaseKey(m.HomeTeam);
            var a = TeamNameNormalizer.BaseKey(m.AwayTeam);
            return rivalBases.Contains((h, a));
        }

        return _matches.Where(m => PassesFilters(m, competition, season) && IsDerby(m))
                       .OrderBy(m => m.Date).ToList();
    }

    // ---------------------------------------------------------------------
    private static bool PassesFilters(Match m, Competition? competition, int? season = null,
        DateTime? from = null, DateTime? to = null)
    {
        if (competition.HasValue && m.Competition != competition.Value) return false;
        if (season.HasValue && m.Season != season.Value) return false;
        if (from.HasValue && m.Date < from.Value) return false;
        if (to.HasValue && m.Date > to.Value) return false;
        return true;
    }
}
