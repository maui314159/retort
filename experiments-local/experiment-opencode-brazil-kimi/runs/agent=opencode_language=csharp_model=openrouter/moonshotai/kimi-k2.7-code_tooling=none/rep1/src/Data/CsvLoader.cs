/*
 * Brazilian Soccer MCP Server - CSV Data Loader
 *
 * Loads and normalizes the six heterogeneous Kaggle CSV files into the
 * unified domain models used by the query engine.
 */
using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Data;

public sealed class CsvLoader
{
    private static readonly string[] DateFormats =
    [
        "yyyy-MM-dd HH:mm:ss",
        "yyyy-MM-dd",
        "dd/MM/yyyy",
        "MM/dd/yyyy HH:mm:ss",
        "MM/dd/yyyy"
    ];

    public IReadOnlyList<MatchRecord> LoadMatches(string dataDirectory)
    {
        var matches = new List<MatchRecord>();
        matches.AddRange(LoadBrasileirao(Path.Combine(dataDirectory, "Brasileirao_Matches.csv")));
        matches.AddRange(LoadBrazilianCup(Path.Combine(dataDirectory, "Brazilian_Cup_Matches.csv")));
        matches.AddRange(LoadLibertadores(Path.Combine(dataDirectory, "Libertadores_Matches.csv")));
        matches.AddRange(LoadBrFootball(Path.Combine(dataDirectory, "BR-Football-Dataset.csv")));
        matches.AddRange(LoadNovoCampeonato(Path.Combine(dataDirectory, "novo_campeonato_brasileiro.csv")));
        return matches;
    }

    public IReadOnlyList<PlayerRecord> LoadPlayers(string dataDirectory)
    {
        var players = new List<PlayerRecord>();
        using var reader = new StreamReader(Path.Combine(dataDirectory, "fifa_data.csv"), Encoding.UTF8);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            MissingFieldFound = null,
            BadDataFound = null
        });
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            players.Add(new PlayerRecord
            {
                Id = ParseInt(csv.GetField("ID")),
                Name = csv.GetField("Name") ?? string.Empty,
                Age = ParseInt(csv.GetField("Age")),
                Nationality = csv.GetField("Nationality"),
                Overall = ParseInt(csv.GetField("Overall")),
                Potential = ParseInt(csv.GetField("Potential")),
                Club = csv.GetField("Club"),
                Position = csv.GetField("Position"),
                JerseyNumber = csv.GetField("Jersey Number"),
                Height = csv.GetField("Height"),
                Weight = csv.GetField("Weight")
            });
        }
        return players;
    }

    private IEnumerable<MatchRecord> LoadBrasileirao(string path)
    {
        foreach (var row in ReadRows(path))
        {
            yield return new MatchRecord
            {
                Date = ParseDate(row.GetValueOrDefault("datetime")),
                HomeTeam = row.GetValueOrDefault("home_team") ?? string.Empty,
                AwayTeam = row.GetValueOrDefault("away_team") ?? string.Empty,
                HomeGoals = ParseInt(row.GetValueOrDefault("home_goal")),
                AwayGoals = ParseInt(row.GetValueOrDefault("away_goal")),
                Competition = "Brasileirão",
                Season = ParseInt(row.GetValueOrDefault("season")),
                Round = row.GetValueOrDefault("round")
            };
        }
    }

    private IEnumerable<MatchRecord> LoadBrazilianCup(string path)
    {
        foreach (var row in ReadRows(path))
        {
            yield return new MatchRecord
            {
                Date = ParseDate(row.GetValueOrDefault("datetime")),
                HomeTeam = row.GetValueOrDefault("home_team") ?? string.Empty,
                AwayTeam = row.GetValueOrDefault("away_team") ?? string.Empty,
                HomeGoals = ParseInt(row.GetValueOrDefault("home_goal")),
                AwayGoals = ParseInt(row.GetValueOrDefault("away_goal")),
                Competition = "Copa do Brasil",
                Season = ParseInt(row.GetValueOrDefault("season")),
                Round = row.GetValueOrDefault("round")
            };
        }
    }

    private IEnumerable<MatchRecord> LoadLibertadores(string path)
    {
        foreach (var row in ReadRows(path))
        {
            yield return new MatchRecord
            {
                Date = ParseDate(row.GetValueOrDefault("datetime")),
                HomeTeam = row.GetValueOrDefault("home_team") ?? string.Empty,
                AwayTeam = row.GetValueOrDefault("away_team") ?? string.Empty,
                HomeGoals = ParseInt(row.GetValueOrDefault("home_goal")),
                AwayGoals = ParseInt(row.GetValueOrDefault("away_goal")),
                Competition = "Copa Libertadores",
                Season = ParseInt(row.GetValueOrDefault("season")),
                Stage = row.GetValueOrDefault("stage")
            };
        }
    }

    private IEnumerable<MatchRecord> LoadBrFootball(string path)
    {
        foreach (var row in ReadRows(path))
        {
            var date = ParseDate(row.GetValueOrDefault("date"));
            var time = row.GetValueOrDefault("time");
            if (date.HasValue && !string.IsNullOrWhiteSpace(time))
            {
                if (TimeSpan.TryParse(time, out var ts))
                    date = date.Value.Date + ts;
            }

            var tournament = row.GetValueOrDefault("tournament") ?? "Unknown";
            var competition = tournament.ToLowerInvariant() switch
            {
                var t when t.Contains("brasileir") => "Brasileirão",
                var t when t.Contains("copa do brasil") => "Copa do Brasil",
                var t when t.Contains("libertadores") => "Copa Libertadores",
                _ => tournament
            };

            yield return new MatchRecord
            {
                Date = date,
                HomeTeam = row.GetValueOrDefault("home") ?? string.Empty,
                AwayTeam = row.GetValueOrDefault("away") ?? string.Empty,
                HomeGoals = ParseInt(row.GetValueOrDefault("home_goal")),
                AwayGoals = ParseInt(row.GetValueOrDefault("away_goal")),
                Competition = competition,
                Season = date?.Year
            };
        }
    }

    private IEnumerable<MatchRecord> LoadNovoCampeonato(string path)
    {
        foreach (var row in ReadRows(path))
        {
            yield return new MatchRecord
            {
                Date = ParseDate(row.GetValueOrDefault("Data")),
                HomeTeam = row.GetValueOrDefault("Equipe_mandante") ?? string.Empty,
                AwayTeam = row.GetValueOrDefault("Equipe_visitante") ?? string.Empty,
                HomeGoals = ParseInt(row.GetValueOrDefault("Gols_mandante")),
                AwayGoals = ParseInt(row.GetValueOrDefault("Gols_visitante")),
                Competition = "Brasileirão",
                Season = ParseInt(row.GetValueOrDefault("Ano")),
                Round = row.GetValueOrDefault("Rodada"),
                Stadium = row.GetValueOrDefault("Arena")
            };
        }
    }

    private static IEnumerable<Dictionary<string, string>> ReadRows(string path)
    {
        if (!File.Exists(path))
            yield break;

        using var reader = new StreamReader(path, Encoding.UTF8);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            MissingFieldFound = null,
            BadDataFound = null
        });
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            var row = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var header in csv.HeaderRecord ?? [])
            {
                row[header] = csv.GetField(header) ?? string.Empty;
            }
            yield return row;
        }
    }

    private static int? ParseInt(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        value = value.Trim();
        if (int.TryParse(value, NumberStyles.Any, CultureInfo.InvariantCulture, out var result))
            return result;
        return null;
    }

    private static DateTime? ParseDate(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        value = value.Trim();
        foreach (var format in DateFormats)
        {
            if (DateTime.TryParseExact(value, format, CultureInfo.InvariantCulture, DateTimeStyles.None, out var result))
                return result;
        }
        if (DateTime.TryParse(value, CultureInfo.InvariantCulture, DateTimeStyles.None, out var fallback))
            return fallback;
        return null;
    }
}

internal static class DictionaryExtensions
{
    public static string? GetValueOrDefault(this Dictionary<string, string> dict, string key)
    {
        dict.TryGetValue(key, out var value);
        return value;
    }
}
