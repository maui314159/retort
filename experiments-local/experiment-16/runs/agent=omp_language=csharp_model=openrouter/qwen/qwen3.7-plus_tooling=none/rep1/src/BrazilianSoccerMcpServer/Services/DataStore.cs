using System.Globalization;
using BrazilianSoccerMcpServer.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcpServer.Services;

public class BrazilianSoccerDataStore
{
    public List<Match> Matches { get; } = new();
    public List<Player> Players { get; } = new();

    public void LoadFromDirectory(string dataDirectory)
    {
        LoadBrasileirao(Path.Combine(dataDirectory, "Brasileirao_Matches.csv"));
        LoadBrazilianCup(Path.Combine(dataDirectory, "Brazilian_Cup_Matches.csv"));
        LoadLibertadores(Path.Combine(dataDirectory, "Libertadores_Matches.csv"));
        LoadBrFootballDataset(Path.Combine(dataDirectory, "BR-Football-Dataset.csv"));
        LoadNovoCampeonato(Path.Combine(dataDirectory, "novo_campeonato_brasileiro.csv"));
        LoadFifaData(Path.Combine(dataDirectory, "fifa_data.csv"));
    }

    private static List<T> LoadCsv<T>(string path, CsvConfiguration config) where T : class
    {
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, config);
        return csv.GetRecords<T>().ToList();
    }

    private void LoadBrasileirao(string path)
    {
        if (!File.Exists(path)) return;
        var config = new CsvConfiguration(CultureInfo.InvariantCulture) { HeaderValidated = null, MissingFieldFound = null, Delimiter = "," };
        var records = LoadCsv<BrasileiraoMatchCsv>(path, config);
        
        foreach (var r in records)
        {
            if (DateTime.TryParse(r.datetime, out var date))
            {
                Matches.Add(new Match(
                    Competition: "Brasileirão",
                    Date: date,
                    Season: ParseInt(r.season),
                    Round: r.round,
                    HomeTeam: TeamNameNormalizer.Normalize(r.home_team),
                    AwayTeam: TeamNameNormalizer.Normalize(r.away_team),
                    HomeGoal: ParseInt(r.home_goal),
                    AwayGoal: ParseInt(r.away_goal),
                    HomeTeamState: r.home_team_state,
                    AwayTeamState: r.away_team_state,
                    Stage: null
                ));
            }
        }
    }

    private void LoadBrazilianCup(string path)
    {
        if (!File.Exists(path)) return;
        var config = new CsvConfiguration(CultureInfo.InvariantCulture) { HeaderValidated = null, MissingFieldFound = null, Delimiter = "," };
        var records = LoadCsv<BrazilianCupMatchCsv>(path, config);
        
        foreach (var r in records)
        {
            if (DateTime.TryParse(r.datetime, out var date))
            {
                Matches.Add(new Match(
                    Competition: "Copa do Brasil",
                    Date: date,
                    Season: ParseInt(r.season),
                    Round: r.round,
                    HomeTeam: TeamNameNormalizer.Normalize(r.home_team),
                    AwayTeam: TeamNameNormalizer.Normalize(r.away_team),
                    HomeGoal: ParseInt(r.home_goal),
                    AwayGoal: ParseInt(r.away_goal)
                ));
            }
        }
    }

    private void LoadLibertadores(string path)
    {
        if (!File.Exists(path)) return;
        var config = new CsvConfiguration(CultureInfo.InvariantCulture) { HeaderValidated = null, MissingFieldFound = null, Delimiter = "," };
        var records = LoadCsv<LibertadoresMatchCsv>(path, config);
        
        foreach (var r in records)
        {
            if (DateTime.TryParse(r.datetime, out var date))
            {
                Matches.Add(new Match(
                    Competition: "Libertadores",
                    Date: date,
                    Season: ParseInt(r.season),
                    Round: r.stage,
                    HomeTeam: TeamNameNormalizer.Normalize(r.home_team),
                    AwayTeam: TeamNameNormalizer.Normalize(r.away_team),
                    HomeGoal: ParseInt(r.home_goal),
                    AwayGoal: ParseInt(r.away_goal),
                    Stage: r.stage
                ));
            }
        }
    }

    private void LoadBrFootballDataset(string path)
    {
        if (!File.Exists(path)) return;
        var config = new CsvConfiguration(CultureInfo.InvariantCulture) { HeaderValidated = null, MissingFieldFound = null, Delimiter = "," };
        var records = LoadCsv<BrFootballDatasetCsv>(path, config);
        
        foreach (var r in records)
        {
            if (DateTime.TryParse(r.date, out var date))
            {
                Matches.Add(new Match(
                    Competition: r.tournament,
                    Date: date,
                    Season: date.Year,
                    Round: "",
                    HomeTeam: TeamNameNormalizer.Normalize(r.home),
                    AwayTeam: TeamNameNormalizer.Normalize(r.away),
                    HomeGoal: ParseInt(r.home_goal),
                    AwayGoal: ParseInt(r.away_goal),
                    HomeCorner: ParseIntNullable(r.home_corner),
                    AwayCorner: ParseIntNullable(r.away_corner),
                    HomeAttack: ParseIntNullable(r.home_attack),
                    AwayAttack: ParseIntNullable(r.away_attack),
                    HomeShot: ParseIntNullable(r.home_shots),
                    AwayShot: ParseIntNullable(r.away_shots),
                    HalfTimeResult: r.ht_result,
                    TotalCorners: ParseIntNullable(r.total_corners)
                ));
            }
        }
    }

    private void LoadNovoCampeonato(string path)
    {
        if (!File.Exists(path)) return;
        var ptBr = new CultureInfo("pt-BR");
        var config = new CsvConfiguration(ptBr) 
        { 
            HeaderValidated = null, 
            MissingFieldFound = null,
            Delimiter = ","
        };
        var records = LoadCsv<NovoCampeonatoBrasileiroCsv>(path, config);
        
        foreach (var r in records)
        {
            if (DateTime.TryParse(r.Data, ptBr, DateTimeStyles.None, out var date))
            {
                Matches.Add(new Match(
                    Competition: "Brasileirão",
                    Date: date,
                    Season: ParseInt(r.Ano),
                    Round: r.Rodada,
                    HomeTeam: TeamNameNormalizer.Normalize(r.Equipe_mandante),
                    AwayTeam: TeamNameNormalizer.Normalize(r.Equipe_visitante),
                    HomeGoal: ParseInt(r.Gols_mandante),
                    AwayGoal: ParseInt(r.Gols_visitante),
                    HomeTeamState: r.Mandante_UF,
                    AwayTeamState: r.Visitante_UF,
                    Arena: r.Arena
                ));
            }
        }
    }

    private void LoadFifaData(string path)
    {
        if (!File.Exists(path)) return;
        var config = new CsvConfiguration(CultureInfo.InvariantCulture) { HeaderValidated = null, MissingFieldFound = null, Delimiter = "," };
        
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, config);
        
        // Skip the first weird column by using a custom map or just reading dynamically
        // Actually, let's just use dynamic or read by index
        
        csv.Read();
        csv.ReadHeader();
        
        while (csv.Read())
        {
            // The first column is empty or BOM, so index 1 is ID, 2 is Name, etc.
            // Let's try to get by name, ignoring the first empty column
            var idStr = csv.GetField("ID");
            if (!int.TryParse(idStr, out var id)) continue;
            
            var name = csv.GetField("Name") ?? "";
            var ageStr = csv.GetField("Age");
            var nationality = csv.GetField("Nationality") ?? "";
            var overallStr = csv.GetField("Overall");
            var potentialStr = csv.GetField("Potential");
            var club = csv.GetField("Club") ?? "";
            var position = csv.GetField("Position") ?? "";
            var jerseyStr = csv.GetField("Jersey Number");
            var height = csv.GetField("Height");
            var weight = csv.GetField("Weight");

            Players.Add(new Player(
                Id: id,
                Name: name,
                Age: int.TryParse(ageStr, out var age) ? age : 0,
                Nationality: nationality,
                Overall: int.TryParse(overallStr, out var overall) ? overall : 0,
                Potential: int.TryParse(potentialStr, out var potential) ? potential : 0,
                Club: TeamNameNormalizer.Normalize(club),
                Position: position,
                JerseyNumber: int.TryParse(jerseyStr, out var jersey) ? jersey : null,
                Height: height,
                Weight: weight
            ));
        }
    }

    private static int ParseInt(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return 0;
        if (int.TryParse(value, out var result)) return result;
        if (double.TryParse(value, out var d)) return (int)d;
        return 0;
    }

    private static int? ParseIntNullable(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        if (int.TryParse(value, out var result)) return result;
        if (double.TryParse(value, out var d)) return (int)d;
        return null;
    }
}
