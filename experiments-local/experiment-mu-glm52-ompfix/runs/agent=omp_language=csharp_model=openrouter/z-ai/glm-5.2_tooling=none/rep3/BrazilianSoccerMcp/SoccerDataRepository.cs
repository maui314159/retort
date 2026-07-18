// =============================================================================
// BrazilianSoccerMcp - Soccer Data Repository
// -----------------------------------------------------------------------------
// Context: Loads all six Kaggle CSV datasets into memory once (singleton in the
// MCP host) and exposes the query surface used by the MCP tools and the tests.
// Loading is source-agnostic: each file is parsed into the same Match/Player
// models with canonical team keys (see TeamNormalizer) and normalized
// competition names, so a single query can transparently span every file.
//
// Sources:
//   Brasileirao_Matches.csv      -> Brasileirão Série A (2012-2022, has rounds)
//   Brazilian_Cup_Matches.csv    -> Copa do Brasil (2012-2021)
//   Libertadores_Matches.csv     -> Copa Libertadores (2013-2022, has stage)
//   BR-Football-Dataset.csv      -> Serie A/B/C + Copa do Brasil (2014-2023, extended stats)
//   novo_campeonato_brasileiro.csv -> Brasileirão Série A historical (2003-2019)
//   fifa_data.csv                -> FIFA player database (18k+ players)
//
// Notes:
//   * Standings for Série A pick ONE source per season (Brasileirao > Novo >
//     BR-Football) to avoid double-counting overlapping seasons.
//   * Copa do Brasil / Libertadores are knockouts; standings-style tables are
//     not computed for them.
// =============================================================================

using System.Globalization;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Data;

public sealed class SoccerDataRepository
{
    public IReadOnlyList<Match> Matches { get; }
    public IReadOnlyList<Player> Players { get; }
    public IReadOnlyDictionary<string, string> DisplayNames { get; }
    public IReadOnlyCollection<string> TeamKeys { get; }

    public SoccerDataRepository(string dataDirectory)
    {
        if (!Directory.Exists(dataDirectory))
            throw new DirectoryNotFoundException($"Data directory not found: {dataDirectory}");

        var matches = new List<Match>();
        var display = new Dictionary<string, DisplayCandidate>(StringComparer.Ordinal);

        LoadBrasileirao(Path.Combine(dataDirectory, "Brasileirao_Matches.csv"), matches, display);
        LoadCup(Path.Combine(dataDirectory, "Brazilian_Cup_Matches.csv"), matches, display);
        LoadLibertadores(Path.Combine(dataDirectory, "Libertadores_Matches.csv"), matches, display);
        LoadBrFootball(Path.Combine(dataDirectory, "BR-Football-Dataset.csv"), matches, display);
        LoadNovo(Path.Combine(dataDirectory, "novo_campeonato_brasileiro.csv"), matches, display);

        Matches = Deduplicate(matches);
        TeamKeys = display.Keys.ToList();
        DisplayNames = BuildDisplayNames(display);
        Players = LoadFifa(Path.Combine(dataDirectory, "fifa_data.csv"));
    }

    // ----------------------------------------------------------------- loading

    private static void RegisterName(Dictionary<string, DisplayCandidate> display, string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return;
        var key = TeamNormalizer.NormalizeKey(raw);
        if (key.Length == 0) return;
        var candidate = new DisplayCandidate(TeamNormalizer.CleanDisplay(raw),
            TeamNormalizer.AccentCount(raw), TeamNormalizer.CleanDisplay(raw).Length);
        if (!display.TryGetValue(key, out var cur))
            display[key] = candidate;
        else
            display[key] = PickDisplay(cur, candidate);
    }

    private static DisplayCandidate PickDisplay(DisplayCandidate a, DisplayCandidate b)
    {
        // Prefer more accents; tiebreak shorter; tiebreak existing.
        if (b.Accents > a.Accents) return b;
        if (b.Accents == a.Accents && b.Len < a.Len) return b;
        return a;
    }

    private static Dictionary<string, string> BuildDisplayNames(Dictionary<string, DisplayCandidate> display)
    {
        var result = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var (key, val) in display)
            result[key] = TeamNormalizer.DisplayOverride.TryGetValue(key, out var ov) ? ov : val.Name;
        return result;
    }

    private static CsvReader OpenCsv(string path)
    {
        var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HeaderValidated = null,
            MissingFieldFound = null,
            BadDataFound = null,
            IgnoreBlankLines = true,
        });
        csv.Read();
        csv.ReadHeader();
        return csv;
    }

    private static void LoadBrasileirao(string path, List<Match> matches, Dictionary<string, DisplayCandidate> display)
    {
        using var csv = OpenCsv(path);
        while (csv.Read())
        {
            if (!TryParseDate(csv.GetField("datetime"), out var date)) continue;
            if (!TryParseInt(csv.GetField("season"), out var season)) continue;
            var home = csv.GetField("home_team");
            var away = csv.GetField("away_team");
            RegisterName(display, home); RegisterName(display, away);
            matches.Add(new Match
            {
                Competition = "Brasileirão Série A",
                Source = "Brasileirao",
                Date = date,
                HomeTeam = TeamNormalizer.CleanDisplay(home),
                AwayTeam = TeamNormalizer.CleanDisplay(away),
                HomeKey = TeamNormalizer.NormalizeKey(home),
                AwayKey = TeamNormalizer.NormalizeKey(away),
                HomeGoals = ParseInt(csv.GetField("home_goal")),
                AwayGoals = ParseInt(csv.GetField("away_goal")),
                Season = season,
                Round = csv.GetField("round"),
            });
        }
    }

    private static void LoadCup(string path, List<Match> matches, Dictionary<string, DisplayCandidate> display)
    {
        using var csv = OpenCsv(path);
        while (csv.Read())
        {
            if (!TryParseDate(csv.GetField("datetime"), out var date)) continue;
            if (!TryParseInt(csv.GetField("season"), out var season)) continue;
            var home = csv.GetField("home_team");
            var away = csv.GetField("away_team");
            RegisterName(display, home); RegisterName(display, away);
            matches.Add(new Match
            {
                Competition = "Copa do Brasil",
                Source = "Cup",
                Date = date,
                HomeTeam = TeamNormalizer.CleanDisplay(home),
                AwayTeam = TeamNormalizer.CleanDisplay(away),
                HomeKey = TeamNormalizer.NormalizeKey(home),
                AwayKey = TeamNormalizer.NormalizeKey(away),
                HomeGoals = ParseInt(csv.GetField("home_goal")),
                AwayGoals = ParseInt(csv.GetField("away_goal")),
                Season = season,
                Round = csv.GetField("round"),
            });
        }
    }

    private static void LoadLibertadores(string path, List<Match> matches, Dictionary<string, DisplayCandidate> display)
    {
        using var csv = OpenCsv(path);
        while (csv.Read())
        {
            // Skip junk rows (e.g. the "NA" season / "-" goals placeholder row).
            if (!TryParseInt(csv.GetField("season"), out var season)) continue;
            if (!TryParseDate(csv.GetField("datetime"), out var date)) continue;
            var hg = ParseInt(csv.GetField("home_goal"));
            var ag = ParseInt(csv.GetField("away_goal"));
            if (hg < 0 || ag < 0) continue;
            var home = csv.GetField("home_team");
            var away = csv.GetField("away_team");
            RegisterName(display, home); RegisterName(display, away);
            matches.Add(new Match
            {
                Competition = "Copa Libertadores",
                Source = "Libertadores",
                Date = date,
                HomeTeam = TeamNormalizer.CleanDisplay(home),
                AwayTeam = TeamNormalizer.CleanDisplay(away),
                HomeKey = TeamNormalizer.NormalizeKey(home),
                AwayKey = TeamNormalizer.NormalizeKey(away),
                HomeGoals = hg,
                AwayGoals = ag,
                Season = season,
                Stage = csv.GetField("stage"),
            });
        }
    }

    private static void LoadBrFootball(string path, List<Match> matches, Dictionary<string, DisplayCandidate> display)
    {
        using var csv = OpenCsv(path);
        while (csv.Read())
        {
            if (!TryParseDate(csv.GetField("date"), out var date)) continue;
            var home = csv.GetField("home");
            var away = csv.GetField("away");
            RegisterName(display, home); RegisterName(display, away);
            matches.Add(new Match
            {
                Competition = MapBrFootballCompetition(csv.GetField("tournament")),
                Source = "BRFootball",
                Date = date,
                HomeTeam = TeamNormalizer.CleanDisplay(home),
                AwayTeam = TeamNormalizer.CleanDisplay(away),
                HomeKey = TeamNormalizer.NormalizeKey(home),
                AwayKey = TeamNormalizer.NormalizeKey(away),
                HomeGoals = ParseInt(csv.GetField("home_goal")),
                AwayGoals = ParseInt(csv.GetField("away_goal")),
                Season = date.Year,
                Stage = null,
            });
        }
    }

    private static void LoadNovo(string path, List<Match> matches, Dictionary<string, DisplayCandidate> display)
    {
        using var csv = OpenCsv(path);
        while (csv.Read())
        {
            if (!TryParseInt(csv.GetField("Ano"), out var season)) continue;
            // Data is dd/MM/yyyy
            if (!DateTime.TryParseExact(csv.GetField("Data"), "dd/MM/yyyy",
                    CultureInfo.InvariantCulture, DateTimeStyles.None, out var date)) continue;
            var home = csv.GetField("Equipe_mandante");
            var away = csv.GetField("Equipe_visitante");
            RegisterName(display, home); RegisterName(display, away);
            matches.Add(new Match
            {
                Competition = "Brasileirão Série A",
                Source = "Novo",
                Date = date,
                HomeTeam = TeamNormalizer.CleanDisplay(home),
                AwayTeam = TeamNormalizer.CleanDisplay(away),
                HomeKey = TeamNormalizer.NormalizeKey(home),
                AwayKey = TeamNormalizer.NormalizeKey(away),
                HomeGoals = ParseInt(csv.GetField("Gols_mandante")),
                AwayGoals = ParseInt(csv.GetField("Gols_visitante")),
                Season = season,
                Round = csv.GetField("Rodada"),
                Arena = csv.GetField("Arena"),
            });
        }
    }

    private static IReadOnlyList<Player> LoadFifa(string path)
    {
        var players = new List<Player>();
        // The FIFA file has an unnamed leading index column and quoted fields with
        // embedded newlines, so read strictly by column index (CsvHelper handles
        // the multiline quoted fields correctly).
        var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            BadDataFound = null,
            IgnoreBlankLines = true,
        });
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            players.Add(new Player
            {
                Id = ParseInt(csv.GetField(1)),
                Name = csv.GetField(2)?.Trim() ?? "",
                Age = ParseInt(csv.GetField(3)),
                Nationality = csv.GetField(5)?.Trim() ?? "",
                Overall = ParseInt(csv.GetField(7)),
                Potential = ParseInt(csv.GetField(8)),
                Club = csv.GetField(9)?.Trim() ?? "",
                Position = csv.GetField(21)?.Trim() ?? "",
                JerseyNumber = TryParseInt(csv.GetField(22), out var jn) ? jn : null,
                Value = csv.GetField(11)?.Trim(),
                Wage = csv.GetField(12)?.Trim(),
            });
        }
        return players;
    }

    // ------------------------------------------------------------- resolution

    /// <summary>Map a free-text competition token to a canonical competition name.</summary>
    public static string? ResolveCompetition(string? competition)
    {
        if (string.IsNullOrWhiteSpace(competition)) return null;
        var c = TeamNormalizer.StripDiacritics(competition).ToLowerInvariant().Trim();
        return c switch
        {
            "brasileirao" or "serie a" or "seriea" => "Brasileirão Série A",
            "serie b" or "serieb" => "Brasileirão Série B",
            "serie c" or "seriec" => "Brasileirão Série C",
            "copa do brasil" or "brazilian cup" or "cup" or "copa" => "Copa do Brasil",
            "libertadores" or "copa libertadores" => "Copa Libertadores",
            _ when c.Contains("serie a") || c.Contains("brasileirao") => "Brasileirão Série A",
            _ when c.Contains("serie b") => "Brasileirão Série B",
            _ when c.Contains("serie c") => "Brasileirão Série C",
            _ when c.Contains("libertadores") => "Copa Libertadores",
            _ when c.Contains("copa") || c.Contains("cup") => "Copa do Brasil",
            _ => null,
        };
    }

    /// <summary>Resolve a free-text team name to its canonical key (exact, then prefix/contains).</summary>
    public string ResolveTeamKey(string team)
    {
        var key = TeamNormalizer.NormalizeKey(team);
        if (key.Length == 0) return "";
        if (DisplayNames.ContainsKey(key)) return key;
        var prefix = TeamKeys.FirstOrDefault(k => k.StartsWith(key, StringComparison.Ordinal));
        if (prefix != null) return prefix;
        var contains = TeamKeys.FirstOrDefault(k => k.Contains(key, StringComparison.Ordinal));
        return contains ?? key;
    }

    public string DisplayName(string key) =>
        DisplayNames.TryGetValue(key, out var d) ? d : key;

    // ----------------------------------------------------------------- queries

    public IEnumerable<Match> SearchMatches(
        string? team = null, string? opponent = null, string? competition = null,
        int? season = null, DateTime? dateFrom = null, DateTime? dateTo = null)
    {
        var comp = ResolveCompetition(competition);
        var teamKey = string.IsNullOrEmpty(team) ? null : ResolveTeamKey(team);
        var oppKey = string.IsNullOrEmpty(opponent) ? null : ResolveTeamKey(opponent);

        return Matches.Where(m =>
            (comp is null || m.Competition == comp) &&
            (season is null || m.Season == season) &&
            (dateFrom is null || m.Date >= dateFrom) &&
            (dateTo is null || m.Date <= dateTo) &&
            (teamKey is null || m.HomeKey == teamKey || m.AwayKey == teamKey) &&
            (oppKey is null || m.HomeKey == oppKey || m.AwayKey == oppKey));
    }

    public TeamStat GetTeamStatistics(string teamKey, int? season = null, string? competition = null,
        string venue = "any")
    {
        var comp = ResolveCompetition(competition);
        int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0, count = 0;
        foreach (var m in Matches)
        {
            if (season is not null && m.Season != season) continue;
            if (comp is not null && m.Competition != comp) continue;
            bool isHome = m.HomeKey == teamKey;
            bool isAway = m.AwayKey == teamKey;
            if (!isHome && !isAway) continue;
            if (venue.Equals("home", StringComparison.OrdinalIgnoreCase) && !isHome) continue;
            if (venue.Equals("away", StringComparison.OrdinalIgnoreCase) && !isAway) continue;
            count++;
            int mine = isHome ? m.HomeGoals : m.AwayGoals;
            int theirs = isHome ? m.AwayGoals : m.HomeGoals;
            gf += mine; ga += theirs;
            if (mine > theirs) wins++;
            else if (mine < theirs) losses++;
            else draws++;
        }
        return new TeamStat { Team = DisplayName(teamKey), Matches = count, Wins = wins, Draws = draws, Losses = losses, GoalsFor = gf, GoalsAgainst = ga };
    }

    public record HeadToHead(string Team1, string Team2, int Team1Wins, int Team2Wins, int Draws,
        IReadOnlyList<Match> Matches);

    public HeadToHead GetHeadToHead(string team1, string team2, string? competition = null, int? season = null)
    {
        var k1 = ResolveTeamKey(team1);
        var k2 = ResolveTeamKey(team2);
        var comp = ResolveCompetition(competition);
        var list = new List<Match>();
        int w1 = 0, w2 = 0, draws = 0;
        foreach (var m in Matches)
        {
            if (comp is not null && m.Competition != comp) continue;
            if (season is not null && m.Season != season) continue;
            if (!((m.HomeKey == k1 && m.AwayKey == k2) || (m.HomeKey == k2 && m.AwayKey == k1))) continue;
            list.Add(m);
            if (m.IsDraw) draws++;
            else
            {
                var winnerKey = m.IsHomeWin ? m.HomeKey : m.AwayKey;
                if (winnerKey == k1) w1++; else w2++;
            }
        }
        list.Sort((a, b) => b.Date.CompareTo(a.Date));
        return new HeadToHead(DisplayName(k1), DisplayName(k2), w1, w2, draws, list);
    }

    public record StandingRow(string Team, int Played, int Wins, int Draws, int Losses,
        int GoalsFor, int GoalsAgainst, int GoalDiff, int Points, bool Champion, bool Relegated);

    public record Standings(string Competition, int Season, string Source, IReadOnlyList<StandingRow> Rows);

    /// <summary>Compute a league-style standings table for a round-robin competition season.</summary>
    public Standings? GetStandings(string competition, int season)
    {
        var comp = ResolveCompetition(competition);
        if (comp is null) return null;
        var source = ChooseStandingsSource(comp, season);
        if (source is null) return null;

        var agg = new Dictionary<string, (int P, int W, int D, int L, int GF, int GA)>(StringComparer.Ordinal);
        foreach (var m in Matches)
        {
            if (m.Competition != comp || m.Season != season || m.Source != source) continue;
            Accumulate(agg, m.HomeKey, m.HomeGoals, m.AwayGoals);
            Accumulate(agg, m.AwayKey, m.AwayGoals, m.HomeGoals);
        }
        if (agg.Count == 0) return null;

        var rows = agg.Select(kv =>
        {
            var v = kv.Value;
            return new StandingRow(DisplayName(kv.Key), v.P, v.W, v.D, v.L, v.GF, v.GA, v.GF - v.GA, v.W * 3 + v.D, false, false);
        })
        .OrderByDescending(r => r.Points).ThenByDescending(r => r.Wins)
        .ThenByDescending(r => r.GoalDiff).ThenByDescending(r => r.GoalsFor)
        .ThenBy(r => r.Team).ToList();

        if (rows.Count > 0) rows[0] = rows[0] with { Champion = true };
        for (int i = Math.Max(0, rows.Count - 4); i < rows.Count; i++)
            rows[i] = rows[i] with { Relegated = true };

        return new Standings(comp, season, source, rows);
    }

    private static void Accumulate(Dictionary<string, (int, int, int, int, int, int)> agg,
        string key, int gf, int ga)
    {
        if (!agg.TryGetValue(key, out var v)) v = (0, 0, 0, 0, 0, 0);
        int w = v.Item2, d = v.Item3, l = v.Item4;
        if (gf > ga) w++; else if (gf < ga) l++; else d++;
        agg[key] = (v.Item1 + 1, w, d, l, v.Item5 + gf, v.Item6 + ga);
    }

    /// <summary>Pick a single source file for Série A standings to avoid double counting.</summary>
    private string? ChooseStandingsSource(string comp, int season)
    {
        if (comp is "Brasileirão Série A")
        {
            if (season is >= 2012 and <= 2022) return "Brasileirao";
            if (season is >= 2003 and <= 2011) return "Novo";
            if (season is >= 2014 and <= 2023) return "BRFootball";
            return null;
        }
        if (comp is "Brasileirão Série B" or "Brasileirão Série C")
            return "BRFootball";
        return null; // knockout competitions: no league standings
    }

    public IEnumerable<Match> BiggestWins(string? competition = null, int? season = null, int limit = 10) =>
        SearchMatches(competition: competition, season: season)
            .OrderByDescending(m => m.GoalDifference)
            .ThenByDescending(m => m.HomeGoals + m.AwayGoals)
            .Take(limit);

    public record GoalStats(int Matches, double AvgGoals, double HomeWinPct, double AwayWinPct, double DrawPct);

    public GoalStats AverageGoals(string? competition = null, int? season = null)
    {
        var ms = SearchMatches(competition: competition, season: season).ToList();
        if (ms.Count == 0) return new GoalStats(0, 0, 0, 0, 0);
        int totalGoals = ms.Sum(m => m.HomeGoals + m.AwayGoals);
        int hw = ms.Count(m => m.IsHomeWin), aw = ms.Count(m => m.IsAwayWin), dr = ms.Count(m => m.IsDraw);
        double n = ms.Count;
        return new GoalStats(ms.Count, totalGoals / n, hw / n * 100, aw / n * 100, dr / n * 100);
    }

    public IReadOnlyList<string> TeamCompetitions(string team)
    {
        var key = ResolveTeamKey(team);
        return Matches.Where(m => m.HomeKey == key || m.AwayKey == key)
            .Select(m => m.Competition).Distinct().OrderBy(c => c).ToList();
    }

    // Derby definitions keyed by the two canonical team keys.
    private static readonly (string Key1, string Key2, string Name)[] DerbyRivals =
    {
        ("flamengo", "fluminense", "Fla-Flu"),
        ("flamengo", "vasco da gama", "Clássico das Multidões"),
        ("palmeiras", "corinthians", "Clássico Majestoso"),
        ("palmeiras", "sao paulo", "Choque-Rei"),
        ("santos", "sao paulo", "San-São"),
        ("gremio", "internacional", "Gre-Nal"),
        ("cruzeiro", "atletico mg", "Clássico Mineiro"),
        ("atletico pr", "coritiba", "Atletiba"),
        ("bahia", "vitoria", "Ba-Vi"),
        ("sport", "nautico", "Clássico dos Clássicos"),
    };

    public record Derby(string Name, IReadOnlyList<Match> Matches);

    public IEnumerable<Derby> Derbies(int season)
    {
        foreach (var (k1, k2, name) in DerbyRivals)
        {
            var ms = Matches.Where(m => m.Season == season &&
                ((m.HomeKey == k1 && m.AwayKey == k2) || (m.HomeKey == k2 && m.AwayKey == k1)))
                .OrderBy(m => m.Date).ToList();
            if (ms.Count > 0) yield return new Derby(name, ms);
        }
    }

    public IEnumerable<Player> SearchPlayers(
        string? name = null, string? nationality = null, string? club = null,
        string? position = null, int? minOverall = null)
    {
        var natKey = string.IsNullOrEmpty(nationality)
            ? null : TeamNormalizer.StripDiacritics(nationality).ToLowerInvariant().Trim();
        var clubKey = string.IsNullOrEmpty(club)
            ? null : TeamNormalizer.StripDiacritics(club).ToLowerInvariant().Trim();
        var nameKey = string.IsNullOrEmpty(name)
            ? null : TeamNormalizer.StripDiacritics(name).ToLowerInvariant().Trim();
        var posKey = string.IsNullOrEmpty(position)
            ? null : TeamNormalizer.StripDiacritics(position).ToLowerInvariant().Trim();

        return Players.Where(p =>
            (nameKey is null || p.Name.ToLowerInvariant().Contains(nameKey)) &&
            (natKey is null || p.Nationality.ToLowerInvariant() == natKey ||
                p.Nationality.ToLowerInvariant().Contains(natKey)) &&
            (clubKey is null || p.Club.ToLowerInvariant().Contains(clubKey)) &&
            (posKey is null || p.Position.ToLowerInvariant().Contains(posKey)) &&
            (minOverall is null || p.Overall >= minOverall));
    }

    public IReadOnlyList<(string Club, int Count, double AvgRating)> BrazilianClubsSummary()
    {
        var knownBr = new HashSet<string>(StringComparer.Ordinal)
        {
            "flamengo","fluminense","vasco da gama","palmeiras","corinthians","sao paulo",
            "santos","gremio","internacional","cruzeiro","atletico mg","athletico pr",
            "bahia","sport","fortaleza","ceara","coritiba","botafogo","goias","criciuma",
            "chapecoense","figueirense","vitoria","avai","juventude","ponte preta","portuguesa"
        };
        return Players
            .Where(p => p.Nationality.Equals("Brazil", StringComparison.OrdinalIgnoreCase))
            .GroupBy(p => p.Club)
            .Select(g => (Club: g.Key, Count: g.Count(), AvgRating: g.Average(x => x.Overall),
                Key: TeamNormalizer.NormalizeKey(g.Key)))
            .Where(x => knownBr.Contains(x.Key))
            .OrderByDescending(x => x.Count)
            .Select(x => (x.Club, x.Count, x.AvgRating))
            .ToList();
    }

    /// <summary>
    /// Collapse matches that appear in more than one source file (e.g. a 2019
    /// Série A fixture is present in both Brasileirao_Matches.csv and
    /// BR-Football-Dataset.csv). The dedup key is (date, homeKey, awayKey,
    /// homeGoals, awayGoals); when two rows collide the richer source is kept,
    /// where "richer" means: has a round/stage/arena, then Brasileirao &gt;
    /// Novo &gt; Cup &gt; Libertadores &gt; BRFootball (the curated files first).
    /// </summary>
    private static IReadOnlyList<Match> Deduplicate(List<Match> matches)
    {
        var order = new Dictionary<string, int>(StringComparer.Ordinal)
        {
            ["Brasileirao"] = 0, ["Novo"] = 1, ["Cup"] = 2,
            ["Libertadores"] = 3, ["BRFootball"] = 4,
        };
        var seen = new Dictionary<(DateTime, string, string, int, int), Match>();
        var result = new List<Match>(matches.Count);
        foreach (var m in matches)
        {
            var key = (m.Date.Date, m.HomeKey, m.AwayKey, m.HomeGoals, m.AwayGoals);
            if (!seen.TryGetValue(key, out var existing))
            {
                seen[key] = m;
                result.Add(m);
                continue;
            }
            // Keep the richer/better-sourced row.
            if (Better(m, existing, order))
            {
                seen[key] = m;
                var idx = result.IndexOf(existing);
                if (idx >= 0) result[idx] = m;
            }
        }
        return result;
    }

    private static bool Better(Match m, Match existing, Dictionary<string, int> order)
    {
        bool Has(Match x) => !string.IsNullOrEmpty(x.Round) || !string.IsNullOrEmpty(x.Stage) || !string.IsNullOrEmpty(x.Arena);
        if (Has(m) && !Has(existing)) return true;
        if (!Has(m) && Has(existing)) return false;
        order.TryGetValue(m.Source, out var mo); order.TryGetValue(existing.Source, out var eo);
        return mo < eo;
    }

    // ----------------------------------------------------------------- helpers

    private static string MapBrFootballCompetition(string? tournament) => (tournament ?? "") switch
    {
        "Serie A" => "Brasileirão Série A",
        "Serie B" => "Brasileirão Série B",
        "Serie C" => "Brasileirão Série C",
        "Copa do Brasil" => "Copa do Brasil",
        _ => tournament ?? "",
    };

    private static int ParseInt(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return 0;
        s = s.Trim().Trim('"');
        if (double.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
            return (int)d;
        return int.TryParse(s, out var i) ? i : 0;
    }

    private static bool TryParseInt(string? s, out int value)
    {
        value = 0;
        if (string.IsNullOrWhiteSpace(s)) return false;
        s = s.Trim().Trim('"');
        if (double.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
        { value = (int)d; return true; }
        return int.TryParse(s, out value);
    }

    private static bool TryParseDate(string? s, out DateTime value)
    {
        value = default;
        if (string.IsNullOrWhiteSpace(s)) return false;
        s = s.Trim().Trim('"');
        if (DateTime.TryParseExact(s, "yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture, DateTimeStyles.None, out value)) return true;
        if (DateTime.TryParseExact(s, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out value)) return true;
        return DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.None, out value);
    }
}
