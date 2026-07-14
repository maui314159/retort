using System.Globalization;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Loads every CSV dataset from <c>data/kaggle/</c> into the normalized
/// <see cref="MatchRecord"/> / <see cref="PlayerRecord"/> shapes. The loader
/// is deliberately tolerant: it tolerates missing columns, mixed date
/// formats and quoted values that include commas.
/// </summary>
public sealed class DataRepository
{
    private readonly string _kaggleDir;

    public IReadOnlyList<MatchRecord> Matches { get; private set; } = Array.Empty<MatchRecord>();
    public IReadOnlyList<PlayerRecord> Players { get; private set; } = Array.Empty<PlayerRecord>();

    public DataRepository(string kaggleDir)
    {
        _kaggleDir = kaggleDir;
    }

    /// <summary>Loads all six CSV files. Idempotent; safe to call multiple times.</summary>
    public void Load()
    {
        var matches = new List<MatchRecord>();
        matches.AddRange(LoadBrasileirao());
        matches.AddRange(LoadCopaDoBrasil());
        matches.AddRange(LoadLibertadores());
        matches.AddRange(LoadBrFootball());
        matches.AddRange(LoadHistoricalBrasileirao());
        Matches = matches;

        Players = LoadFifa();
    }

    // ----- individual file loaders -----

    private IEnumerable<MatchRecord> LoadBrasileirao()
    {
        var path = Path.Combine(_kaggleDir, "Brasileirao_Matches.csv");
        if (!File.Exists(path)) yield break;
        foreach (var row in ReadRows(path))
        {
            yield return new MatchRecord
            {
                Competition = "Brasileirao",
                Date = ParseDate(Get(row, "datetime")),
                HomeTeam = TeamNameNormalizer.DisplayName(Get(row, "home_team")),
                AwayTeam = TeamNameNormalizer.DisplayName(Get(row, "away_team")),
                HomeState = Get(row, "home_team_state"),
                AwayState = Get(row, "away_team_state"),
                HomeGoal = ParseInt(Get(row, "home_goal")),
                AwayGoal = ParseInt(Get(row, "away_goal")),
                Season = ParseInt(Get(row, "season")),
                Round = "Round " + Get(row, "round"),
                RawHomeTeam = Get(row, "home_team"),
                RawAwayTeam = Get(row, "away_team"),
            };
        }
    }

    private IEnumerable<MatchRecord> LoadCopaDoBrasil()
    {
        var path = Path.Combine(_kaggleDir, "Brazilian_Cup_Matches.csv");
        if (!File.Exists(path)) yield break;
        foreach (var row in ReadRows(path))
        {
            yield return new MatchRecord
            {
                Competition = "CopaDoBrasil",
                Date = ParseDate(Get(row, "datetime")),
                HomeTeam = TeamNameNormalizer.DisplayName(Get(row, "home_team")),
                AwayTeam = TeamNameNormalizer.DisplayName(Get(row, "away_team")),
                HomeGoal = ParseInt(Get(row, "home_goal")),
                AwayGoal = ParseInt(Get(row, "away_goal")),
                Season = ParseInt(Get(row, "season")),
                Round = Get(row, "round"),
                RawHomeTeam = Get(row, "home_team"),
                RawAwayTeam = Get(row, "away_team"),
            };
        }
    }

    private IEnumerable<MatchRecord> LoadLibertadores()
    {
        var path = Path.Combine(_kaggleDir, "Libertadores_Matches.csv");
        if (!File.Exists(path)) yield break;
        foreach (var row in ReadRows(path))
        {
            yield return new MatchRecord
            {
                Competition = "Libertadores",
                Date = ParseDate(Get(row, "datetime")),
                HomeTeam = TeamNameNormalizer.DisplayName(Get(row, "home_team")),
                AwayTeam = TeamNameNormalizer.DisplayName(Get(row, "away_team")),
                HomeGoal = ParseInt(Get(row, "home_goal")),
                AwayGoal = ParseInt(Get(row, "away_goal")),
                Season = ParseInt(Get(row, "season")),
                Round = Get(row, "stage"),
                RawHomeTeam = Get(row, "home_team"),
                RawAwayTeam = Get(row, "away_team"),
            };
        }
    }

    private IEnumerable<MatchRecord> LoadBrFootball()
    {
        var path = Path.Combine(_kaggleDir, "BR-Football-Dataset.csv");
        if (!File.Exists(path)) yield break;
        foreach (var row in ReadRows(path))
        {
            yield return new MatchRecord
            {
                Competition = Get(row, "tournament"),
                Date = ParseDate(Get(row, "date")),
                HomeTeam = TeamNameNormalizer.DisplayName(Get(row, "home")),
                AwayTeam = TeamNameNormalizer.DisplayName(Get(row, "away")),
                HomeGoal = ParseInt(Get(row, "home_goal")),
                AwayGoal = ParseInt(Get(row, "away_goal")),
                Season = ParseDate(Get(row, "date")).Year,
                Round = string.Empty,
                RawHomeTeam = Get(row, "home"),
                RawAwayTeam = Get(row, "away"),
            };
        }
    }

    private IEnumerable<MatchRecord> LoadHistoricalBrasileirao()
    {
        var path = Path.Combine(_kaggleDir, "novo_campeonato_brasileiro.csv");
        if (!File.Exists(path)) yield break;
        foreach (var row in ReadRows(path))
        {
            yield return new MatchRecord
            {
                Competition = "BrasileiraoHistorico",
                Date = ParseBrDate(Get(row, "Data")),
                HomeTeam = TeamNameNormalizer.DisplayName(Get(row, "Equipe_mandante")),
                AwayTeam = TeamNameNormalizer.DisplayName(Get(row, "Equipe_visitante")),
                HomeState = Get(row, "Mandante_UF"),
                AwayState = Get(row, "Visitante_UF"),
                HomeGoal = ParseInt(Get(row, "Gols_mandante")),
                AwayGoal = ParseInt(Get(row, "Gols_visitante")),
                Season = ParseInt(Get(row, "Ano")),
                Round = "Round " + Get(row, "Rodada"),
                RawHomeTeam = Get(row, "Equipe_mandante"),
                RawAwayTeam = Get(row, "Equipe_visitante"),
            };
        }
    }

    private IReadOnlyList<PlayerRecord> LoadFifa()
    {
        var path = Path.Combine(_kaggleDir, "fifa_data.csv");
        var list = new List<PlayerRecord>();
        if (!File.Exists(path)) return list;
        foreach (var row in ReadRows(path))
        {
            list.Add(new PlayerRecord
            {
                Id = ParseInt(Get(row, "ID")),
                Name = Get(row, "Name"),
                Age = ParseInt(Get(row, "Age")),
                Nationality = Get(row, "Nationality"),
                Overall = ParseInt(Get(row, "Overall")),
                Potential = ParseInt(Get(row, "Potential")),
                Club = Get(row, "Club"),
                Position = Get(row, "Position"),
                JerseyNumber = ParseInt(Get(row, "Jersey Number")),
                Height = Get(row, "Height"),
                Weight = Get(row, "Weight"),
            });
        }
        return list;
    }

    // ----- helpers -----

    private static IEnumerable<IReadOnlyDictionary<string, string>> ReadRows(string path)
    {
        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HeaderValidated = null,
            MissingFieldFound = null,
            BadDataFound = null,
            PrepareHeaderForMatch = args => args.Header.Trim().Trim('"'),
        };
        using var sr = new StreamReader(path);
        using var csv = new CsvReader(sr, config);
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            var dict = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var header in csv.HeaderRecord ?? Array.Empty<string>())
            {
                dict[header] = csv.GetField(header) ?? string.Empty;
            }
            yield return dict;
        }
    }

    private static string Get(IReadOnlyDictionary<string, string> row, string key)
        => row.TryGetValue(key, out var v) ? v : string.Empty;

    private static int ParseInt(string s)
    {
        if (string.IsNullOrWhiteSpace(s)) return 0;
        if (int.TryParse(s, out var i)) return i;
        if (double.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var d)) return (int)d;
        return 0;
    }

    private static DateTime ParseDate(string s)
    {
        if (string.IsNullOrWhiteSpace(s)) return DateTime.MinValue;
        // ISO with optional time: "2023-09-24" or "2012-05-19 18:30:00"
        if (DateTime.TryParseExact(s, "yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeLocal | DateTimeStyles.AllowLeadingWhite, out var withTime))
            return withTime;
        if (DateTime.TryParseExact(s, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var dateOnly))
            return dateOnly;
        if (DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var fallback))
            return fallback;
        return DateTime.MinValue;
    }

    private static DateTime ParseBrDate(string s)
    {
        if (string.IsNullOrWhiteSpace(s)) return DateTime.MinValue;
        if (DateTime.TryParseExact(s, "dd/MM/yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out var d))
            return d;
        return ParseDate(s);
    }
}
