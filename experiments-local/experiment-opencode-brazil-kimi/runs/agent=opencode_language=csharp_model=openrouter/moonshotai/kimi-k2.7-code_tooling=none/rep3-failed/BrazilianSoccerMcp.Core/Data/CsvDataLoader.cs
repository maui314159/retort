// <copyright file="CsvDataLoader.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Loads and unifies all CSV datasets.
//
// Supported datasets:
//   - Brasileirao_Matches.csv (Serie A)
//   - Brazilian_Cup_Matches.csv (Copa do Brasil)
//   - Libertadores_Matches.csv (Copa Libertadores)
//   - BR-Football-Dataset.csv (extended stats, multiple competitions)
//   - novo_campeonato_brasileiro.csv (historical 2003-2019)
//   - fifa_data.csv (FIFA player database)
// </copyright>
using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Normalization;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Core.Data;

/// <summary>
/// Loads and normalizes match and player data from the provided CSV files.
/// </summary>
public sealed class CsvDataLoader
{
    private readonly string _dataDirectory;

    public CsvDataLoader(string dataDirectory)
    {
        _dataDirectory = dataDirectory ?? throw new ArgumentNullException(nameof(dataDirectory));
    }

    /// <summary>
    /// Loads all match CSVs and returns a unified, normalized collection.
    /// </summary>
    public IReadOnlyList<SoccerMatch> LoadMatches()
    {
        var matches = new List<SoccerMatch>();
        matches.AddRange(LoadBrasileirao());
        matches.AddRange(LoadCopaDoBrasil());
        matches.AddRange(LoadLibertadores());
        matches.AddRange(LoadExtendedStats());
        matches.AddRange(LoadHistoricalBrasileirao());
        return matches;
    }

    /// <summary>
    /// Loads the FIFA player CSV.
    /// </summary>
    public IReadOnlyList<Player> LoadPlayers()
    {
        var filePath = Path.Combine(_dataDirectory, "fifa_data.csv");
        if (!File.Exists(filePath))
            return Array.Empty<Player>();

        var players = new List<Player>();
        using var reader = new StreamReader(filePath, Encoding.UTF8);
        using var csv = new CsvReader(reader, CreateConfig());
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            players.Add(new Player
            {
                Id = GetLong(csv, "ID") ?? 0,
                Name = GetString(csv, "Name"),
                Age = GetInt(csv, "Age"),
                Nationality = GetString(csv, "Nationality"),
                Overall = GetInt(csv, "Overall"),
                Potential = GetInt(csv, "Potential"),
                Club = TeamNameNormalizer.Normalize(GetString(csv, "Club")),
                Position = GetString(csv, "Position"),
                JerseyNumber = GetString(csv, "Jersey Number"),
                PreferredFoot = GetString(csv, "Preferred Foot")
            });
        }

        return players;
    }

    private CsvConfiguration CreateConfig()
    {
        return new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            Encoding = Encoding.UTF8,
            BadDataFound = null,
            MissingFieldFound = null,
            HeaderValidated = null
        };
    }

    private IEnumerable<SoccerMatch> LoadBrasileirao()
    {
        var filePath = Path.Combine(_dataDirectory, "Brasileirao_Matches.csv");
        if (!File.Exists(filePath))
            yield break;

        using var reader = new StreamReader(filePath, Encoding.UTF8);
        using var csv = new CsvReader(reader, CreateConfig());
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            var date = DateParser.Parse(GetString(csv, "datetime"));
            var home = GetString(csv, "home_team");
            var away = GetString(csv, "away_team");

            yield return new SoccerMatch
            {
                Date = date,
                HomeTeam = TeamNameNormalizer.Normalize(home),
                AwayTeam = TeamNameNormalizer.Normalize(away),
                HomeGoals = GetInt(csv, "home_goal"),
                AwayGoals = GetInt(csv, "away_goal"),
                Competition = CompetitionCatalog.Brasileirao,
                Season = GetInt(csv, "season"),
                Round = GetString(csv, "round"),
                SourceFile = "Brasileirao_Matches.csv"
            };
        }
    }

    private IEnumerable<SoccerMatch> LoadCopaDoBrasil()
    {
        var filePath = Path.Combine(_dataDirectory, "Brazilian_Cup_Matches.csv");
        if (!File.Exists(filePath))
            yield break;

        using var reader = new StreamReader(filePath, Encoding.UTF8);
        using var csv = new CsvReader(reader, CreateConfig());
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            var date = DateParser.Parse(GetString(csv, "datetime"));

            yield return new SoccerMatch
            {
                Date = date,
                HomeTeam = TeamNameNormalizer.Normalize(GetString(csv, "home_team")),
                AwayTeam = TeamNameNormalizer.Normalize(GetString(csv, "away_team")),
                HomeGoals = GetInt(csv, "home_goal"),
                AwayGoals = GetInt(csv, "away_goal"),
                Competition = CompetitionCatalog.CopaDoBrasil,
                Season = GetInt(csv, "season"),
                Round = GetString(csv, "round"),
                SourceFile = "Brazilian_Cup_Matches.csv"
            };
        }
    }

    private IEnumerable<SoccerMatch> LoadLibertadores()
    {
        var filePath = Path.Combine(_dataDirectory, "Libertadores_Matches.csv");
        if (!File.Exists(filePath))
            yield break;

        using var reader = new StreamReader(filePath, Encoding.UTF8);
        using var csv = new CsvReader(reader, CreateConfig());
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            var date = DateParser.Parse(GetString(csv, "datetime"));

            yield return new SoccerMatch
            {
                Date = date,
                HomeTeam = TeamNameNormalizer.Normalize(GetString(csv, "home_team")),
                AwayTeam = TeamNameNormalizer.Normalize(GetString(csv, "away_team")),
                HomeGoals = GetInt(csv, "home_goal"),
                AwayGoals = GetInt(csv, "away_goal"),
                Competition = CompetitionCatalog.CopaLibertadores,
                Season = GetInt(csv, "season"),
                Round = GetString(csv, "stage"),
                SourceFile = "Libertadores_Matches.csv"
            };
        }
    }

    private IEnumerable<SoccerMatch> LoadExtendedStats()
    {
        var filePath = Path.Combine(_dataDirectory, "BR-Football-Dataset.csv");
        if (!File.Exists(filePath))
            yield break;

        using var reader = new StreamReader(filePath, Encoding.UTF8);
        using var csv = new CsvReader(reader, CreateConfig());
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            var date = DateParser.Parse(GetString(csv, "date"), GetString(csv, "time"));
            var tournament = GetString(csv, "tournament");

            yield return new SoccerMatch
            {
                Date = date,
                HomeTeam = TeamNameNormalizer.Normalize(GetString(csv, "home")),
                AwayTeam = TeamNameNormalizer.Normalize(GetString(csv, "away")),
                HomeGoals = GetInt(csv, "home_goal"),
                AwayGoals = GetInt(csv, "away_goal"),
                Competition = CompetitionCatalog.Normalize(tournament),
                Season = DateParser.ParseSeason(null, date),
                Round = null,
                SourceFile = "BR-Football-Dataset.csv"
            };
        }
    }

    private IEnumerable<SoccerMatch> LoadHistoricalBrasileirao()
    {
        var filePath = Path.Combine(_dataDirectory, "novo_campeonato_brasileiro.csv");
        if (!File.Exists(filePath))
            yield break;

        var config = CreateConfig();
        // The historical file uses semi-colon? Let's inspect dynamically.
        config.Delimiter = DetectDelimiter(filePath) ?? ",";

        using var reader = new StreamReader(filePath, Encoding.UTF8);
        using var csv = new CsvReader(reader, config);
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            var date = DateParser.Parse(GetString(csv, "Data"));

            yield return new SoccerMatch
            {
                Date = date,
                HomeTeam = TeamNameNormalizer.Normalize(GetString(csv, "Equipe_mandante")),
                AwayTeam = TeamNameNormalizer.Normalize(GetString(csv, "Equipe_visitante")),
                HomeGoals = GetInt(csv, "Gols_mandante"),
                AwayGoals = GetInt(csv, "Gols_visitante"),
                Competition = CompetitionCatalog.Brasileirao,
                Season = GetInt(csv, "Ano") ?? DateParser.ParseSeason(null, date),
                Round = GetString(csv, "Rodada"),
                SourceFile = "novo_campeonato_brasileiro.csv"
            };
        }
    }

    private static string? DetectDelimiter(string filePath)
    {
        using var reader = new StreamReader(filePath, Encoding.UTF8);
        var firstLine = reader.ReadLine();
        if (string.IsNullOrEmpty(firstLine))
            return null;

        // Count semicolons vs commas outside of quotes.
        var semicolons = CountUnquoted(firstLine, ';');
        var commas = CountUnquoted(firstLine, ',');

        return semicolons > commas ? ";" : ",";
    }

    private static int CountUnquoted(string line, char delimiter)
    {
        var count = 0;
        var inQuotes = false;
        foreach (var c in line)
        {
            if (c == '"')
                inQuotes = !inQuotes;
            else if (!inQuotes && c == delimiter)
                count++;
        }

        return count;
    }

    private static int? GetInt(CsvReader csv, string name)
    {
        var raw = GetString(csv, name);
        if (string.IsNullOrWhiteSpace(raw))
            return null;

        // Strip trailing ".0" coming from BR-Football-Dataset.
        if (raw.EndsWith(".0", StringComparison.OrdinalIgnoreCase))
            raw = raw[..^2];

        if (int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var value))
            return value;

        if (double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
            return (int)d;

        return null;
    }

    private static long? GetLong(CsvReader csv, string name)
    {
        var raw = GetString(csv, name);
        if (long.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var value))
            return value;
        return null;
    }

    private static string GetString(CsvReader csv, string name)
    {
        if (csv.HeaderRecord?.Contains(name, StringComparer.OrdinalIgnoreCase) != true)
            return string.Empty;

        return csv.GetField(name)?.Trim() ?? string.Empty;
    }
}
