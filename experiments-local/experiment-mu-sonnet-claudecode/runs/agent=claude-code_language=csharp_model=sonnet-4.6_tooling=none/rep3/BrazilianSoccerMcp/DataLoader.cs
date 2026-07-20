using CsvHelper;
using CsvHelper.Configuration;
using System.Globalization;
using System.Text;

namespace BrazilianSoccerMcp;

public class DataLoader
{
    private static readonly string[] DateFormats = [
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd",
        "dd/MM/yyyy",
        "M/d/yyyy",
    ];

    private static DateTime ParseDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return DateTime.MinValue;
        s = s.Trim().Trim('"');
        foreach (var fmt in DateFormats)
        {
            if (DateTime.TryParseExact(s, fmt, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt))
                return dt;
        }
        if (DateTime.TryParse(s, out var dt2)) return dt2;
        return DateTime.MinValue;
    }

    private static int ParseInt(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return 0;
        s = s.Trim().Trim('"');
        if (double.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
            return (int)d;
        return 0;
    }

    private static int? ParseNullableInt(string? s)
    {
        if (string.IsNullOrWhiteSpace(s) || s.Trim() == "\"\"") return null;
        s = s.Trim().Trim('"');
        if (double.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
            return (int)d;
        return null;
    }

    private static CsvReader CreateReader(string path)
    {
        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            BadDataFound = null,
            MissingFieldFound = null,
            HeaderValidated = null,
            Encoding = Encoding.UTF8,
        };
        var reader = new StreamReader(path, Encoding.UTF8);
        return new CsvReader(reader, config);
    }

    public static List<Match> LoadBrasileiraoMatches(string path)
    {
        var matches = new List<Match>();
        using var csv = CreateReader(path);
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            matches.Add(new Match
            {
                Date = ParseDate(csv.GetField("datetime")),
                HomeTeam = NormalizeTeam(csv.GetField("home_team") ?? ""),
                AwayTeam = NormalizeTeam(csv.GetField("away_team") ?? ""),
                HomeGoals = ParseInt(csv.GetField("home_goal")),
                AwayGoals = ParseInt(csv.GetField("away_goal")),
                Season = ParseInt(csv.GetField("season")),
                Round = csv.GetField("round") ?? "",
                Competition = "Brasileirão Série A",
                HomeState = csv.GetField("home_team_state"),
                AwayState = csv.GetField("away_team_state"),
            });
        }
        return matches;
    }

    public static List<Match> LoadCupMatches(string path)
    {
        var matches = new List<Match>();
        using var csv = CreateReader(path);
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            matches.Add(new Match
            {
                Date = ParseDate(csv.GetField("datetime")),
                HomeTeam = NormalizeTeam(csv.GetField("home_team") ?? ""),
                AwayTeam = NormalizeTeam(csv.GetField("away_team") ?? ""),
                HomeGoals = ParseInt(csv.GetField("home_goal")),
                AwayGoals = ParseInt(csv.GetField("away_goal")),
                Season = ParseInt(csv.GetField("season")),
                Round = csv.GetField("round") ?? "",
                Competition = "Copa do Brasil",
            });
        }
        return matches;
    }

    public static List<Match> LoadLibertadoresMatches(string path)
    {
        var matches = new List<Match>();
        using var csv = CreateReader(path);
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            matches.Add(new Match
            {
                Date = ParseDate(csv.GetField("datetime")),
                HomeTeam = NormalizeTeam(csv.GetField("home_team") ?? ""),
                AwayTeam = NormalizeTeam(csv.GetField("away_team") ?? ""),
                HomeGoals = ParseInt(csv.GetField("home_goal")),
                AwayGoals = ParseInt(csv.GetField("away_goal")),
                Season = ParseInt(csv.GetField("season")),
                Stage = csv.GetField("stage") ?? "",
                Competition = "Copa Libertadores",
            });
        }
        return matches;
    }

    public static List<Match> LoadBrFootballDataset(string path)
    {
        var matches = new List<Match>();
        using var csv = CreateReader(path);
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            var dateStr = csv.GetField("date") ?? "";
            var timeStr = csv.GetField("time") ?? "";
            DateTime date = ParseDate(dateStr);

            matches.Add(new Match
            {
                Date = date,
                HomeTeam = NormalizeTeam(csv.GetField("home") ?? ""),
                AwayTeam = NormalizeTeam(csv.GetField("away") ?? ""),
                HomeGoals = ParseInt(csv.GetField("home_goal")),
                AwayGoals = ParseInt(csv.GetField("away_goal")),
                Season = date.Year,
                Competition = csv.GetField("tournament") ?? "Unknown",
                Round = "",
            });
        }
        return matches;
    }

    public static List<Match> LoadHistoricalBrasileirao(string path)
    {
        var matches = new List<Match>();
        using var csv = CreateReader(path);
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            matches.Add(new Match
            {
                Date = ParseDate(csv.GetField("Data")),
                HomeTeam = NormalizeTeam(csv.GetField("Equipe_mandante") ?? ""),
                AwayTeam = NormalizeTeam(csv.GetField("Equipe_visitante") ?? ""),
                HomeGoals = ParseInt(csv.GetField("Gols_mandante")),
                AwayGoals = ParseInt(csv.GetField("Gols_visitante")),
                Season = ParseInt(csv.GetField("Ano")),
                Round = csv.GetField("Rodada") ?? "",
                Competition = "Brasileirão Série A",
                HomeState = csv.GetField("Mandante_UF"),
                AwayState = csv.GetField("Visitante_UF"),
                Arena = csv.GetField("Arena"),
            });
        }
        return matches;
    }

    public static List<Player> LoadFifaData(string path)
    {
        var players = new List<Player>();
        using var csv = CreateReader(path);
        csv.Read(); csv.ReadHeader();
        while (csv.Read())
        {
            players.Add(new Player
            {
                Id = ParseInt(csv.GetField("ID")),
                Name = csv.GetField("Name") ?? "",
                Age = ParseInt(csv.GetField("Age")),
                Nationality = csv.GetField("Nationality") ?? "",
                Overall = ParseInt(csv.GetField("Overall")),
                Potential = ParseInt(csv.GetField("Potential")),
                Club = csv.GetField("Club") ?? "",
                Position = csv.GetField("Position") ?? "",
                JerseyNumber = csv.GetField("Jersey Number"),
                Height = csv.GetField("Height"),
                Weight = csv.GetField("Weight"),
                Value = csv.GetField("Value"),
                Wage = csv.GetField("Wage"),
                Crossing = ParseNullableInt(csv.GetField("Crossing")),
                Finishing = ParseNullableInt(csv.GetField("Finishing")),
                Dribbling = ParseNullableInt(csv.GetField("Dribbling")),
                Passing = ParseNullableInt(csv.GetField("ShortPassing")),
                GkDiving = ParseNullableInt(csv.GetField("GKDiving")),
                GkHandling = ParseNullableInt(csv.GetField("GKHandling")),
                GkKicking = ParseNullableInt(csv.GetField("GKKicking")),
                GkPositioning = ParseNullableInt(csv.GetField("GKPositioning")),
                GkReflexes = ParseNullableInt(csv.GetField("GKReflexes")),
            });
        }
        return players;
    }

    public static string NormalizeTeam(string name)
    {
        if (string.IsNullOrWhiteSpace(name)) return name;
        name = name.Trim().Trim('"');
        // Remove state suffix like "-SP", "-RJ" etc.
        var idx = name.LastIndexOf('-');
        if (idx > 0 && idx == name.Length - 3 && name.Substring(idx + 1).All(char.IsUpper))
            name = name.Substring(0, idx).Trim();
        return name;
    }

    public static bool TeamMatches(string teamInData, string searchTerm)
    {
        if (string.IsNullOrWhiteSpace(searchTerm)) return false;
        var normalized = NormalizeTeam(teamInData);
        return normalized.Contains(searchTerm, StringComparison.OrdinalIgnoreCase)
            || teamInData.Contains(searchTerm, StringComparison.OrdinalIgnoreCase);
    }
}
