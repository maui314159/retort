using System.Globalization;
using System.Text;
using BrazilianSoccerMcpServer.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcpServer.Data;

public sealed class SoccerDataStore
{
    public List<Match> Matches { get; } = new();
    public List<Player> Players { get; } = new();

    public bool IsLoaded { get; set; }
}

public static class CsvLoader
{
    public static SoccerDataStore LoadFromDirectory(string directory)
    {
        var store = new SoccerDataStore();
        var dataPath = Path.Combine(directory, "data", "kaggle");

        LoadBrasileiraoMatches(store, Path.Combine(dataPath, "Brasileirao_Matches.csv"));
        LoadCopaDoBrasilMatches(store, Path.Combine(dataPath, "Brazilian_Cup_Matches.csv"));
        LoadLibertadoresMatches(store, Path.Combine(dataPath, "Libertadores_Matches.csv"));
        LoadBrFootballDataset(store, Path.Combine(dataPath, "BR-Football-Dataset.csv"));
        LoadNovoCampeonato(store, Path.Combine(dataPath, "novo_campeonato_brasileiro.csv"));
        LoadFifaPlayers(store, Path.Combine(dataPath, "fifa_data.csv"));

        store.IsLoaded = true;
        store.Matches.Sort((a, b) => Nullable.Compare(b.Date, a.Date));
        return store;
    }

    private static CsvConfiguration BaseConfig => new(CultureInfo.InvariantCulture)
    {
        HeaderValidated = null,
        MissingFieldFound = null,
        BadDataFound = null,
        TrimOptions = TrimOptions.Trim,
    };

    private static void LoadBrasileiraoMatches(SoccerDataStore store, string path)
    {
        if (!File.Exists(path)) return;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HeaderValidated = null,
            MissingFieldFound = null,
            BadDataFound = null,
            TrimOptions = TrimOptions.Trim,
        };

        using var reader = new StreamReader(path, Encoding.UTF8);
        using var csv = new CsvReader(reader, config);
        var records = csv.GetRecords<BrasileiraoMatchRecord>();
        foreach (var r in records)
        {
            if (!int.TryParse(r.season, out var season)) continue;
            if (!TryParseGoals(r.home_goal, out var homeGoals)) continue;
            if (!TryParseGoals(r.away_goal, out var awayGoals)) continue;

            var date = ParseDateTime(r.datetime);
            var home = r.home_team ?? string.Empty;
            var away = r.away_team ?? string.Empty;

            store.Matches.Add(new Match
            {
                MatchId = store.Matches.Count + 1,
                Date = date,
                HomeTeam = home,
                AwayTeam = away,
                NormalizedHomeTeam = NameNormalizer.Normalize(home),
                NormalizedAwayTeam = NameNormalizer.Normalize(away),
                HomeGoals = homeGoals,
                AwayGoals = awayGoals,
                Competition = "Brasileirão",
                Season = season,
                Round = r.round,
                HomeState = r.home_team_state,
                AwayState = r.away_team_state,
                Source = "Brasileirao_Matches.csv",
            });
        }
    }

    private static void LoadCopaDoBrasilMatches(SoccerDataStore store, string path)
    {
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path, Encoding.UTF8);
        using var csv = new CsvReader(reader, BaseConfig);
        var records = csv.GetRecords<CopaDoBrasilMatchRecord>();
        foreach (var r in records)
        {
            if (!int.TryParse(r.season, out var season)) continue;
            if (!TryParseGoals(r.home_goal, out var homeGoals)) continue;
            if (!TryParseGoals(r.away_goal, out var awayGoals)) continue;

            var date = ParseDateTime(r.datetime);
            var home = r.home_team ?? string.Empty;
            var away = r.away_team ?? string.Empty;

            store.Matches.Add(new Match
            {
                MatchId = store.Matches.Count + 1,
                Date = date,
                HomeTeam = home,
                AwayTeam = away,
                NormalizedHomeTeam = NameNormalizer.Normalize(home),
                NormalizedAwayTeam = NameNormalizer.Normalize(away),
                HomeGoals = homeGoals,
                AwayGoals = awayGoals,
                Competition = "Copa do Brasil",
                Season = season,
                Round = r.round,
                Source = "Brazilian_Cup_Matches.csv",
            });
        }
    }

    private static void LoadLibertadoresMatches(SoccerDataStore store, string path)
    {
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path, Encoding.UTF8);
        using var csv = new CsvReader(reader, BaseConfig);
        var records = csv.GetRecords<LibertadoresMatchRecord>();
        foreach (var r in records)
        {
            if (!int.TryParse(r.season, out var season)) continue;
            if (!TryParseGoals(r.home_goal, out var homeGoals)) continue;
            if (!TryParseGoals(r.away_goal, out var awayGoals)) continue;

            var date = ParseDateTime(r.datetime);
            var home = r.home_team ?? string.Empty;
            var away = r.away_team ?? string.Empty;

            store.Matches.Add(new Match
            {
                MatchId = store.Matches.Count + 1,
                Date = date,
                HomeTeam = home,
                AwayTeam = away,
                NormalizedHomeTeam = NameNormalizer.Normalize(home),
                NormalizedAwayTeam = NameNormalizer.Normalize(away),
                HomeGoals = homeGoals,
                AwayGoals = awayGoals,
                Competition = "Copa Libertadores",
                Season = season,
                Stage = r.stage,
                Source = "Libertadores_Matches.csv",
            });
        }
    }

    private static void LoadBrFootballDataset(SoccerDataStore store, string path)
    {
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path, Encoding.UTF8);
        using var csv = new CsvReader(reader, BaseConfig);
        var records = csv.GetRecords<BrFootballMatchRecord>();
        foreach (var r in records)
        {
            if (!TryParseGoals(r.home_goal, out var homeGoals)) continue;
            if (!TryParseGoals(r.away_goal, out var awayGoals)) continue;
            if (!int.TryParse(r.date?.Replace("-", "").Substring(0, 4), out var season) && !int.TryParse(r.date?.Split('-').FirstOrDefault(), out season))
            {
                if (!TryParseDate(r.date, out var parsedDate))
                    continue;
                season = parsedDate.Year;
            }

            var date = TryParseDate(r.date, out var d) ? d : (DateTime?)null;
            var home = r.home ?? string.Empty;
            var away = r.away ?? string.Empty;

            store.Matches.Add(new Match
            {
                MatchId = store.Matches.Count + 1,
                Date = date,
                HomeTeam = home,
                AwayTeam = away,
                NormalizedHomeTeam = NameNormalizer.Normalize(home),
                NormalizedAwayTeam = NameNormalizer.Normalize(away),
                HomeGoals = homeGoals,
                AwayGoals = awayGoals,
                Competition = r.tournament ?? "Brazilian Football",
                Season = season,
                HomeCorners = ParseDouble(r.home_corner),
                AwayCorners = ParseDouble(r.away_corner),
                HomeShots = ParseDouble(r.home_shots),
                AwayShots = ParseDouble(r.away_shots),
                HalfTimeResult = r.ht_result,
                Source = "BR-Football-Dataset.csv",
            });
        }
    }

    private static void LoadNovoCampeonato(SoccerDataStore store, string path)
    {
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path, Encoding.UTF8);
        using var csv = new CsvReader(reader, BaseConfig);
        var records = csv.GetRecords<NovoCampeonatoRecord>();
        foreach (var r in records)
        {
            if (!int.TryParse(r.Ano, out var season)) continue;
            if (!TryParseGoals(r.Gols_mandante, out var homeGoals)) continue;
            if (!TryParseGoals(r.Gols_visitante, out var awayGoals)) continue;

            var date = TryParseDate(r.Data, out var d) ? d : (DateTime?)null;
            var home = r.Equipe_mandante ?? string.Empty;
            var away = r.Equipe_visitante ?? string.Empty;

            store.Matches.Add(new Match
            {
                MatchId = store.Matches.Count + 1,
                Date = date,
                HomeTeam = home,
                AwayTeam = away,
                NormalizedHomeTeam = NameNormalizer.Normalize(home),
                NormalizedAwayTeam = NameNormalizer.Normalize(away),
                HomeGoals = homeGoals,
                AwayGoals = awayGoals,
                Competition = "Brasileirão",
                Season = season,
                Round = r.Rodada,
                HomeState = r.Mandante_UF,
                AwayState = r.Visitante_UF,
                Stadium = r.Arena,
                Source = "novo_campeonato_brasileiro.csv",
            });
        }
    }

    private static void LoadFifaPlayers(SoccerDataStore store, string path)
    {
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path, Encoding.UTF8);
        using var csv = new CsvReader(reader, BaseConfig);
        var records = csv.GetRecords<FifaPlayerRecord>();
        foreach (var r in records)
        {
            if (!int.TryParse(r.ID, out var id)) continue;

            store.Players.Add(new Player
            {
                Id = id,
                Name = r.Name ?? string.Empty,
                Age = int.TryParse(r.Age, out var age) ? age : 0,
                Nationality = r.Nationality ?? string.Empty,
                Overall = int.TryParse(r.Overall, out var overall) ? overall : 0,
                Potential = int.TryParse(r.Potential, out var potential) ? potential : 0,
                Club = r.Club ?? string.Empty,
                Position = r.Position ?? string.Empty,
                JerseyNumber = r.Jersey_Number,
                Height = r.Height,
                Weight = r.Weight,
                Crossing = NullableInt(r.Crossing),
                Finishing = NullableInt(r.Finishing),
                Dribbling = NullableInt(r.Dribbling),
                ShortPassing = NullableInt(r.ShortPassing),
            });
        }
    }

    private static bool TryParseGoals(string? value, out int? goals)
    {
        goals = null;
        if (string.IsNullOrWhiteSpace(value)) return false;
        if (int.TryParse(value, out var g))
        {
            goals = g;
            return true;
        }
        return false;
    }

    private static double? ParseDouble(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        if (double.TryParse(value, NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
            return d;
        return null;
    }

    private static int? NullableInt(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        if (int.TryParse(value, out var i))
            return i;
        return null;
    }

    private static DateTime? ParseDateTime(string? value)
    {
        if (TryParseDate(value, out var date))
            return date;
        return null;
    }

    private static bool TryParseDate(string? value, out DateTime date)
    {
        date = default;
        if (string.IsNullOrWhiteSpace(value)) return false;

        var formats = new[]
        {
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd",
            "dd/MM/yyyy",
            "MM/dd/yyyy",
        };

        if (DateTime.TryParseExact(value.Trim(), formats, CultureInfo.InvariantCulture, DateTimeStyles.None, out date))
            return true;

        if (DateTime.TryParse(value, CultureInfo.InvariantCulture, DateTimeStyles.None, out date))
            return true;

        return false;
    }

    private sealed class BrasileiraoMatchRecord
    {
        public string? datetime { get; set; }
        public string? home_team { get; set; }
        public string? home_team_state { get; set; }
        public string? away_team { get; set; }
        public string? away_team_state { get; set; }
        public string? home_goal { get; set; }
        public string? away_goal { get; set; }
        public string? season { get; set; }
        public string? round { get; set; }
    }

    private sealed class CopaDoBrasilMatchRecord
    {
        public string? round { get; set; }
        public string? datetime { get; set; }
        public string? home_team { get; set; }
        public string? away_team { get; set; }
        public string? home_goal { get; set; }
        public string? away_goal { get; set; }
        public string? season { get; set; }
    }

    private sealed class LibertadoresMatchRecord
    {
        public string? datetime { get; set; }
        public string? home_team { get; set; }
        public string? away_team { get; set; }
        public string? home_goal { get; set; }
        public string? away_goal { get; set; }
        public string? season { get; set; }
        public string? stage { get; set; }
    }

    private sealed class BrFootballMatchRecord
    {
        public string? tournament { get; set; }
        public string? home { get; set; }
        public string? home_goal { get; set; }
        public string? away_goal { get; set; }
        public string? away { get; set; }
        public string? home_corner { get; set; }
        public string? away_corner { get; set; }
        public string? home_attack { get; set; }
        public string? away_attack { get; set; }
        public string? home_shots { get; set; }
        public string? away_shots { get; set; }
        public string? time { get; set; }
        public string? date { get; set; }
        public string? ht_diff { get; set; }
        public string? at_diff { get; set; }
        public string? ht_result { get; set; }
        public string? at_result { get; set; }
        public string? total_corners { get; set; }
    }

    private sealed class NovoCampeonatoRecord
    {
        public string? ID { get; set; }
        public string? Data { get; set; }
        public string? Ano { get; set; }
        public string? Rodada { get; set; }
        public string? Equipe_mandante { get; set; }
        public string? Equipe_visitante { get; set; }
        public string? Gols_mandante { get; set; }
        public string? Gols_visitante { get; set; }
        public string? Mandante_UF { get; set; }
        public string? Visitante_UF { get; set; }
        public string? Vencedor { get; set; }
        public string? Arena { get; set; }
        public string? OBS { get; set; }
    }

    private sealed class FifaPlayerRecord
    {
        public string? ID { get; set; }
        public string? Name { get; set; }
        public string? Age { get; set; }
        public string? Photo { get; set; }
        public string? Nationality { get; set; }
        public string? Flag { get; set; }
        public string? Overall { get; set; }
        public string? Potential { get; set; }
        public string? Club { get; set; }
        public string? Club_Logo { get; set; }
        public string? Value { get; set; }
        public string? Wage { get; set; }
        public string? Special { get; set; }
        public string? Preferred_Foot { get; set; }
        public string? International_Reputation { get; set; }
        public string? Weak_Foot { get; set; }
        public string? Skill_Moves { get; set; }
        public string? Work_Rate { get; set; }
        public string? Body_Type { get; set; }
        public string? Real_Face { get; set; }
        public string? Position { get; set; }
        public string? Jersey_Number { get; set; }
        public string? Joined { get; set; }
        public string? Loaned_From { get; set; }
        public string? Contract_Valid_Until { get; set; }
        public string? Height { get; set; }
        public string? Weight { get; set; }
        public string? Crossing { get; set; }
        public string? Finishing { get; set; }
        public string? HeadingAccuracy { get; set; }
        public string? ShortPassing { get; set; }
        public string? Volleys { get; set; }
        public string? Dribbling { get; set; }
    }
}
