using System.Globalization;
using BrazilianSoccerMcp.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Data;

public class DataLoader
{
    private readonly string _dataDirectory;

    public DataLoader(string dataDirectory)
    {
        _dataDirectory = dataDirectory;
    }

    public List<MatchRecord> LoadAllMatches()
    {
        var matches = new List<MatchRecord>();

        matches.AddRange(LoadBrasileiraoMatches());
        matches.AddRange(LoadBrazilianCupMatches());
        matches.AddRange(LoadLibertadoresMatches());
        matches.AddRange(LoadBRFootballDataset());
        matches.AddRange(LoadNovoCampeonato());

        return matches;
    }

    public List<PlayerRecord> LoadPlayers()
    {
        var players = new List<PlayerRecord>();
        var filePath = Path.Combine(_dataDirectory, "fifa_data.csv");
        if (!File.Exists(filePath)) return players;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null
        };

        using var reader = new StreamReader(filePath);
        using var csv = new CsvReader(reader, config);

        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            try
            {
                players.Add(new PlayerRecord
                {
                    Id = csv.GetField<int>("ID"),
                    Name = csv.GetField<string>("Name") ?? "",
                    Age = csv.GetField<int>("Age"),
                    Nationality = csv.GetField<string>("Nationality") ?? "",
                    Overall = csv.GetField<int>("Overall"),
                    Potential = csv.GetField<int>("Potential"),
                    Club = csv.GetField<string>("Club") ?? "",
                    Position = csv.GetField<string>("Position") ?? "",
                    JerseyNumber = csv.GetField<string>("Jersey Number"),
                    Height = csv.GetField<string>("Height"),
                    Weight = csv.GetField<string>("Weight"),
                    Value = csv.GetField<string>("Value"),
                    Wage = csv.GetField<string>("Wage"),
                    Finishing = GetIntSafe(csv, "Finishing"),
                    Dribbling = GetIntSafe(csv, "Dribbling"),
                    ShortPassing = GetIntSafe(csv, "ShortPassing"),
                    Stamina = GetIntSafe(csv, "Stamina")
                });
            }
            catch
            {
                // Skip bad rows
            }
        }

        return players;
    }

    private List<MatchRecord> LoadBrasileiraoMatches()
    {
        var matches = new List<MatchRecord>();
        var filePath = Path.Combine(_dataDirectory, "Brasileirao_Matches.csv");
        if (!File.Exists(filePath)) return matches;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null
        };

        using var reader = new StreamReader(filePath);
        using var csv = new CsvReader(reader, config);

        while (csv.Read())
        {
            try
            {
                var dateStr = csv.GetField<string>("datetime");
                DateTime? date = null;
                if (!string.IsNullOrEmpty(dateStr))
                {
                    DateTime.TryParse(dateStr, out var parsed);
                    date = parsed;
                }

                matches.Add(new MatchRecord
                {
                    Source = "Brasileirao",
                    Competition = "Brasileirão Série A",
                    Date = date,
                    Season = csv.GetField<string>("season") ?? "",
                    Round = csv.GetField<string>("round") ?? "",
                    HomeTeam = TeamNormalizer.Normalize(csv.GetField<string>("home_team") ?? ""),
                    AwayTeam = TeamNormalizer.Normalize(csv.GetField<string>("away_team") ?? ""),
                    HomeGoals = GetIntSafe(csv, "home_goal"),
                    AwayGoals = GetIntSafe(csv, "away_goal"),
                    HomeTeamState = csv.GetField<string>("home_team_state"),
                    AwayTeamState = csv.GetField<string>("away_team_state")
                });
            }
            catch { }
        }
        return matches;
    }

    private List<MatchRecord> LoadBrazilianCupMatches()
    {
        var matches = new List<MatchRecord>();
        var filePath = Path.Combine(_dataDirectory, "Brazilian_Cup_Matches.csv");
        if (!File.Exists(filePath)) return matches;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null
        };

        using var reader = new StreamReader(filePath);
        using var csv = new CsvReader(reader, config);

        while (csv.Read())
        {
            try
            {
                var dateStr = csv.GetField<string>("datetime");
                DateTime? date = null;
                if (!string.IsNullOrEmpty(dateStr))
                {
                    DateTime.TryParse(dateStr, out var parsed);
                    date = parsed;
                }

                matches.Add(new MatchRecord
                {
                    Source = "BrazilianCup",
                    Competition = "Copa do Brasil",
                    Date = date,
                    Season = csv.GetField<string>("season") ?? "",
                    Round = csv.GetField<string>("round") ?? "",
                    HomeTeam = TeamNormalizer.Normalize(csv.GetField<string>("home_team") ?? ""),
                    AwayTeam = TeamNormalizer.Normalize(csv.GetField<string>("away_team") ?? ""),
                    HomeGoals = GetIntSafe(csv, "home_goal"),
                    AwayGoals = GetIntSafe(csv, "away_goal")
                });
            }
            catch { }
        }
        return matches;
    }

    private List<MatchRecord> LoadLibertadoresMatches()
    {
        var matches = new List<MatchRecord>();
        var filePath = Path.Combine(_dataDirectory, "Libertadores_Matches.csv");
        if (!File.Exists(filePath)) return matches;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null
        };

        using var reader = new StreamReader(filePath);
        using var csv = new CsvReader(reader, config);

        while (csv.Read())
        {
            try
            {
                var dateStr = csv.GetField<string>("datetime");
                DateTime? date = null;
                if (!string.IsNullOrEmpty(dateStr))
                {
                    DateTime.TryParse(dateStr, out var parsed);
                    date = parsed;
                }

                matches.Add(new MatchRecord
                {
                    Source = "Libertadores",
                    Competition = "Copa Libertadores",
                    Date = date,
                    Season = csv.GetField<string>("season") ?? "",
                    Stage = csv.GetField<string>("stage") ?? "",
                    HomeTeam = TeamNormalizer.Normalize(csv.GetField<string>("home_team") ?? ""),
                    AwayTeam = TeamNormalizer.Normalize(csv.GetField<string>("away_team") ?? ""),
                    HomeGoals = GetIntSafe(csv, "home_goal"),
                    AwayGoals = GetIntSafe(csv, "away_goal")
                });
            }
            catch { }
        }
        return matches;
    }

    private List<MatchRecord> LoadBRFootballDataset()
    {
        var matches = new List<MatchRecord>();
        var filePath = Path.Combine(_dataDirectory, "BR-Football-Dataset.csv");
        if (!File.Exists(filePath)) return matches;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null
        };

        using var reader = new StreamReader(filePath);
        using var csv = new CsvReader(reader, config);

        while (csv.Read())
        {
            try
            {
                var dateStr = csv.GetField<string>("date");
                DateTime? date = null;
                if (!string.IsNullOrEmpty(dateStr))
                {
                    DateTime.TryParse(dateStr, out var parsed);
                    date = parsed;
                }

                matches.Add(new MatchRecord
                {
                    Source = "BRFootball",
                    Competition = csv.GetField<string>("tournament") ?? "Unknown",
                    Date = date,
                    HomeTeam = TeamNormalizer.Normalize(csv.GetField<string>("home") ?? ""),
                    AwayTeam = TeamNormalizer.Normalize(csv.GetField<string>("away") ?? ""),
                    HomeGoals = GetIntSafe(csv, "home_goal"),
                    AwayGoals = GetIntSafe(csv, "away_goal"),
                    HomeCorners = GetIntSafe(csv, "home_corner"),
                    AwayCorners = GetIntSafe(csv, "away_corner"),
                    HomeShots = GetIntSafe(csv, "home_shots"),
                    AwayShots = GetIntSafe(csv, "away_shots")
                });
            }
            catch { }
        }
        return matches;
    }

    private List<MatchRecord> LoadNovoCampeonato()
    {
        var matches = new List<MatchRecord>();
        var filePath = Path.Combine(_dataDirectory, "novo_campeonato_brasileiro.csv");
        if (!File.Exists(filePath)) return matches;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null
        };

        using var reader = new StreamReader(filePath);
        using var csv = new CsvReader(reader, config);

        while (csv.Read())
        {
            try
            {
                var dateStr = csv.GetField<string>("Data");
                DateTime? date = null;
                if (!string.IsNullOrEmpty(dateStr))
                {
                    // Format is DD/MM/YYYY
                    if (DateTime.TryParseExact(dateStr, "dd/MM/yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out var parsed))
                    {
                        date = parsed;
                    }
                }

                matches.Add(new MatchRecord
                {
                    Source = "NovoCampeonato",
                    Competition = "Brasileirão Série A",
                    Date = date,
                    Season = csv.GetField<string>("Ano") ?? "",
                    Round = csv.GetField<string>("Rodada") ?? "",
                    HomeTeam = TeamNormalizer.Normalize(csv.GetField<string>("Equipe_mandante") ?? ""),
                    AwayTeam = TeamNormalizer.Normalize(csv.GetField<string>("Equipe_visitante") ?? ""),
                    HomeGoals = GetIntSafe(csv, "Gols_mandante"),
                    AwayGoals = GetIntSafe(csv, "Gols_visitante"),
                    HomeTeamState = csv.GetField<string>("Mandante_UF"),
                    AwayTeamState = csv.GetField<string>("Visitante_UF")
                });
            }
            catch { }
        }
        return matches;
    }

    private static int GetIntSafe(CsvReader csv, string columnName)
    {
        try
        {
            var val = csv.GetField<string>(columnName);
            if (double.TryParse(val, out var d)) return (int)d;
        }
        catch { }
        return 0;
    }
}
