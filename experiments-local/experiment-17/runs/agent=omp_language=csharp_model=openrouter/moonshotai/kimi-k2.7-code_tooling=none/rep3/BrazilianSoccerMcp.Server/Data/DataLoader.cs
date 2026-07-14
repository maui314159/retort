using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Server.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Server.Data;

public sealed class DataLoader
{
    private readonly string _dataDirectory;

    public DataLoader(string dataDirectory)
    {
        _dataDirectory = dataDirectory;
    }

    public SoccerDataContext Load()
    {
        var matches = new List<MatchRecord>();

        matches.AddRange(LoadBrasileirao());
        matches.AddRange(LoadCup());
        matches.AddRange(LoadLibertadores());
        matches.AddRange(LoadBrFootball());
        matches.AddRange(LoadHistorical());

        var players = LoadPlayers();

        return new SoccerDataContext(matches, players);
    }

    private string GetPath(string fileName) => Path.Combine(_dataDirectory, fileName);

    private static CsvReader CreateReader(string path)
    {
        var stream = File.OpenRead(path);
        var reader = new StreamReader(stream, Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HeaderValidated = null,
            MissingFieldFound = null,
            BadDataFound = null
        });
        return csv;
    }

    private IEnumerable<MatchRecord> LoadBrasileirao()
    {
        using var csv = CreateReader(GetPath("Brasileirao_Matches.csv"));
        foreach (var row in csv.GetRecords<dynamic>())
        {
            var dict = (IDictionary<string, object>)row;
            yield return new MatchRecord(
                Competition: "Brasileirão",
                Date: ParseDateTime(GetString(dict, "datetime")),
                HomeTeam: GetString(dict, "home_team"),
                AwayTeam: GetString(dict, "away_team"),
                HomeGoals: ParseInt(GetString(dict, "home_goal")),
                AwayGoals: ParseInt(GetString(dict, "away_goal")),
                Season: ParseIntNullable(GetString(dict, "season")),
                Round: GetString(dict, "round"),
                Stage: null,
                Stadium: null,
                SourceFile: "Brasileirao_Matches.csv");
        }
    }

    private IEnumerable<MatchRecord> LoadCup()
    {
        using var csv = CreateReader(GetPath("Brazilian_Cup_Matches.csv"));
        foreach (var row in csv.GetRecords<dynamic>())
        {
            var dict = (IDictionary<string, object>)row;
            yield return new MatchRecord(
                Competition: "Copa do Brasil",
                Date: ParseDateTime(GetString(dict, "datetime")),
                HomeTeam: GetString(dict, "home_team"),
                AwayTeam: GetString(dict, "away_team"),
                HomeGoals: ParseInt(GetString(dict, "home_goal")),
                AwayGoals: ParseInt(GetString(dict, "away_goal")),
                Season: ParseIntNullable(GetString(dict, "season")),
                Round: GetString(dict, "round"),
                Stage: null,
                Stadium: null,
                SourceFile: "Brazilian_Cup_Matches.csv");
        }
    }

    private IEnumerable<MatchRecord> LoadLibertadores()
    {
        using var csv = CreateReader(GetPath("Libertadores_Matches.csv"));
        foreach (var row in csv.GetRecords<dynamic>())
        {
            var dict = (IDictionary<string, object>)row;
            yield return new MatchRecord(
                Competition: "Copa Libertadores",
                Date: ParseDateTime(GetString(dict, "datetime")),
                HomeTeam: GetString(dict, "home_team"),
                AwayTeam: GetString(dict, "away_team"),
                HomeGoals: ParseInt(GetString(dict, "home_goal")),
                AwayGoals: ParseInt(GetString(dict, "away_goal")),
                Season: ParseIntNullable(GetString(dict, "season")),
                Round: null,
                Stage: GetString(dict, "stage"),
                Stadium: null,
                SourceFile: "Libertadores_Matches.csv");
        }
    }

    private IEnumerable<MatchRecord> LoadBrFootball()
    {
        using var csv = CreateReader(GetPath("BR-Football-Dataset.csv"));
        foreach (var row in csv.GetRecords<dynamic>())
        {
            var dict = (IDictionary<string, object>)row;
            var comp = GetString(dict, "tournament");
            var time = GetString(dict, "time");
            var date = GetString(dict, "date");
            var dateTime = ParseDateTime(date);
            if (dateTime.HasValue && !string.IsNullOrWhiteSpace(time))
            {
                if (TimeSpan.TryParse(time, out var ts))
                {
                    dateTime = dateTime.Value.Date + ts;
                }
            }

            yield return new MatchRecord(
                Competition: comp,
                Date: dateTime,
                HomeTeam: GetString(dict, "home"),
                AwayTeam: GetString(dict, "away"),
                HomeGoals: ParseInt(GetString(dict, "home_goal")),
                AwayGoals: ParseInt(GetString(dict, "away_goal")),
                Season: dateTime?.Year,
                Round: null,
                Stage: null,
                Stadium: null,
                SourceFile: "BR-Football-Dataset.csv");
        }
    }

    private IEnumerable<MatchRecord> LoadHistorical()
    {
        using var csv = CreateReader(GetPath("novo_campeonato_brasileiro.csv"));
        foreach (var row in csv.GetRecords<dynamic>())
        {
            var dict = (IDictionary<string, object>)row;
            yield return new MatchRecord(
                Competition: "Brasileirão",
                Date: ParseDateTime(GetString(dict, "Data")),
                HomeTeam: GetString(dict, "Equipe_mandante"),
                AwayTeam: GetString(dict, "Equipe_visitante"),
                HomeGoals: ParseInt(GetString(dict, "Gols_mandante")),
                AwayGoals: ParseInt(GetString(dict, "Gols_visitante")),
                Season: ParseIntNullable(GetString(dict, "Ano")),
                Round: GetString(dict, "Rodada"),
                Stage: null,
                Stadium: GetString(dict, "Arena"),
                SourceFile: "novo_campeonato_brasileiro.csv");
        }
    }

    private IReadOnlyList<PlayerRecord> LoadPlayers()
    {
        var players = new List<PlayerRecord>();
        using var csv = CreateReader(GetPath("fifa_data.csv"));
        foreach (var row in csv.GetRecords<dynamic>())
        {
            var dict = (IDictionary<string, object>)row;
            players.Add(new PlayerRecord(
                Id: ParseInt(GetString(dict, "ID")),
                Name: GetString(dict, "Name"),
                Age: ParseIntNullable(GetString(dict, "Age")),
                Nationality: GetString(dict, "Nationality"),
                Overall: ParseIntNullable(GetString(dict, "Overall")),
                Potential: ParseIntNullable(GetString(dict, "Potential")),
                Club: GetString(dict, "Club"),
                Position: GetString(dict, "Position"),
                JerseyNumber: ParseIntNullable(GetString(dict, "Jersey Number")),
                Height: GetString(dict, "Height"),
                Weight: GetString(dict, "Weight")));
        }
        return players;
    }

    private static string GetString(IDictionary<string, object> dict, string key)
    {
        if (dict.TryGetValue(key, out var value) && value is not null)
        {
            return value.ToString()?.Trim() ?? string.Empty;
        }

        // Try case-insensitive fallback
        var match = dict.Keys.FirstOrDefault(k =>
            k.Equals(key, StringComparison.OrdinalIgnoreCase));
        if (match is not null && dict[match] is not null)
        {
            return dict[match]?.ToString()?.Trim() ?? string.Empty;
        }

        return string.Empty;
    }

    private static int ParseInt(string value)
    {
        if (int.TryParse(value, NumberStyles.Any, CultureInfo.InvariantCulture, out var result))
            return result;
        return 0;
    }

    private static int? ParseIntNullable(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return null;
        if (int.TryParse(value, NumberStyles.Any, CultureInfo.InvariantCulture, out var result))
            return result;
        return null;
    }

    private static DateTime? ParseDateTime(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return null;

        var formats = new[]
        {
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd",
            "dd/MM/yyyy",
            "dd/MM/yyyy HH:mm:ss",
            "dd/MM/yyyy HH:mm",
            "MM/dd/yyyy",
            "yyyy/MM/dd"
        };

        if (DateTime.TryParseExact(value.Trim(), formats, CultureInfo.InvariantCulture,
                DateTimeStyles.None, out var parsed))
            return parsed;

        if (DateTime.TryParse(value.Trim(), CultureInfo.InvariantCulture, DateTimeStyles.None, out parsed))
            return parsed;

        return null;
    }
}
