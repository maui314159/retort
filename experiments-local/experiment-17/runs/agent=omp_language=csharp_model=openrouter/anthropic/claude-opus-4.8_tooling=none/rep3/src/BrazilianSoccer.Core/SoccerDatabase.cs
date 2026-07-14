// =============================================================================
// File:    SoccerDatabase.cs
// Project: BrazilianSoccer.Core
// Purpose: The query engine. Holds the loaded matches and players (SoccerDataset)
//          and answers every capability category from TASK.md: match search,
//          team records, head-to-head, calculated league standings, player
//          search, and aggregate statistics (avg goals, biggest wins, best
//          home/away records).
// Context: Source-agnostic — operates only on the unified Match/Player model
//          produced by DataLoader. All team matching goes through normalized
//          fold keys (NameNormalizer.Key) so "Palmeiras", "Palmeiras-SP" and
//          "Sociedade Esportiva Palmeiras" resolve to the same team. Standings
//          are recomputed from match results (3pts win / 1 draw) as the spec
//          requires; only completed matches with scores contribute to stats.
//          Match indexes by team key are built once at construction so simple
//          lookups stay well under the 2s budget on the ~24k match corpus.
// =============================================================================

namespace BrazilianSoccer.Core;

/// <summary>Immutable container for the loaded corpus.</summary>
public sealed class SoccerDataset
{
    public IReadOnlyList<Match> Matches { get; }
    public IReadOnlyList<Player> Players { get; }

    public SoccerDataset(IReadOnlyList<Match> matches, IReadOnlyList<Player> players)
    {
        Matches = matches;
        Players = players;
    }
}

public sealed class SoccerDatabase
{
    private readonly SoccerDataset _data;
    // team key -> matches that team played (home or away).
    private readonly Dictionary<string, List<Match>> _byTeam;
    // team key -> chosen display name (most frequent spelling seen).
    private readonly Dictionary<string, string> _display;

    public SoccerDatabase(SoccerDataset data)
    {
        _data = data;
        _byTeam = new Dictionary<string, List<Match>>(StringComparer.Ordinal);

        // Count every spelling per key, then pick the most frequent one as the
        // display name. Frequency is the right signal: the dominant spelling in
        // the corpus is the real club name, while rare variants ("Vasco da Gama
        // RJ", "Fluminense PI") are data noise that a "longest wins" rule would
        // wrongly surface.
        var spellings = new Dictionary<string, Dictionary<string, int>>(StringComparer.Ordinal);
        foreach (var m in data.Matches)
        {
            Index(m.HomeKey, m);
            if (m.AwayKey != m.HomeKey) Index(m.AwayKey, m);
            Count(spellings, m.HomeKey, m.HomeTeam);
            Count(spellings, m.AwayKey, m.AwayTeam);
        }

        _display = new Dictionary<string, string>(spellings.Count, StringComparer.Ordinal);
        foreach (var (key, counts) in spellings)
        {
            string best = key;
            int bestCount = -1;
            foreach (var (name, n) in counts)
            {
                // More frequent wins; ties broken by shorter (drops trailing
                // state noise) then ordinal for determinism.
                if (n > bestCount ||
                    (n == bestCount && (name.Length < best.Length ||
                        (name.Length == best.Length && string.CompareOrdinal(name, best) < 0))))
                {
                    best = name;
                    bestCount = n;
                }
            }
            _display[key] = best;
        }
    }

    private void Index(string key, Match m)
    {
        if (key.Length == 0) return;
        if (!_byTeam.TryGetValue(key, out var list))
            _byTeam[key] = list = new List<Match>();
        list.Add(m);
    }

    private static void Count(Dictionary<string, Dictionary<string, int>> spellings, string key, string name)
    {
        if (key.Length == 0 || name.Length == 0) return;
        if (!spellings.TryGetValue(key, out var counts))
            spellings[key] = counts = new Dictionary<string, int>(StringComparer.Ordinal);
        counts.TryGetValue(name, out var c);
        counts[name] = c + 1;
    }

    /// <summary>Best display name for a team key (the key itself if unknown).</summary>
    public string DisplayName(string key) =>
        _display.TryGetValue(key, out var d) ? d : key;

    public IReadOnlyList<Match> AllMatches => _data.Matches;
    public IReadOnlyList<Player> AllPlayers => _data.Players;

    /// <summary>Loads a database from a data directory.</summary>
    public static SoccerDatabase Load(string dataDir) => new(DataLoader.LoadAll(dataDir));

    // --- Match queries -------------------------------------------------------

    /// <summary>
    /// Finds matches by optional team, opponent, competition, season and date
    /// range. When both team and opponent are given, returns only matches
    /// between exactly those two. Results are sorted newest first.
    /// </summary>
    public IReadOnlyList<Match> FindMatches(
        string? team = null, string? opponent = null,
        Competition? competition = null, int? season = null,
        DateTime? from = null, DateTime? to = null,
        bool homeOnly = false, bool awayOnly = false)
    {
        IEnumerable<Match> source;
        string? teamKey = Normalize(team);
        string? oppKey = Normalize(opponent);

        if (teamKey is not null && _byTeam.TryGetValue(teamKey, out var indexed))
            source = indexed;
        else if (teamKey is not null)
            return Array.Empty<Match>();
        else
            source = _data.Matches;

        var results = new List<Match>();
        foreach (var m in source)
        {
            if (teamKey is not null)
            {
                bool isHome = m.HomeKey == teamKey;
                bool isAway = m.AwayKey == teamKey;
                if (homeOnly && !isHome) continue;
                if (awayOnly && !isAway) continue;
            }

            if (oppKey is not null && m.HomeKey != oppKey && m.AwayKey != oppKey) continue;
            if (competition is not null && m.Competition != competition) continue;
            if (season is not null && m.Season != season) continue;
            if (from is not null && (m.Date is null || m.Date < from)) continue;
            if (to is not null && (m.Date is null || m.Date > to)) continue;

            results.Add(m);
        }

        results.Sort(static (a, b) => Nullable.Compare(b.Date, a.Date));
        return results;
    }

    // --- Team queries --------------------------------------------------------

    /// <summary>Aggregates a team's W/D/L and goals over a filtered match set.</summary>
    public TeamRecord? TeamRecord(
        string team, Competition? competition = null, int? season = null,
        bool homeOnly = false, bool awayOnly = false)
    {
        var key = Normalize(team);
        if (key is null || !_byTeam.TryGetValue(key, out var matches)) return null;

        var record = new TeamRecord { Team = DisplayName(key) };
        foreach (var m in matches)
        {
            if (!m.HasScore) continue;
            if (competition is not null && m.Competition != competition) continue;
            if (season is not null && m.Season != season) continue;

            bool isHome = m.HomeKey == key;
            if (homeOnly && !isHome) continue;
            if (awayOnly && isHome) continue;

            int gf = isHome ? m.HomeGoals!.Value : m.AwayGoals!.Value;
            int ga = isHome ? m.AwayGoals!.Value : m.HomeGoals!.Value;
            record.Add(win: gf > ga, draw: gf == ga, gf, ga);
        }
        return record;
    }

    // --- Head-to-head --------------------------------------------------------

    public HeadToHead? HeadToHead(string teamA, string teamB,
        Competition? competition = null, int? season = null)
    {
        var keyA = Normalize(teamA);
        var keyB = Normalize(teamB);
        if (keyA is null || keyB is null || keyA == keyB) return null;
        if (!_byTeam.TryGetValue(keyA, out var matches)) return null;

        var subset = new List<Match>();
        var h2h = new HeadToHead
        {
            TeamA = DisplayName(keyA),
            TeamB = DisplayName(keyB),
            Matches = subset,
        };

        foreach (var m in matches)
        {
            bool involvesB = m.HomeKey == keyB || m.AwayKey == keyB;
            if (!involvesB) continue;
            if (competition is not null && m.Competition != competition) continue;
            if (season is not null && m.Season != season) continue;
            subset.Add(m);

            if (!m.HasScore) continue;
            bool aHome = m.HomeKey == keyA;
            int aGoals = aHome ? m.HomeGoals!.Value : m.AwayGoals!.Value;
            int bGoals = aHome ? m.AwayGoals!.Value : m.HomeGoals!.Value;
            h2h.TeamAGoals += aGoals;
            h2h.TeamBGoals += bGoals;
            if (aGoals > bGoals) h2h.TeamAWins++;
            else if (bGoals > aGoals) h2h.TeamBWins++;
            else h2h.Draws++;
        }

        subset.Sort(static (a, b) => Nullable.Compare(b.Date, a.Date));
        return h2h;
    }

    // --- Competition standings -----------------------------------------------

    /// <summary>Calculates a league table from match results for a season/competition.</summary>
    public IReadOnlyList<Standing> Standings(Competition competition, int season)
    {
        var records = new Dictionary<string, TeamRecord>(StringComparer.Ordinal);

        foreach (var m in _data.Matches)
        {
            if (m.Competition != competition || m.Season != season || !m.HasScore) continue;

            var home = GetOrAdd(records, m.HomeKey);
            var away = GetOrAdd(records, m.AwayKey);
            int hg = m.HomeGoals!.Value, ag = m.AwayGoals!.Value;
            home.Add(win: hg > ag, draw: hg == ag, hg, ag);
            away.Add(win: ag > hg, draw: hg == ag, ag, hg);
        }

        var standings = records.Values
            .OrderByDescending(r => r.Points)
            .ThenByDescending(r => r.GoalDifference)
            .ThenByDescending(r => r.GoalsFor)
            .ThenBy(r => r.Team, StringComparer.OrdinalIgnoreCase)
            .Select((r, i) => new Standing { Position = i + 1, Record = r })
            .ToList();
        return standings;
    }

    // --- Player queries ------------------------------------------------------

    /// <summary>Searches players by name substring, nationality, club, position.</summary>
    public IReadOnlyList<Player> FindPlayers(
        string? name = null, string? nationality = null,
        string? club = null, string? position = null, int limit = 50)
    {
        var nameKey = Normalize(name);
        var clubKey = Normalize(club);

        IEnumerable<Player> q = _data.Players;
        if (nameKey is not null) q = q.Where(p => p.NameKey.Contains(nameKey, StringComparison.Ordinal));
        if (clubKey is not null) q = q.Where(p => p.ClubKey.Contains(clubKey, StringComparison.Ordinal));
        if (!string.IsNullOrWhiteSpace(nationality))
            q = q.Where(p => p.Nationality.Equals(nationality.Trim(), StringComparison.OrdinalIgnoreCase));
        if (!string.IsNullOrWhiteSpace(position))
            q = q.Where(p => p.Position.Equals(position.Trim(), StringComparison.OrdinalIgnoreCase));

        return q.OrderByDescending(p => p.Overall)
                .ThenBy(p => p.Name, StringComparer.OrdinalIgnoreCase)
                .Take(Math.Max(1, limit))
                .ToList();
    }

    // --- Statistics ----------------------------------------------------------

    /// <summary>Average goals per match over a filtered, scored subset.</summary>
    public (int Matches, double AverageGoals, double HomeWinRate) GoalStats(
        Competition? competition = null, int? season = null)
    {
        int count = 0, goals = 0, homeWins = 0;
        foreach (var m in _data.Matches)
        {
            if (!m.HasScore) continue;
            if (competition is not null && m.Competition != competition) continue;
            if (season is not null && m.Season != season) continue;
            count++;
            goals += m.TotalGoals;
            if (m.Outcome == MatchOutcome.HomeWin) homeWins++;
        }
        return count == 0
            ? (0, 0, 0)
            : (count, (double)goals / count, (double)homeWins / count);
    }

    /// <summary>Biggest victories (largest goal margin) over a filtered subset.</summary>
    public IReadOnlyList<Match> BiggestWins(
        Competition? competition = null, int? season = null, int limit = 10)
    {
        IEnumerable<Match> q = _data.Matches.Where(m => m.HasScore);
        if (competition is not null) q = q.Where(m => m.Competition == competition);
        if (season is not null) q = q.Where(m => m.Season == season);
        return q.OrderByDescending(m => Math.Abs(m.HomeGoals!.Value - m.AwayGoals!.Value))
                .ThenByDescending(m => m.TotalGoals)
                .Take(Math.Max(1, limit))
                .ToList();
    }

    /// <summary>Ranks teams by win rate for home or away matches (min games filter).</summary>
    public IReadOnlyList<TeamRecord> BestRecords(
        bool homeOnly, Competition? competition = null, int? season = null,
        int minPlayed = 5, int limit = 10)
    {
        var records = new Dictionary<string, TeamRecord>(StringComparer.Ordinal);
        foreach (var m in _data.Matches)
        {
            if (!m.HasScore) continue;
            if (competition is not null && m.Competition != competition) continue;
            if (season is not null && m.Season != season) continue;

            if (homeOnly)
            {
                var r = GetOrAdd(records, m.HomeKey);
                r.Add(m.HomeGoals!.Value > m.AwayGoals!.Value,
                      m.HomeGoals.Value == m.AwayGoals.Value,
                      m.HomeGoals.Value, m.AwayGoals.Value);
            }
            else
            {
                var r = GetOrAdd(records, m.AwayKey);
                r.Add(m.AwayGoals!.Value > m.HomeGoals!.Value,
                      m.AwayGoals.Value == m.HomeGoals.Value,
                      m.AwayGoals.Value, m.HomeGoals.Value);
            }
        }

        return records.Values
            .Where(r => r.Played >= minPlayed)
            .OrderByDescending(r => r.WinRate)
            .ThenByDescending(r => r.GoalDifference)
            .Take(Math.Max(1, limit))
            .ToList();
    }

    /// <summary>Lists the competitions a team has appeared in (with match counts).</summary>
    public IReadOnlyList<(Competition Competition, int Matches)> CompetitionsForTeam(string team)
    {
        var key = Normalize(team);
        if (key is null || !_byTeam.TryGetValue(key, out var matches)) return Array.Empty<(Competition, int)>();
        return matches.GroupBy(m => m.Competition)
            .Select(g => (g.Key, g.Count()))
            .OrderByDescending(t => t.Item2)
            .ToList();
    }

    /// <summary>Resolves a free-text team name to its canonical display spelling.</summary>
    public string ResolveDisplayName(string team)
    {
        var key = Normalize(team);
        return key is not null ? DisplayName(key) : NameNormalizer.Display(team);
    }

    // --- internals -----------------------------------------------------------

    private static string? Normalize(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        var k = NameNormalizer.Key(s);
        return k.Length == 0 ? null : k;
    }

    private TeamRecord GetOrAdd(Dictionary<string, TeamRecord> map, string key)
    {
        if (!map.TryGetValue(key, out var r))
            map[key] = r = new TeamRecord { Team = DisplayName(key) };
        return r;
    }
}
