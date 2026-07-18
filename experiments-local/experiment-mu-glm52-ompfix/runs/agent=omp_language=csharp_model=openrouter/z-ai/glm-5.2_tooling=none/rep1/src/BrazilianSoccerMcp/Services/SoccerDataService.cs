// Brazilian Soccer MCP Server - Core soccer data service
//
// Context: This is the single in-memory data store backing every MCP tool. It
// loads all six bundled CSV datasets on startup (once, eagerly) and exposes
// query methods that the tool layer calls. Match records are normalized into a
// unified Match shape and indexed by canonical team key so cross-dataset and
// head-to-head queries are simple lookups rather than repeated string parsing.
//
// Loading strategy: CsvHelper reads with InvariantCulture and a header-aware
// reader so the heterogeneous column orders/layouts across the five match files
// are each handled by a dedicated, tolerant loader. Goal values appear as ints,
// quoted strings ("2"), and floats ("1.0") depending on the file, so a shared
// coercion helper normalizes them. Dates appear as ISO ("2012-05-19 18:30:00")
// and Brazilian ("29/03/2003"); both are parsed.

using System.Globalization;
using BrazilianSoccerMcp.Models;
using CsvHelper.Configuration;
using CsvHelper;
using System.Diagnostics;

namespace BrazilianSoccerMcp.Services;

/// <summary>
/// Loads the bundled Kaggle datasets into memory and answers structured queries
/// about matches, teams, players, competitions, and statistics.
/// </summary>
public sealed class SoccerDataService
{
    private readonly List<Match> _matches = [];
    private readonly List<Player> _players = [];
    private readonly Dictionary<string, string> _teamKeyToDisplay = new(StringComparer.OrdinalIgnoreCase);
    private bool _loaded;

    /// <summary>Path to the directory containing the CSV files.</summary>
    public string DataDirectory { get; }

    public IReadOnlyList<Match> Matches => _matches;
    public IReadOnlyList<Player> Players => _players;

    public SoccerDataService(string? dataDirectory = null)
    {
        DataDirectory = dataDirectory ?? DataPathResolver.ResolveDataDirectory();
    }

    /// <summary>Loads all datasets if not already loaded. Safe to call repeatedly.</summary>
    public void EnsureLoaded()
    {
        if (_loaded) return;
        _loaded = true;

        LoadBrasileiraoMatches();
        LoadCupMatches();
        LoadLibertadoresMatches();
        LoadExtendedStats();
        LoadHistoricalBrasileirao();
        LoadFifaPlayers();

        // Sort matches chronologically so "most recent" queries and ordered
        // output don't need to re-sort per call.
        _matches.Sort((a, b) =>
        {
            if (!a.Date.HasValue && !b.Date.HasValue) return 0;
            if (!a.Date.HasValue) return 1;
            if (!b.Date.HasValue) return -1;
            return a.Date.Value.CompareTo(b.Date.Value);
        });
    }

    private string PathFor(string file) => Path.Combine(DataDirectory, file);

    private void LoadBrasileiraoMatches()
    {
        LoadCsv(PathFor("Brasileirao_Matches.csv"), row =>
        {
            var home = row.GetField<string>("home_team") ?? "";
            var away = row.GetField<string>("away_team") ?? "";
            _matches.Add(new Match
            {
                Competition = "Brasileirão",
                Source = "Brasileirao_Matches.csv",
                HomeTeam = TeamNameNormalizer.StripSuffix(home),
                AwayTeam = TeamNameNormalizer.StripSuffix(away),
                HomeTeamKey = TeamNameNormalizer.CanonicalKey(home),
                AwayTeamKey = TeamNameNormalizer.CanonicalKey(away),
                HomeGoals = ParseInt(row.GetField("home_goal")),
                AwayGoals = ParseInt(row.GetField("away_goal")),
                Date = ParseDate(row.GetField<string>("datetime")),
                Season = ParseInt(row.GetField("season")),
                Round = "Round " + row.GetField<string>("round"),
                HomeState = row.GetField<string>("home_team_state"),
                AwayState = row.GetField<string>("away_team_state"),
            });
            RegisterTeam(home);
            RegisterTeam(away);
        });
    }

    private void LoadCupMatches()
    {
        LoadCsv(PathFor("Brazilian_Cup_Matches.csv"), row =>
        {
            var home = row.GetField<string>("home_team") ?? "";
            var away = row.GetField<string>("away_team") ?? "";
            _matches.Add(new Match
            {
                Competition = "Copa do Brasil",
                Source = "Brazilian_Cup_Matches.csv",
                HomeTeam = TeamNameNormalizer.StripSuffix(home),
                AwayTeam = TeamNameNormalizer.StripSuffix(away),
                HomeTeamKey = TeamNameNormalizer.CanonicalKey(home),
                AwayTeamKey = TeamNameNormalizer.CanonicalKey(away),
                HomeGoals = ParseInt(row.GetField("home_goal")),
                AwayGoals = ParseInt(row.GetField("away_goal")),
                Date = ParseDate(row.GetField<string>("datetime")),
                Season = ParseInt(row.GetField("season")),
                Round = row.GetField<string>("round"),
            });
            RegisterTeam(home);
            RegisterTeam(away);
        });
    }

    private void LoadLibertadoresMatches()
    {
        LoadCsv(PathFor("Libertadores_Matches.csv"), row =>
        {
            var home = row.GetField<string>("home_team") ?? "";
            var away = row.GetField<string>("away_team") ?? "";
            _matches.Add(new Match
            {
                Competition = "Copa Libertadores",
                Source = "Libertadores_Matches.csv",
                HomeTeam = TeamNameNormalizer.StripSuffix(home),
                AwayTeam = TeamNameNormalizer.StripSuffix(away),
                HomeTeamKey = TeamNameNormalizer.CanonicalKey(home),
                AwayTeamKey = TeamNameNormalizer.CanonicalKey(away),
                HomeGoals = ParseInt(row.GetField("home_goal")),
                AwayGoals = ParseInt(row.GetField("away_goal")),
                Date = ParseDate(row.GetField<string>("datetime")),
                Season = ParseInt(row.GetField("season")),
                Stage = row.GetField<string>("stage"),
            });
            RegisterTeam(home);
            RegisterTeam(away);
        });
    }

    private void LoadExtendedStats()
    {
        LoadCsv(PathFor("BR-Football-Dataset.csv"), row =>
        {
            var tournament = row.GetField<string>("tournament") ?? "";
            var competition = tournament.Trim() switch
            {
                "Serie A" => "Brasileirão Série A",
                "Serie B" => "Brasileirão Série B",
                "Serie C" => "Brasileirão Série C",
                "Copa do Brasil" => "Copa do Brasil",
                _ => tournament,
            };
            var home = row.GetField<string>("home") ?? "";
            var away = row.GetField<string>("away") ?? "";
            _matches.Add(new Match
            {
                Competition = competition,
                Source = "BR-Football-Dataset.csv",
                HomeTeam = TeamNameNormalizer.StripSuffix(home),
                AwayTeam = TeamNameNormalizer.StripSuffix(away),
                HomeTeamKey = TeamNameNormalizer.CanonicalKey(home),
                AwayTeamKey = TeamNameNormalizer.CanonicalKey(away),
                HomeGoals = ParseInt(row.GetField("home_goal")),
                AwayGoals = ParseInt(row.GetField("away_goal")),
                HomeCorners = ParseInt(row.GetField("home_corner")),
                AwayCorners = ParseInt(row.GetField("away_corner")),
                HomeShots = ParseInt(row.GetField("home_shots")),
                AwayShots = ParseInt(row.GetField("away_shots")),
                HomeAttacks = ParseInt(row.GetField("home_attack")),
                AwayAttacks = ParseInt(row.GetField("away_attack")),
                Date = ParseDate(row.GetField<string>("date")),
                Season = ParseDate(row.GetField<string>("date"))?.Year,
            });
            RegisterTeam(home);
            RegisterTeam(away);
        });
    }

    private void LoadHistoricalBrasileirao()
    {
        LoadCsv(PathFor("novo_campeonato_brasileiro.csv"), row =>
        {
            var home = row.GetField<string>("Equipe_mandante") ?? "";
            var away = row.GetField<string>("Equipe_visitante") ?? "";
            _matches.Add(new Match
            {
                Competition = "Brasileirão (Histórico)",
                Source = "novo_campeonato_brasileiro.csv",
                HomeTeam = TeamNameNormalizer.StripSuffix(home),
                AwayTeam = TeamNameNormalizer.StripSuffix(away),
                HomeTeamKey = TeamNameNormalizer.CanonicalKey(home),
                AwayTeamKey = TeamNameNormalizer.CanonicalKey(away),
                HomeGoals = ParseInt(row.GetField("Gols_mandante")),
                AwayGoals = ParseInt(row.GetField("Gols_visitante")),
                Date = ParseDate(row.GetField<string>("Data")),
                Season = ParseInt(row.GetField("Ano")),
                Round = "Round " + row.GetField<string>("Rodada"),
                HomeState = row.GetField<string>("Mandante_UF"),
                AwayState = row.GetField<string>("Visitante_UF"),
                Arena = row.GetField<string>("Arena"),
            });
            RegisterTeam(home);
            RegisterTeam(away);
        });
    }

    private void LoadFifaPlayers()
    {
        var path = PathFor("fifa_data.csv");
        if (!File.Exists(path)) return;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HeaderValidated = null,
            MissingFieldFound = null,
            BadDataFound = null,
            PrepareHeaderForMatch = args => args.Header.Trim(),
        };

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, config);
        // The FIFA file has a stray leading BOM/empty column; read as-is and
        // look up columns by name defensively. Explicit ReadHeader() is required
        // by CsvHelper 33.x to parse column names for GetField("Name") lookups.
        if (!csv.Read()) return;
        csv.ReadHeader();
        while (csv.Read())
        {
            try
            {
                var name = csv.GetField<string>("Name");
                if (string.IsNullOrWhiteSpace(name)) continue;

                _players.Add(new Player
                {
                    Id = ParseLong(csv.GetField("ID")),
                    Name = name,
                    Age = ParseInt(csv.GetField("Age")),
                    Nationality = csv.GetField<string>("Nationality") ?? "",
                    Overall = ParseInt(csv.GetField("Overall")),
                    Potential = ParseInt(csv.GetField("Potential")),
                    Club = csv.GetField<string>("Club") ?? "",
                    Position = csv.GetField<string>("Position"),
                    JerseyNumber = ParseInt(csv.GetField("Jersey Number")),
                    PreferredFoot = csv.GetField<string>("Preferred Foot"),
                    Height = csv.GetField<string>("Height"),
                    Weight = csv.GetField<string>("Weight"),
                    Value = csv.GetField<string>("Value"),
                    Wage = csv.GetField<string>("Wage"),
                });
            }
            catch (Exception)
            {
                // Skip malformed rows rather than failing the entire load.
                Debug.WriteLine("Skipped a malformed FIFA player row.");
            }
        }
    }

    private void RegisterTeam(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return;
        var key = TeamNameNormalizer.CanonicalKey(raw);
        var display = TeamNameNormalizer.StripSuffix(raw);
        if (key.Length > 0 && !_teamKeyToDisplay.ContainsKey(key))
            _teamKeyToDisplay[key] = display;
    }

    /// <summary>Returns the display name for a canonical key, or the key itself.</summary>
    public string DisplayName(string key) =>
        _teamKeyToDisplay.TryGetValue(key, out var display) ? display : key;

    /// <summary>Resolves a user-provided team name to its canonical key.</summary>
    public string ResolveTeamKey(string team) =>
        TeamNameNormalizer.CanonicalKey(team);

    /// <summary>All known team display names, sorted alphabetically.</summary>
    public IReadOnlyList<string> AllTeams() =>
        _teamKeyToDisplay.Values
            .Where(v => !string.IsNullOrWhiteSpace(v))
            .OrderBy(v => v, StringComparer.OrdinalIgnoreCase)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();

    /// <summary>Matches where the given team played (home or away).</summary>
    public IEnumerable<Match> MatchesForTeam(string team)
    {
        var key = ResolveTeamKey(team);
        return _matches.Where(m => m.HomeTeamKey == key || m.AwayTeamKey == key);
    }

    /// <summary>Matches between two specific teams (either order).</summary>
    public IEnumerable<Match> HeadToHead(string teamA, string teamB)
    {
        var keyA = ResolveTeamKey(teamA);
        var keyB = ResolveTeamKey(teamB);
        return _matches.Where(m =>
            (m.HomeTeamKey == keyA && m.AwayTeamKey == keyB) ||
            (m.HomeTeamKey == keyB && m.AwayTeamKey == keyA));
    }

    /// <summary>Computes aggregated stats for a team, optionally scoped.</summary>
    public TeamStats StatsForTeam(string team, string? competition = null, int? season = null, bool homeOnly = false, bool awayOnly = false)
    {
        var key = ResolveTeamKey(team);
        var display = DisplayName(key);
        var stats = new TeamStats { Team = display };

        foreach (var m in _matches)
        {
            if (competition is not null && !m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase))
                continue;
            if (season.HasValue && m.Season != season)
                continue;

            bool isHome = m.HomeTeamKey == key;
            bool isAway = m.AwayTeamKey == key;
            if (!isHome && !isAway) continue;
            if (homeOnly && !isHome) continue;
            if (awayOnly && !isAway) continue;

            if (!m.HomeGoals.HasValue || !m.AwayGoals.HasValue) continue;

            stats.Matches++;
            int gf = isHome ? m.HomeGoals.Value : m.AwayGoals.Value;
            int ga = isHome ? m.AwayGoals.Value : m.HomeGoals.Value;
            stats.GoalsFor += gf;
            stats.GoalsAgainst += ga;
            if (gf > ga) stats.Wins++;
            else if (gf < ga) stats.Losses++;
            else stats.Draws++;
        }

        return stats;
    }

    /// <summary>Computes a points-based standings table for a competition season.</summary>
    public List<StandingsEntry> Standings(string competition, int season)
    {
        var rows = new Dictionary<string, StandingsEntry>(StringComparer.OrdinalIgnoreCase);
        foreach (var m in _matches)
        {
            if (m.Season != season) continue;
            if (!m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase)) continue;
            if (!m.HomeGoals.HasValue || !m.AwayGoals.HasValue) continue;

            var home = rows.GetOrAdd(m.HomeTeamKey, _ => new StandingsEntry { Team = m.HomeTeam });
            var away = rows.GetOrAdd(m.AwayTeamKey, _ => new StandingsEntry { Team = m.AwayTeam });

            home.Played++; away.Played++;
            home.GoalsFor += m.HomeGoals.Value; home.GoalsAgainst += m.AwayGoals.Value;
            away.GoalsFor += m.AwayGoals.Value; away.GoalsAgainst += m.HomeGoals.Value;

            if (m.HomeWin) { home.Wins++; away.Losses++; }
            else if (m.AwayWin) { away.Wins++; home.Losses++; }
            else { home.Draws++; away.Draws++; }
        }

        var list = rows.Values
            .OrderByDescending(r => r.Points)
            .ThenByDescending(r => r.Wins)
            .ThenByDescending(r => r.GoalDifference)
            .ThenBy(r => r.Team, StringComparer.OrdinalIgnoreCase)
            .ToList();

        for (var i = 0; i < list.Count; i++)
        {
            list[i].Position = i + 1;
            list[i].Champion = i == 0;
        }

        return list;
    }

    /// <summary>The biggest victories (by goal difference) across the dataset.</summary>
    public List<Match> BiggestVictories(int top = 10, string? competition = null)
    {
        var query = _matches.AsEnumerable();
        if (competition is not null)
            query = query.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));

        return query
            .Where(m => m.GoalDifference.HasValue && m.GoalDifference > 0)
            .OrderByDescending(m => m.GoalDifference!.Value)
            .ThenByDescending(m => m.TotalGoals ?? 0)
            .Take(top)
            .ToList();
    }

    // ---- Parsing helpers (tolerant of int/"2"/1.0/"2.0" etc.) ----

    public static int? ParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        if (int.TryParse(raw, out var i)) return i;
        if (double.TryParse(raw, NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
            return (int)d;
        return null;
    }

    internal static long? ParseLong(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        if (long.TryParse(raw, out var l)) return l;
        if (double.TryParse(raw, NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
            return (long)d;
        return null;
    }

    public static DateTime? ParseDate(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        // ISO "2012-05-19 18:30:00" or "2023-09-24"
        if (DateTime.TryParse(raw, CultureInfo.InvariantCulture, DateTimeStyles.None, out var iso))
            return iso;
        // Brazilian "29/03/2003"
        if (DateTime.TryParseExact(raw.Trim(), "dd/MM/yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out var br))
            return br;
        return null;
    }

    // ---- CsvHelper shared loader ----

    private void LoadCsv(string path, Action<IReaderRow> read)
    {
        if (!File.Exists(path)) return;
        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HeaderValidated = null,
            MissingFieldFound = null,
            BadDataFound = null,
            PrepareHeaderForMatch = args => args.Header.Trim(),
        };

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, config);
        // CsvHelper 33.x requires an explicit ReadHeader() call after the first
        // Read() so that GetField("columnName") can resolve headers by name.
        if (csv.Read())
        {
            csv.ReadHeader();
            while (csv.Read())
            {
                try { read(csv); }
                catch (Exception) { /* skip malformed row */ }
            }
        }
    }
}

internal static class DictExtensions
{
    public static TValue GetOrAdd<TKey, TValue>(this Dictionary<TKey, TValue> dict, TKey key, Func<TKey, TValue> factory)
        where TKey : notnull
    {
        if (dict.TryGetValue(key, out var value)) return value;
        value = factory(key);
        dict[key] = value;
        return value;
    }
}
