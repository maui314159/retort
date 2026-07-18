// ============================================================================
// BrazilianSoccerMcp - Data/SoccerDataStore.cs
//
// Context block:
//   In-memory read-only store for the six Kaggle CSV datasets. Loads happen
//   once at construction; everything the MCP tools return is derived from the
//   in-memory lists, so simple lookups are O(matches) and stay well under the
//   2-second budget even for the full ~24k matches.
//
//   Data directory resolution: the caller passes an explicit dataDir. Program.cs
//   resolves it from SOCCER_DATA_DIR, then ./data/kaggle relative to the app,
//   then a couple of ancestor lookups so `dotnet run` from the repo root works.
//   Tests pass the repo's data/kaggle path directly.
//
//   Parsing: CsvHelper handles RFC4180 quoting (the FIFA file has quoted
//   "Jul 1, 2004" cells and BOM). Dates/scores/goals are parsed defensively:
//   unparseable rows are kept for fixture presence but their goals become null
//   and are excluded from aggregates by Match.HasScore.
// ============================================================================

using System.Globalization;
using BrazilianSoccerMcp.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Data;

/// <summary>Loads and serves all Brazilian-soccer datasets in memory.</summary>
public sealed class SoccerDataStore
{
    public IReadOnlyList<Match> Matches { get; private set; } = Array.Empty<Match>();
    public IReadOnlyList<Player> Players { get; private set; } = Array.Empty<Player>();

    /// <summary>Per-competition match counts after loading.</summary>
    public IReadOnlyDictionary<Competition, int> MatchCounts { get; private set; }
        = new Dictionary<Competition, int>();

    /// <summary>
    /// Load every dataset from <paramref name="dataDir"/> (the folder that
    /// directly contains the six CSV files). Missing files are tolerated and
    /// counted as zero rows so a partial deployment still starts.
    /// </summary>
    public SoccerDataStore(string dataDir)
    {
        var matches = new List<Match>(24_000);
        var path = Path.GetFullPath(dataDir);

        LoadBrasileirano(matches, Path.Combine(path, "Brasileirao_Matches.csv"));
        LoadCup(matches, Path.Combine(path, "Brazilian_Cup_Matches.csv"));
        LoadLibertadores(matches, Path.Combine(path, "Libertadores_Matches.csv"));
        LoadBrFootball(matches, Path.Combine(path, "BR-Football-Dataset.csv"));
        LoadHistorico(matches, Path.Combine(path, "novo_campeonato_brasileiro.csv"));
        Matches = matches;
        MatchCounts = matches.GroupBy(m => m.Competition)
            .ToDictionary(g => g.Key, g => g.Count());

        Players = LoadPlayers(Path.Combine(path, "fifa_data.csv"));
    }

    // ----------------------------------------------------------------------
    // Helpers
    // ----------------------------------------------------------------------

    private static IEnumerable<IReaderRow> ReadRows(string file)
    {
        if (!File.Exists(file))
            yield break;
        using var reader = new StreamReader(file, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, CsvInvariant);
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
            yield return new IReaderRow(csv);
    }

    private static readonly CsvConfiguration CsvInvariant = new(CultureInfo.InvariantCulture)
    {
        DetectColumnCountChanges = false,
        IgnoreReferences = false,
    };

    /// <summary>Wraps a CsvReader row with safe column accessors.</summary>
    private readonly struct IReaderRow(CsvReader csv)
    {
        public string? Get(string name)
        {
            if (!csv.HeaderRecord?.Contains(name) ?? true) return null;
            return csv.TryGetField<string>(name, out var v) ? v : null;
        }
    }

    private static int? ParseInt(string? s) =>
        int.TryParse(s?.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var n) ? n : null;

    private static int? ParseIntLoose(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        // Tolerate "2.0" / "2,0" style floats occasionally seen in stat cols.
        if (double.TryParse(s.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
            return (int)d;
        return null;
    }

    private static DateTime? ParseDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        s = s.Trim();
        // ISO "yyyy-MM-dd HH:mm:ss" or "yyyy-MM-dd"
        if (DateTime.TryParseExact(s, new[]
            {
                "yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd HH:mm", "yyyy-MM-dd",
            }, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var iso))
            return iso;
        // Brazilian "dd/MM/yyyy"
        if (DateTime.TryParseExact(s, new[] { "dd/MM/yyyy", "d/M/yyyy", "dd/MM/yyyy HH:mm:ss" },
                CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var br))
            return br;
        return null;
    }

    private static DateTime? CombineDateTime(string? dateStr, string? timeStr)
    {
        var d = ParseDate(dateStr);
        if (d is null) return null;
        if (TimeSpan.TryParse(timeStr, CultureInfo.InvariantCulture, out var t))
            return d + t;
        return d;
    }

    // ----------------------------------------------------------------------
    // Per-dataset loaders
    // ----------------------------------------------------------------------

    private static void LoadBrasileirano(List<Match> sink, string file)
    {
        foreach (var r in ReadRows(file))
        {
            sink.Add(new Match
            {
                Competition = Competition.Brasileirao,
                Date = ParseDate(r.Get("datetime")),
                Season = ParseInt(r.Get("season")),
                HomeTeam = TeamNameNormalizer.NormalizeTeam(r.Get("home_team")),
                AwayTeam = TeamNameNormalizer.NormalizeTeam(r.Get("away_team")),
                HomeTeamRaw = r.Get("home_team") ?? "",
                AwayTeamRaw = r.Get("away_team") ?? "",
                HomeState = r.Get("home_team_state"),
                AwayState = r.Get("away_team_state"),
                HomeGoals = ParseInt(r.Get("home_goal")),
                AwayGoals = ParseInt(r.Get("away_goal")),
                Round = r.Get("round"),
            });
        }
    }

    private static void LoadCup(List<Match> sink, string file)
    {
        foreach (var r in ReadRows(file))
        {
            sink.Add(new Match
            {
                Competition = Competition.CopaDoBrasil,
                Date = ParseDate(r.Get("datetime")),
                Season = ParseInt(r.Get("season")),
                HomeTeam = TeamNameNormalizer.NormalizeTeam(r.Get("home_team")),
                AwayTeam = TeamNameNormalizer.NormalizeTeam(r.Get("away_team")),
                HomeTeamRaw = r.Get("home_team") ?? "",
                AwayTeamRaw = r.Get("away_team") ?? "",
                HomeGoals = ParseInt(r.Get("home_goal")),
                AwayGoals = ParseInt(r.Get("away_goal")),
                Round = r.Get("round"),
            });
        }
    }

    private static void LoadLibertadores(List<Match> sink, string file)
    {
        foreach (var r in ReadRows(file))
        {
            sink.Add(new Match
            {
                Competition = Competition.Libertadores,
                Date = ParseDate(r.Get("datetime")),
                Season = ParseInt(r.Get("season")),
                HomeTeam = TeamNameNormalizer.NormalizeTeam(r.Get("home_team")),
                AwayTeam = TeamNameNormalizer.NormalizeTeam(r.Get("away_team")),
                HomeTeamRaw = r.Get("home_team") ?? "",
                AwayTeamRaw = r.Get("away_team") ?? "",
                HomeGoals = ParseIntLoose(r.Get("home_goal")),
                AwayGoals = ParseIntLoose(r.Get("away_goal")),
                Stage = r.Get("stage"),
            });
        }
    }

    private static void LoadBrFootball(List<Match> sink, string file)
    {
        foreach (var r in ReadRows(file))
        {
            sink.Add(new Match
            {
                Competition = Competition.BrFootball,
                Tournament = r.Get("tournament"),
                Date = CombineDateTime(r.Get("date"), r.Get("time")),
                HomeTeam = TeamNameNormalizer.NormalizeTeam(r.Get("home")),
                AwayTeam = TeamNameNormalizer.NormalizeTeam(r.Get("away")),
                HomeTeamRaw = r.Get("home") ?? "",
                AwayTeamRaw = r.Get("away") ?? "",
                HomeGoals = ParseIntLoose(r.Get("home_goal")),
                AwayGoals = ParseIntLoose(r.Get("away_goal")),
                HomeCorners = ParseIntLoose(r.Get("home_corner")),
                AwayCorners = ParseIntLoose(r.Get("away_corner")),
                HomeAttacks = ParseIntLoose(r.Get("home_attack")),
                AwayAttacks = ParseIntLoose(r.Get("away_attack")),
                HomeShots = ParseIntLoose(r.Get("home_shots")),
                AwayShots = ParseIntLoose(r.Get("away_shots")),
            });
        }
    }

    private static void LoadHistorico(List<Match> sink, string file)
    {
        foreach (var r in ReadRows(file))
        {
            sink.Add(new Match
            {
                Competition = Competition.HistoricoBrasileirao,
                Date = ParseDate(r.Get("Data")),
                Season = ParseInt(r.Get("Ano")),
                Round = r.Get("Rodada"),
                HomeTeam = TeamNameNormalizer.NormalizeTeam(r.Get("Equipe_mandante")),
                AwayTeam = TeamNameNormalizer.NormalizeTeam(r.Get("Equipe_visitante")),
                HomeTeamRaw = r.Get("Equipe_mandante") ?? "",
                AwayTeamRaw = r.Get("Equipe_visitante") ?? "",
                HomeState = r.Get("Mandante_UF"),
                AwayState = r.Get("Visitante_UF"),
                HomeGoals = ParseInt(r.Get("Gols_mandante")),
                AwayGoals = ParseInt(r.Get("Gols_visitante")),
                Stadium = r.Get("Arena"),
            });
        }
    }

    private static List<Player> LoadPlayers(string file)
    {
        var players = new List<Player>(18_000);
        foreach (var r in ReadRows(file))
        {
            players.Add(new Player
            {
                Id = ParseInt(r.Get("ID")) ?? 0,
                Name = r.Get("Name") ?? "",
                Age = ParseInt(r.Get("Age")),
                Nationality = r.Get("Nationality"),
                Overall = ParseInt(r.Get("Overall")),
                Potential = ParseInt(r.Get("Potential")),
                Club = r.Get("Club"),
                Position = r.Get("Position"),
                JerseyNumber = ParseInt(r.Get("Jersey Number")),
                PreferredFoot = r.Get("Preferred Foot"),
                Height = r.Get("Height"),
                Weight = r.Get("Weight"),
                Value = r.Get("Value"),
                Wage = r.Get("Wage"),
                Crossing = ParseInt(r.Get("Crossing")),
                Finishing = ParseInt(r.Get("Finishing")),
                HeadingAccuracy = ParseInt(r.Get("HeadingAccuracy")),
                ShortPassing = ParseInt(r.Get("ShortPassing")),
                Volleys = ParseInt(r.Get("Volleys")),
                Dribbling = ParseInt(r.Get("Dribbling")),
                Curve = ParseInt(r.Get("Curve")),
                FkAccuracy = ParseInt(r.Get("FKAccuracy")),
                LongPassing = ParseInt(r.Get("LongPassing")),
                BallControl = ParseInt(r.Get("BallControl")),
                Acceleration = ParseInt(r.Get("Acceleration")),
                SprintSpeed = ParseInt(r.Get("SprintSpeed")),
                ShotPower = ParseInt(r.Get("ShotPower")),
                Stamina = ParseInt(r.Get("Stamina")),
                Strength = ParseInt(r.Get("Strength")),
                Aggression = ParseInt(r.Get("Aggression")),
                Interceptions = ParseInt(r.Get("Interceptions")),
                Positioning = ParseInt(r.Get("Positioning")),
                Vision = ParseInt(r.Get("Vision")),
                Penalties = ParseInt(r.Get("Penalties")),
                Composure = ParseInt(r.Get("Composure")),
                Marking = ParseInt(r.Get("Marking")),
                StandingTackle = ParseInt(r.Get("StandingTackle")),
                SlidingTackle = ParseInt(r.Get("SlidingTackle")),
            });
        }
        return players;
    }
}
