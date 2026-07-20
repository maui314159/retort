using System.Globalization;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Loads the six Kaggle CSV datasets into unified in-memory records.
/// Data directory resolution order: BRAZILIAN_SOCCER_DATA_DIR env var,
/// "data/kaggle" under the current directory, then walking up from the
/// executable directory looking for "data/kaggle".
/// </summary>
public sealed class DataLoader
{
    public const string BrasileiraoSerieA = "Brasileirão Série A";
    public const string BrasileiraoSerieB = "Brasileirão Série B";
    public const string BrasileiraoSerieC = "Brasileirão Série C";
    public const string CopaDoBrasil = "Copa do Brasil";
    public const string CopaLibertadores = "Copa Libertadores";

    public List<MatchRecord> Matches { get; } = [];
    public List<PlayerRecord> Players { get; } = [];

    /// <summary>Files that were loaded, with row counts (for diagnostics / list_datasets tool).</summary>
    public List<DatasetInfo> Datasets { get; } = [];

    public static readonly string[] RequiredFiles =
    [
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
        "fifa_data.csv",
    ];

    public static string ResolveDataDirectory(string? startDirectory = null)
    {
        var env = Environment.GetEnvironmentVariable("BRAZILIAN_SOCCER_DATA_DIR");
        if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env))
            return Path.GetFullPath(env);

        var candidates = new List<string>();
        var cwd = Directory.GetCurrentDirectory();
        candidates.Add(cwd);
        candidates.Add(startDirectory ?? AppContext.BaseDirectory);

        foreach (var candidate in candidates)
        {
            var dir = new DirectoryInfo(candidate);
            while (dir is not null)
            {
                var probe = Path.Combine(dir.FullName, "data", "kaggle");
                if (File.Exists(Path.Combine(probe, "Brasileirao_Matches.csv")))
                    return probe;
                dir = dir.Parent;
            }
        }

        throw new DirectoryNotFoundException(
            "Could not locate the data/kaggle directory. Set BRAZILIAN_SOCCER_DATA_DIR.");
    }

    public static DataLoader LoadAll(string dataDirectory)
    {
        var loader = new DataLoader();
        // Load order matters: earlier sources win cross-file deduplication.
        loader.LoadBrasileiraoMatches(Path.Combine(dataDirectory, "Brasileirao_Matches.csv"));
        loader.LoadBrazilianCupMatches(Path.Combine(dataDirectory, "Brazilian_Cup_Matches.csv"));
        loader.LoadLibertadoresMatches(Path.Combine(dataDirectory, "Libertadores_Matches.csv"));
        loader.LoadBrFootballDataset(Path.Combine(dataDirectory, "BR-Football-Dataset.csv"));
        loader.LoadHistoricalBrasileirao(Path.Combine(dataDirectory, "novo_campeonato_brasileiro.csv"));
        loader.LoadFifaPlayers(Path.Combine(dataDirectory, "fifa_data.csv"));
        loader.DeduplicateMatches();
        return loader;
    }

    /// <summary>
    /// The match files overlap (e.g. BR-Football-Dataset also covers Série A and Copa do Brasil
    /// fixtures present in the dedicated files), and dates for the same fixture can differ by
    /// a day or two between sources. Drop cross-file duplicates — same canonical teams, same
    /// competition, kick-off dates within 2 days — keeping the first (highest priority) row.
    /// </summary>
    private void DeduplicateMatches()
    {
        var datesByPair = new Dictionary<string, List<(DateOnly Date, int KeptIndex)>>(StringComparer.Ordinal);
        var kept = new List<MatchRecord>(Matches.Count);
        var duplicates = 0;
        foreach (var m in Matches)
        {
            if (m.Date is { } date)
            {
                var pairKey = $"{m.HomeTeamCanonical}|{m.AwayTeamCanonical}|{m.Competition}";
                if (!datesByPair.TryGetValue(pairKey, out var entries))
                    datesByPair[pairKey] = entries = [];

                var duplicateIndex = entries.FindIndex(e => Math.Abs(e.Date.DayNumber - date.DayNumber) <= 2);
                if (duplicateIndex >= 0)
                {
                    // Same fixture seen before (possibly from another file with a shifted date).
                    duplicates++;
                    var keptIndex = entries[duplicateIndex].KeptIndex;
                    if (!kept[keptIndex].Played && m.Played)
                        kept[keptIndex] = m; // prefer the row with a recorded score
                    continue;
                }
                entries.Add((date, kept.Count));
            }
            kept.Add(m);
        }
        if (duplicates > 0)
            Datasets.Add(new DatasetInfo("(cross-file duplicates removed)", "-", duplicates));

        Matches.Clear();
        Matches.AddRange(kept);
    }

    // ---------- Match file loaders ----------

    private void LoadBrasileiraoMatches(string path)
    {
        var count = 0;
        foreach (var row in DataRows(path))
        {
            // datetime, home_team, home_team_state, away_team, away_team_state, home_goal, away_goal, season, round
            var match = new MatchRecord
            {
                Date = ParseDate(Cell(row, 0)),
                Season = ParseInt(Cell(row, 7)),
                Competition = BrasileiraoSerieA,
                Source = "Brasileirao_Matches",
                Round = ParseInt(Cell(row, 8)) is { } r ? $"Round {r}" : null,
                HomeTeam = Cell(row, 1),
                AwayTeam = Cell(row, 3),
                HomeTeamCanonical = TeamNameNormalizer.CanonicalName(Cell(row, 1)),
                AwayTeamCanonical = TeamNameNormalizer.CanonicalName(Cell(row, 3)),
                HomeGoals = ParseGoals(Cell(row, 5)),
                AwayGoals = ParseGoals(Cell(row, 6)),
            };
            Matches.Add(match);
            count++;
        }
        Datasets.Add(new DatasetInfo("Brasileirao_Matches.csv", BrasileiraoSerieA, count));
    }

    private void LoadBrazilianCupMatches(string path)
    {
        var count = 0;
        foreach (var row in DataRows(path))
        {
            // round, datetime, home_team, away_team, home_goal, away_goal, season
            var cupRound = ParseInt(Cell(row, 0));
            var match = new MatchRecord
            {
                Date = ParseDate(Cell(row, 1)),
                Season = ParseInt(Cell(row, 6)),
                Competition = CopaDoBrasil,
                Source = "Brazilian_Cup_Matches",
                Round = CupRoundName(cupRound),
                HomeTeam = Cell(row, 2),
                AwayTeam = Cell(row, 3),
                HomeTeamCanonical = TeamNameNormalizer.CanonicalName(Cell(row, 2)),
                AwayTeamCanonical = TeamNameNormalizer.CanonicalName(Cell(row, 3)),
                HomeGoals = ParseGoals(Cell(row, 4)),
                AwayGoals = ParseGoals(Cell(row, 5)),
            };
            Matches.Add(match);
            count++;
        }
        Datasets.Add(new DatasetInfo("Brazilian_Cup_Matches.csv", CopaDoBrasil, count));
    }

    private void LoadLibertadoresMatches(string path)
    {
        var count = 0;
        foreach (var row in DataRows(path))
        {
            // datetime, home_team, away_team, home_goal, away_goal, season, stage
            var date = ParseDate(Cell(row, 0));
            var season = ParseInt(Cell(row, 5)) ?? date?.Year; // some rows have season "NA"
            var stage = Cell(row, 6);
            var match = new MatchRecord
            {
                Date = date,
                Season = season,
                Competition = CopaLibertadores,
                Source = "Libertadores_Matches",
                Round = string.IsNullOrWhiteSpace(stage) ? null : CultureInfo.InvariantCulture.TextInfo.ToTitleCase(stage),
                HomeTeam = Cell(row, 1),
                AwayTeam = Cell(row, 2),
                HomeTeamCanonical = TeamNameNormalizer.CanonicalName(Cell(row, 1)),
                AwayTeamCanonical = TeamNameNormalizer.CanonicalName(Cell(row, 2)),
                HomeGoals = ParseGoals(Cell(row, 3)),
                AwayGoals = ParseGoals(Cell(row, 4)),
            };
            Matches.Add(match);
            count++;
        }
        Datasets.Add(new DatasetInfo("Libertadores_Matches.csv", CopaLibertadores, count));
    }

    private void LoadBrFootballDataset(string path)
    {
        var count = 0;
        foreach (var row in DataRows(path))
        {
            // tournament, home, home_goal, away_goal, away, home_corner, away_corner, home_attack, away_attack,
            // home_shots, away_shots, time, date, ht_diff, at_diff, ht_result, at_result, total_corners
            var competition = Cell(row, 0) switch
            {
                "Serie A" => BrasileiraoSerieA,
                "Serie B" => BrasileiraoSerieB,
                "Serie C" => BrasileiraoSerieC,
                "Copa do Brasil" => CopaDoBrasil,
                var other => string.IsNullOrWhiteSpace(other) ? "Unknown" : other,
            };
            var date = ParseDate(Cell(row, 12));
            var match = new MatchRecord
            {
                Date = date,
                Season = date?.Year,
                Competition = competition,
                Source = "BR-Football-Dataset",
                Round = null,
                HomeTeam = Cell(row, 1),
                AwayTeam = Cell(row, 4),
                HomeTeamCanonical = TeamNameNormalizer.CanonicalName(Cell(row, 1)),
                AwayTeamCanonical = TeamNameNormalizer.CanonicalName(Cell(row, 4)),
                HomeGoals = ParseGoals(Cell(row, 2)),
                AwayGoals = ParseGoals(Cell(row, 3)),
                HomeCorners = ParseGoals(Cell(row, 5)),
                AwayCorners = ParseGoals(Cell(row, 6)),
                HomeShots = ParseGoals(Cell(row, 9)),
                AwayShots = ParseGoals(Cell(row, 10)),
            };
            Matches.Add(match);
            count++;
        }
        Datasets.Add(new DatasetInfo("BR-Football-Dataset.csv", "Multiple tournaments", count));
    }

    private void LoadHistoricalBrasileirao(string path)
    {
        var count = 0;
        foreach (var row in DataRows(path))
        {
            // ID, Data, Ano, Rodada, Equipe_mandante, Equipe_visitante, Gols_mandante, Gols_visitante,
            // Mandante_UF, Visitante_UF, Vencedor, Arena, OBS
            var match = new MatchRecord
            {
                Date = ParseDate(Cell(row, 1)),
                Season = ParseInt(Cell(row, 2)),
                Competition = BrasileiraoSerieA,
                Source = "novo_campeonato_brasileiro",
                Round = ParseInt(Cell(row, 3)) is { } r ? $"Round {r}" : null,
                HomeTeam = Cell(row, 4),
                AwayTeam = Cell(row, 5),
                HomeTeamCanonical = TeamNameNormalizer.CanonicalName(Cell(row, 4)),
                AwayTeamCanonical = TeamNameNormalizer.CanonicalName(Cell(row, 5)),
                HomeGoals = ParseGoals(Cell(row, 6)),
                AwayGoals = ParseGoals(Cell(row, 7)),
                Stadium = NullIfEmpty(Cell(row, 11)),
            };
            Matches.Add(match);
            count++;
        }
        Datasets.Add(new DatasetInfo("novo_campeonato_brasileiro.csv", BrasileiraoSerieA, count));
    }

    // ---------- Player file loader ----------

    private void LoadFifaPlayers(string path)
    {
        var count = 0;
        string[]? header = null;
        var index = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        foreach (var row in CsvParser.ReadRows(path))
        {
            if (header is null)
            {
                header = row;
                for (var i = 0; i < header.Length; i++)
                {
                    var name = header[i].Trim();
                    if (name.Length > 0 && !index.ContainsKey(name))
                        index[name] = i;
                }
                continue;
            }

            string Get(string column) =>
                index.TryGetValue(column, out var i) && i < row.Length ? row[i].Trim() : string.Empty;

            if (!int.TryParse(Get("ID"), NumberStyles.Integer, CultureInfo.InvariantCulture, out var id))
                continue;

            Players.Add(new PlayerRecord
            {
                Id = id,
                Name = Get("Name"),
                Age = ParseInt(Get("Age")),
                Nationality = NullIfEmpty(Get("Nationality")),
                Overall = ParseInt(Get("Overall")),
                Potential = ParseInt(Get("Potential")),
                Club = NullIfEmpty(Get("Club")),
                Position = NullIfEmpty(Get("Position")),
                JerseyNumber = ParseInt(Get("Jersey Number")),
                Height = NullIfEmpty(Get("Height")),
                Weight = NullIfEmpty(Get("Weight")),
            });
            count++;
        }
        Datasets.Add(new DatasetInfo("fifa_data.csv", "FIFA players", count));
    }

    // ---------- Parsing helpers ----------

    private static IEnumerable<string[]> DataRows(string path) =>
        CsvParser.ReadRows(path).Skip(1); // skip header

    private static string Cell(string[] row, int i) =>
        i < row.Length ? row[i].Trim() : string.Empty;

    private static string? NullIfEmpty(string s) =>
        string.IsNullOrWhiteSpace(s) ? null : s;

    /// <summary>Parses goal/stat cells: integers, floats ("1.0"), or null for "NA"/empty.</summary>
    public static int? ParseGoals(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var s = raw.Trim();
        if (s.Equals("NA", StringComparison.OrdinalIgnoreCase)) return null;
        if (int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i)) return i;
        if (double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var d)) return (int)Math.Round(d);
        return null;
    }

    public static int? ParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var s = raw.Trim();
        if (s.Equals("NA", StringComparison.OrdinalIgnoreCase)) return null;
        return int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i) ? i : null;
    }

    /// <summary>Handles ISO ("2023-09-24", "2012-05-19 18:30:00") and Brazilian ("29/03/2003") formats.</summary>
    public static DateOnly? ParseDate(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var s = raw.Trim();
        string[] formats =
        [
            "yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd HH:mm", "yyyy-MM-dd",
            "dd/MM/yyyy HH:mm:ss", "dd/MM/yyyy HH:mm", "dd/MM/yyyy",
        ];
        if (DateTime.TryParseExact(s, formats, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt))
            return DateOnly.FromDateTime(dt);
        if (DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.None, out dt))
            return DateOnly.FromDateTime(dt);
        return null;
    }

    /// <summary>Copa do Brasil round numbers in this dataset: 1..8 where 8 is the two-legged final.</summary>
    public static string CupRoundName(int? round) => round switch
    {
        1 => "First round",
        2 => "Second round",
        3 => "Third round",
        4 => "Fourth round",
        5 => "Round of 16",
        6 => "Quarterfinals",
        7 => "Semifinals",
        8 => "Final",
        { } r => $"Round {r}",
        null => "Unknown round",
    };
}

public sealed record DatasetInfo(string File, string Contents, int RowCount);
