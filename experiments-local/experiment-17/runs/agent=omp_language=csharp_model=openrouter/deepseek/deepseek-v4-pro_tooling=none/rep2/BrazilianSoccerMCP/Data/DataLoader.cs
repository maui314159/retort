using System.Globalization;
using System.Reflection;
using System.Text;
using BrazilianSoccerMCP.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMCP.Data;

public class DataLoader
{
    public string DataDir { get; set; } = FindDataDir();

    public List<BrasileiraoMatch> LoadBrasileiraoMatches()
        => LoadCsv<BrasileiraoMatch>(Path.Combine(DataDir, "Brasileirao_Matches.csv"));

    public List<CopaBrasilMatch> LoadCopaBrasilMatches()
        => LoadCsv<CopaBrasilMatch>(Path.Combine(DataDir, "Brazilian_Cup_Matches.csv"));

    public List<LibertadoresMatch> LoadLibertadoresMatches()
        => LoadCsv<LibertadoresMatch>(Path.Combine(DataDir, "Libertadores_Matches.csv"));

    public List<ExtendedMatch> LoadExtendedMatches()
        => LoadCsv<ExtendedMatch>(Path.Combine(DataDir, "BR-Football-Dataset.csv"));

    public List<HistoricalMatch> LoadHistoricalMatches()
        => LoadCsv<HistoricalMatch>(Path.Combine(DataDir, "novo_campeonato_brasileiro.csv"));

    public List<FifaPlayer> LoadFifaPlayers()
    {
        var path = Path.Combine(DataDir, "fifa_data.csv");
        return LoadCsv<FifaPlayer>(path);
    }

    public List<UnifiedMatch> LoadAllUnifiedMatches()
    {
        var matches = new List<UnifiedMatch>();

        foreach (var m in LoadBrasileiraoMatches())
        {
            var date = ParseDate(m.Datetime);
            matches.Add(new UnifiedMatch
            {
                Date = date,
                Season = m.Season,
                Competition = "Brasileirão",
                HomeTeam = TeamNormalizer.Normalize(m.HomeTeam),
                AwayTeam = TeamNormalizer.Normalize(m.AwayTeam),
                HomeGoals = m.HomeGoal ?? 0,
                AwayGoals = m.AwayGoal ?? 0,
                Round = m.Round.ToString(),
                Stage = "",
            });
        }

        foreach (var m in LoadCopaBrasilMatches())
        {
            var date = ParseDate(m.Datetime);
            matches.Add(new UnifiedMatch
            {
                Date = date,
                Season = m.Season,
                Competition = "Copa do Brasil",
                HomeTeam = TeamNormalizer.Normalize(m.HomeTeam),
                AwayTeam = TeamNormalizer.Normalize(m.AwayTeam),
                HomeGoals = m.HomeGoal ?? 0,
                AwayGoals = m.AwayGoal ?? 0,
                Round = m.Round,
                Stage = "",
            });
        }

        foreach (var m in LoadLibertadoresMatches())
        {
            var date = ParseDate(m.Datetime);
            matches.Add(new UnifiedMatch
            {
                Date = date,
                Season = m.Season,
                Competition = "Libertadores",
                HomeTeam = TeamNormalizer.Normalize(m.HomeTeam),
                AwayTeam = TeamNormalizer.Normalize(m.AwayTeam),
                HomeGoals = m.HomeGoal ?? 0,
                AwayGoals = m.AwayGoal ?? 0,
                Round = "",
                Stage = m.Stage,
            });
        }

        foreach (var m in LoadExtendedMatches())
        {
            var date = ParseDate(m.Date);
            matches.Add(new UnifiedMatch
            {
                Date = date,
                Season = date?.Year,
                Competition = m.Tournament,
                HomeTeam = TeamNormalizer.Normalize(m.Home),
                AwayTeam = TeamNormalizer.Normalize(m.Away),
                HomeGoals = m.HomeGoal,
                AwayGoals = m.AwayGoal,
                Round = "",
                Stage = "",
            });
        }

        foreach (var m in LoadHistoricalMatches())
        {
            var date = ParseDate(m.Data);
            matches.Add(new UnifiedMatch
            {
                Date = date,
                Season = m.Ano,
                Competition = "Brasileirão",
                HomeTeam = TeamNormalizer.Normalize(m.EquipeMandante),
                AwayTeam = TeamNormalizer.Normalize(m.EquipeVisitante),
                HomeGoals = m.GolsMandante ?? 0,
                AwayGoals = m.GolsVisitante ?? 0,
                Round = m.Rodada.ToString(),
                Stage = "",
            });
        }

        return matches;
    }

    private static List<T> LoadCsv<T>(string path)
    {
        using var reader = new StreamReader(path, Encoding.UTF8);
        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            MissingFieldFound = null,
            HeaderValidated = null,
            BadDataFound = null,
        };
        using var csv = new CsvReader(reader, config);
        // Handle "NA" and "-" as null for numeric fields
        csv.Context.TypeConverterOptionsCache.GetOptions<int>().NullValues.Add("NA");
        csv.Context.TypeConverterOptionsCache.GetOptions<int>().NullValues.Add("-");
        csv.Context.TypeConverterOptionsCache.GetOptions<int?>().NullValues.Add("NA");
        csv.Context.TypeConverterOptionsCache.GetOptions<int?>().NullValues.Add("-");
        csv.Context.TypeConverterOptionsCache.GetOptions<int?>().NullValues.Add("");
        return csv.GetRecords<T>().ToList();
    }
    private static DateTime? ParseDate(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return null;

        // Try common formats
        string[] formats =
        [
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd",
            "yyyy-MM-ddTHH:mm:ss",
            "dd/MM/yyyy",
            "MM/dd/yyyy",
            "yyyy/MM/dd",
            "dd-MM-yyyy",
        ];

        if (DateTime.TryParseExact(value.Trim(), formats, CultureInfo.InvariantCulture, DateTimeStyles.None, out var exact))
            return exact;

        if (DateTime.TryParse(value.Trim(), CultureInfo.InvariantCulture, DateTimeStyles.None, out var fallback))
            return fallback;

        return null;
    }

    private static string FindDataDir()
    {
        var candidates = new List<string>();

        // Relative to assembly location (debug/release output dir -> project root -> data/kaggle)
        var assemblyDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
        if (assemblyDir is not null)
        {
            candidates.Add(Path.GetFullPath(Path.Combine(assemblyDir, "..", "..", "..", "data", "kaggle")));
        }

        // Relative to current working directory
        var cwd = Directory.GetCurrentDirectory();
        candidates.Add(Path.Combine(cwd, "data", "kaggle"));
        candidates.Add(Path.Combine(cwd, "..", "data", "kaggle"));
        candidates.Add(Path.Combine(cwd, "..", "..", "data", "kaggle"));
        candidates.Add(Path.Combine(cwd, "..", "..", "..", "data", "kaggle"));

        // Search up from the source file location
        var sourceDir = Path.GetDirectoryName(typeof(DataLoader).Assembly.Location);
        if (sourceDir is not null)
        {
            for (int i = 0; i < 6; i++)
            {
                candidates.Add(Path.Combine(sourceDir, "data", "kaggle"));
                sourceDir = Path.GetDirectoryName(sourceDir);
                if (sourceDir is null) break;
            }
        }

        foreach (var candidate in candidates)
        {
            var full = Path.GetFullPath(candidate);
            if (Directory.Exists(full))
                return full;
        }

        // Hard-coded fallback for the workspace layout
        return Path.GetFullPath(Path.Combine(cwd, "..", "data", "kaggle"));
    }
}