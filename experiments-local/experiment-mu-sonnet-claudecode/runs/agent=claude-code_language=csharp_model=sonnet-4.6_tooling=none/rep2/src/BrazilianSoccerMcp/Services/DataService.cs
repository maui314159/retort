using System.Globalization;
using BrazilianSoccerMcp.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Services;

public class DataService
{
    public List<MatchRecord> Matches { get; private set; } = [];
    public List<PlayerRecord> Players { get; private set; } = [];
    public bool IsLoaded { get; private set; }

    private static string? FindDataDirectory(string? hint = null)
    {
        if (hint != null && Directory.Exists(hint))
            return hint;

        var dir = AppContext.BaseDirectory;
        for (var i = 0; i < 10; i++)
        {
            var candidate = Path.Combine(dir, "data", "kaggle");
            if (Directory.Exists(candidate))
                return candidate;
            var parent = Directory.GetParent(dir)?.FullName;
            if (parent == null) break;
            dir = parent;
        }
        return null;
    }

    public async Task LoadAsync(string? dataDirectory = null)
    {
        if (IsLoaded) return;

        var dataDir = dataDirectory ?? FindDataDirectory();
        if (dataDir == null)
            throw new DirectoryNotFoundException("Could not find data/kaggle directory");

        var matches = new List<MatchRecord>();

        await Task.Run(() =>
        {
            matches.AddRange(LoadBrasileiraoMatches(Path.Combine(dataDir, "Brasileirao_Matches.csv")));
            matches.AddRange(LoadCupMatches(Path.Combine(dataDir, "Brazilian_Cup_Matches.csv")));
            matches.AddRange(LoadLibertadoresMatches(Path.Combine(dataDir, "Libertadores_Matches.csv")));
            matches.AddRange(LoadExtendedMatches(Path.Combine(dataDir, "BR-Football-Dataset.csv")));
            matches.AddRange(LoadHistoricalMatches(Path.Combine(dataDir, "novo_campeonato_brasileiro.csv")));
            Players.AddRange(LoadPlayers(Path.Combine(dataDir, "fifa_data.csv")));
        });

        Matches = matches;
        IsLoaded = true;
    }

    private static IEnumerable<MatchRecord> LoadBrasileiraoMatches(string path)
    {
        if (!File.Exists(path)) yield break;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
        };

        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, config);

        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var homeTeam = csv.GetField("home_team") ?? "";
            var awayTeam = csv.GetField("away_team") ?? "";
            var dateStr = csv.GetField("datetime") ?? "";

            yield return new MatchRecord
            {
                Competition = "Brasileirão Serie A",
                HomeTeam = homeTeam,
                AwayTeam = awayTeam,
                NormalizedHomeTeam = TeamNameNormalizer.Normalize(homeTeam),
                NormalizedAwayTeam = TeamNameNormalizer.Normalize(awayTeam),
                HomeGoal = ParseInt(csv.GetField("home_goal")),
                AwayGoal = ParseInt(csv.GetField("away_goal")),
                Date = ParseDateTime(dateStr),
                Season = ParseInt(csv.GetField("season")),
                Round = csv.GetField("round"),
            };
        }
    }

    private static IEnumerable<MatchRecord> LoadCupMatches(string path)
    {
        if (!File.Exists(path)) yield break;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
        };

        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, config);

        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var homeTeam = csv.GetField("home_team") ?? "";
            var awayTeam = csv.GetField("away_team") ?? "";
            var dateStr = csv.GetField("datetime") ?? "";

            yield return new MatchRecord
            {
                Competition = "Copa do Brasil",
                HomeTeam = homeTeam,
                AwayTeam = awayTeam,
                NormalizedHomeTeam = TeamNameNormalizer.Normalize(homeTeam),
                NormalizedAwayTeam = TeamNameNormalizer.Normalize(awayTeam),
                HomeGoal = ParseInt(csv.GetField("home_goal")),
                AwayGoal = ParseInt(csv.GetField("away_goal")),
                Date = ParseDateTime(dateStr),
                Season = ParseInt(csv.GetField("season")),
                Round = csv.GetField("round"),
            };
        }
    }

    private static IEnumerable<MatchRecord> LoadLibertadoresMatches(string path)
    {
        if (!File.Exists(path)) yield break;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
        };

        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, config);

        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var homeTeam = csv.GetField("home_team") ?? "";
            var awayTeam = csv.GetField("away_team") ?? "";
            var dateStr = csv.GetField("datetime") ?? "";

            yield return new MatchRecord
            {
                Competition = "Copa Libertadores",
                HomeTeam = homeTeam,
                AwayTeam = awayTeam,
                NormalizedHomeTeam = TeamNameNormalizer.Normalize(homeTeam),
                NormalizedAwayTeam = TeamNameNormalizer.Normalize(awayTeam),
                HomeGoal = ParseInt(csv.GetField("home_goal")),
                AwayGoal = ParseInt(csv.GetField("away_goal")),
                Date = ParseDateTime(dateStr),
                Season = ParseInt(csv.GetField("season")),
                Stage = csv.GetField("stage"),
            };
        }
    }

    private static IEnumerable<MatchRecord> LoadExtendedMatches(string path)
    {
        if (!File.Exists(path)) yield break;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
        };

        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, config);

        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var homeTeam = csv.GetField("home") ?? "";
            var awayTeam = csv.GetField("away") ?? "";
            var dateStr = csv.GetField("date") ?? "";
            var tournament = csv.GetField("tournament") ?? "";

            var date = ParseDate(dateStr);
            yield return new MatchRecord
            {
                Competition = tournament,
                HomeTeam = homeTeam,
                AwayTeam = awayTeam,
                NormalizedHomeTeam = TeamNameNormalizer.Normalize(homeTeam),
                NormalizedAwayTeam = TeamNameNormalizer.Normalize(awayTeam),
                HomeGoal = ParseFloat(csv.GetField("home_goal")),
                AwayGoal = ParseFloat(csv.GetField("away_goal")),
                Date = date,
                Season = date?.Year,
                Stage = csv.GetField("ht_result"),
            };
        }
    }

    private static IEnumerable<MatchRecord> LoadHistoricalMatches(string path)
    {
        if (!File.Exists(path)) yield break;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
        };

        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, config);

        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var homeTeam = csv.GetField("Equipe_mandante") ?? "";
            var awayTeam = csv.GetField("Equipe_visitante") ?? "";
            var dateStr = csv.GetField("Data") ?? "";

            yield return new MatchRecord
            {
                Competition = "Brasileirão Serie A (Historical)",
                HomeTeam = homeTeam,
                AwayTeam = awayTeam,
                NormalizedHomeTeam = TeamNameNormalizer.Normalize(homeTeam),
                NormalizedAwayTeam = TeamNameNormalizer.Normalize(awayTeam),
                HomeGoal = ParseInt(csv.GetField("Gols_mandante")),
                AwayGoal = ParseInt(csv.GetField("Gols_visitante")),
                Date = ParseBrazilianDate(dateStr),
                Season = ParseInt(csv.GetField("Ano")),
                Round = csv.GetField("Rodada"),
            };
        }
    }

    private static IEnumerable<PlayerRecord> LoadPlayers(string path)
    {
        if (!File.Exists(path)) yield break;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
        };

        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, config);

        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            yield return new PlayerRecord
            {
                Id = ParseInt(csv.GetField("ID")),
                Name = csv.GetField("Name") ?? "",
                Age = ParseInt(csv.GetField("Age")),
                Nationality = csv.GetField("Nationality") ?? "",
                Overall = ParseInt(csv.GetField("Overall")),
                Potential = ParseInt(csv.GetField("Potential")),
                Club = csv.GetField("Club") ?? "",
                Position = csv.GetField("Position") ?? "",
                PreferredFoot = csv.GetField("Preferred Foot"),
                JerseyNumber = ParseInt(csv.GetField("Jersey Number")),
                Height = csv.GetField("Height"),
                Weight = csv.GetField("Weight"),
                Crossing = ParseStatField(csv.GetField("Crossing")),
                Finishing = ParseStatField(csv.GetField("Finishing")),
                Dribbling = ParseStatField(csv.GetField("Dribbling")),
                ShortPassing = ParseStatField(csv.GetField("ShortPassing")),
                Acceleration = ParseStatField(csv.GetField("Acceleration")),
                SprintSpeed = ParseStatField(csv.GetField("SprintSpeed")),
                Stamina = ParseStatField(csv.GetField("Stamina")),
                Strength = ParseStatField(csv.GetField("Strength")),
                GkDiving = ParseStatField(csv.GetField("GKDiving")),
                GkHandling = ParseStatField(csv.GetField("GKHandling")),
                GkReflexes = ParseStatField(csv.GetField("GKReflexes")),
                SkillMoves = ParseInt(csv.GetField("Skill Moves")),
                WeakFoot = ParseInt(csv.GetField("Weak Foot")),
            };
        }
    }

    private static int? ParseInt(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        if (int.TryParse(s.Trim(), out var n)) return n;
        return null;
    }

    private static int? ParseFloat(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        if (double.TryParse(s.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
            return (int)d;
        return null;
    }

    private static int? ParseStatField(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        // FIFA stats may have format like "88+2"
        var idx = s.IndexOf('+');
        if (idx > 0) s = s[..idx];
        idx = s.IndexOf('-');
        if (idx > 0) s = s[..idx];
        if (int.TryParse(s.Trim(), out var n)) return n;
        return null;
    }

    private static DateTime? ParseDateTime(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        if (DateTime.TryParse(s, out var dt)) return dt;
        return null;
    }

    private static DateTime? ParseDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        if (DateTime.TryParseExact(s, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt))
            return dt;
        if (DateTime.TryParse(s, out var dt2)) return dt2;
        return null;
    }

    private static DateTime? ParseBrazilianDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        if (DateTime.TryParseExact(s, "dd/MM/yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt))
            return dt;
        if (DateTime.TryParse(s, out var dt2)) return dt2;
        return null;
    }
}
