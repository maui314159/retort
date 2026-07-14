using System.Globalization;
using BrazilianSoccerMCP.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMCP.Services;

/// <summary>
/// Loads all 6 CSV datasets into unified in-memory collections.
/// Handles column name mapping, date format normalization, and team name normalization.
/// </summary>
public class DataLoader
{
    public List<Match> AllMatches { get; } = new();
    public List<Player> Players { get; } = new();

    private readonly string _dataDir;

    public DataLoader(string dataDir)
    {
        _dataDir = dataDir;
    }

    public void LoadAll()
    {
        LoadBrasileiraoMatches();
        LoadBrazilianCupMatches();
        LoadLibertadoresMatches();
        LoadBrFootballDataset();
        LoadNovoCampeonatoBrasileiro();
        LoadFifaPlayers();
    }

    private CsvConfiguration GetConfig() => new(CultureInfo.InvariantCulture)
    {
        HeaderValidated = null,
        MissingFieldFound = null,
        BadDataFound = null,
        TrimOptions = TrimOptions.Trim,
    };

    // 1. Brasileirao_Matches.csv
    private void LoadBrasileiraoMatches()
    {
        var path = Path.Combine(_dataDir, "kaggle", "Brasileirao_Matches.csv");
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, GetConfig());
        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var date = SafeParseDateTime(csv.GetField("datetime")!);
            if (date == DateTime.MinValue) continue;

            var match = new Match
            {
                Competition = "Brasileirão",
                Date = date,
                HomeTeam = TeamNameNormalizer.Normalize(csv.GetField("home_team")!),
                AwayTeam = TeamNameNormalizer.Normalize(csv.GetField("away_team")!),
                HomeGoal = SafeParseInt(csv.GetField("home_goal")!),
                AwayGoal = SafeParseInt(csv.GetField("away_goal")!),
                Season = SafeParseInt(csv.GetField("season")!),
                Round = csv.GetField("round"),
                HomeTeamState = csv.GetField("home_team_state"),
                AwayTeamState = csv.GetField("away_team_state"),
            };
            AllMatches.Add(match);
        }
    }

    // 2. Brazilian_Cup_Matches.csv
    private void LoadBrazilianCupMatches()
    {
        var path = Path.Combine(_dataDir, "kaggle", "Brazilian_Cup_Matches.csv");
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, GetConfig());
        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var date = SafeParseDateTime(csv.GetField("datetime")!);
            if (date == DateTime.MinValue) continue;

            var match = new Match
            {
                Competition = "Copa do Brasil",
                Date = date,
                HomeTeam = TeamNameNormalizer.Normalize(csv.GetField("home_team")!),
                AwayTeam = TeamNameNormalizer.Normalize(csv.GetField("away_team")!),
                HomeGoal = SafeParseInt(csv.GetField("home_goal")!),
                AwayGoal = SafeParseInt(csv.GetField("away_goal")!),
                Season = SafeParseInt(csv.GetField("season")!),
                Round = csv.GetField("round"),
            };
            AllMatches.Add(match);
        }
    }

    // 3. Libertadores_Matches.csv
    private void LoadLibertadoresMatches()
    {
        var path = Path.Combine(_dataDir, "kaggle", "Libertadores_Matches.csv");
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, GetConfig());
        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var date = SafeParseDateTime(csv.GetField("datetime")!);
            if (date == DateTime.MinValue) continue;

            var homeGoalStr = csv.GetField("home_goal")!;
            var awayGoalStr = csv.GetField("away_goal")!;

            var match = new Match
            {
                Competition = "Copa Libertadores",
                Date = date,
                HomeTeam = TeamNameNormalizer.Normalize(csv.GetField("home_team")!),
                AwayTeam = TeamNameNormalizer.Normalize(csv.GetField("away_team")!),
                HomeGoal = SafeParseInt(homeGoalStr),
                AwayGoal = SafeParseInt(awayGoalStr),
                Season = SafeParseInt(csv.GetField("season")!),
                Stage = csv.GetField("stage"),
            };
            AllMatches.Add(match);
        }
    }

    // 4. BR-Football-Dataset.csv
    private void LoadBrFootballDataset()
    {
        var path = Path.Combine(_dataDir, "kaggle", "BR-Football-Dataset.csv");
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, GetConfig());
        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var competition = MapTournament(csv.GetField("tournament")!);
            var dateStr = csv.GetField("date")!;
            if (!DateTime.TryParse(dateStr, out var date))
                continue;

            var season = date.Year;

            var match = new Match
            {
                Competition = competition,
                Date = date,
                HomeTeam = TeamNameNormalizer.Normalize(csv.GetField("home")!),
                AwayTeam = TeamNameNormalizer.Normalize(csv.GetField("away")!),
                HomeGoal = SafeParseInt(csv.GetField("home_goal")!),
                AwayGoal = SafeParseInt(csv.GetField("away_goal")!),
                Season = season,
                HomeCorner = SafeParseDouble(csv.GetField("home_corner")),
                AwayCorner = SafeParseDouble(csv.GetField("away_corner")),
                HomeAttack = SafeParseDouble(csv.GetField("home_attack")),
                AwayAttack = SafeParseDouble(csv.GetField("away_attack")),
                HomeShots = SafeParseDouble(csv.GetField("home_shots")),
                AwayShots = SafeParseDouble(csv.GetField("away_shots")),
                HalfTimeResult = csv.GetField("ht_result"),
                TotalCorners = SafeParseDouble(csv.GetField("total_corners")),
            };
            AllMatches.Add(match);
        }
    }

    // 5. novo_campeonato_brasileiro.csv (2003-2019)
    private void LoadNovoCampeonatoBrasileiro()
    {
        var path = Path.Combine(_dataDir, "kaggle", "novo_campeonato_brasileiro.csv");
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, GetConfig());
        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var dateStr = csv.GetField("Data")!;
            if (!TryParseBrazilianDate(dateStr, out var date))
                continue;

            var match = new Match
            {
                Competition = "Brasileirão",
                Date = date,
                HomeTeam = TeamNameNormalizer.Normalize(csv.GetField("Equipe_mandante")!),
                AwayTeam = TeamNameNormalizer.Normalize(csv.GetField("Equipe_visitante")!),
                HomeGoal = SafeParseInt(csv.GetField("Gols_mandante")!),
                AwayGoal = SafeParseInt(csv.GetField("Gols_visitante")!),
                Season = SafeParseInt(csv.GetField("Ano")!),
                Round = csv.GetField("Rodada"),
                HomeTeamState = csv.GetField("Mandante_UF"),
                AwayTeamState = csv.GetField("Visitante_UF"),
                Stadium = csv.GetField("Arena"),
            };
            AllMatches.Add(match);
        }
    }

    // 6. fifa_data.csv
    private void LoadFifaPlayers()
    {
        var path = Path.Combine(_dataDir, "kaggle", "fifa_data.csv");
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, GetConfig());
        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var player = new Player
            {
                ID = int.Parse(csv.GetField("ID")!),
                Name = csv.GetField("Name")!,
                Age = int.Parse(csv.GetField("Age")!),
                Nationality = csv.GetField("Nationality")!,
                Overall = int.Parse(csv.GetField("Overall")!),
                Potential = int.Parse(csv.GetField("Potential")!),
                Club = csv.GetField("Club") ?? "",
                Position = csv.GetField("Position") ?? "",
                PreferredFoot = csv.GetField("Preferred Foot") ?? "",
                Height = csv.GetField("Height") ?? "",
                Weight = csv.GetField("Weight") ?? "",
                WorkRate = csv.GetField("Work Rate") ?? "",
                JerseyNumber = SafeParseIntNullable(csv.GetField("Jersey Number")),
                Crossing = SafeParseInt(csv.GetField("Crossing")),
                Finishing = SafeParseInt(csv.GetField("Finishing")),
                HeadingAccuracy = SafeParseInt(csv.GetField("HeadingAccuracy")),
                ShortPassing = SafeParseInt(csv.GetField("ShortPassing")),
                Volleys = SafeParseInt(csv.GetField("Volleys")),
                Dribbling = SafeParseInt(csv.GetField("Dribbling")),
                Curve = SafeParseInt(csv.GetField("Curve")),
                FKAccuracy = SafeParseInt(csv.GetField("FKAccuracy")),
                LongPassing = SafeParseInt(csv.GetField("LongPassing")),
                BallControl = SafeParseInt(csv.GetField("BallControl")),
                Acceleration = SafeParseInt(csv.GetField("Acceleration")),
                SprintSpeed = SafeParseInt(csv.GetField("SprintSpeed")),
                Agility = SafeParseInt(csv.GetField("Agility")),
                Reactions = SafeParseInt(csv.GetField("Reactions")),
                Balance = SafeParseInt(csv.GetField("Balance")),
                ShotPower = SafeParseInt(csv.GetField("ShotPower")),
                Jumping = SafeParseInt(csv.GetField("Jumping")),
                Stamina = SafeParseInt(csv.GetField("Stamina")),
                Strength = SafeParseInt(csv.GetField("Strength")),
                LongShots = SafeParseInt(csv.GetField("LongShots")),
                Aggression = SafeParseInt(csv.GetField("Aggression")),
                Interceptions = SafeParseInt(csv.GetField("Interceptions")),
                Positioning = SafeParseInt(csv.GetField("Positioning")),
                Vision = SafeParseInt(csv.GetField("Vision")),
                Penalties = SafeParseInt(csv.GetField("Penalties")),
                Composure = SafeParseInt(csv.GetField("Composure")),
                Marking = SafeParseInt(csv.GetField("Marking")),
                StandingTackle = SafeParseInt(csv.GetField("StandingTackle")),
                SlidingTackle = SafeParseInt(csv.GetField("SlidingTackle")),
                GKDiving = SafeParseInt(csv.GetField("GKDiving")),
                GKHandling = SafeParseInt(csv.GetField("GKHandling")),
                GKKicking = SafeParseInt(csv.GetField("GKKicking")),
                GKPositioning = SafeParseInt(csv.GetField("GKPositioning")),
                GKReflexes = SafeParseInt(csv.GetField("GKReflexes")),
            };
            Players.Add(player);
        }
    }

    // --- Helpers ---

    private static string MapTournament(string tournament)
    {
        return tournament switch
        {
            "Copa do Brasil" => "Copa do Brasil",
            "Brasileirão" => "Brasileirão",
            "Serie A" => "Brasileirão",
            "Serie B" => "Brasileirão Série B",
            "Serie C" => "Brasileirão Série C",
            "Copa do Nordeste" => "Copa do Nordeste",
            "Copa Paulista" => "Copa Paulista",
            "Copa Gaúcha" => "Copa Gaúcha",
            "Copa Carioca" => "Copa Carioca",
            "Amistoso" => "Amistoso",
            "Amistoso da seleção" => "Amistoso da seleção",
            _ => tournament,
        };
    }

    private static bool TryParseBrazilianDate(string dateStr, out DateTime result)
    {
        if (DateTime.TryParseExact(dateStr, "dd/MM/yyyy", CultureInfo.InvariantCulture,
                DateTimeStyles.None, out result))
            return true;
        return DateTime.TryParse(dateStr, out result);
    }

    private static DateTime SafeParseDateTime(string s)
    {
        if (string.IsNullOrWhiteSpace(s)) return DateTime.MinValue;
        return DateTime.TryParse(s, out var result) ? result : DateTime.MinValue;
    }

    private static int SafeParseInt(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return 0;
        if (s!.Contains('+'))
            s = s.Split('+')[0];
        // Handle decimal strings like "1.0" by parsing as double first
        if (s.Contains('.'))
        {
            if (double.TryParse(s, CultureInfo.InvariantCulture, out var d))
                return (int)Math.Round(d);
            return 0;
        }
        return int.TryParse(s.Trim(), out var v) ? v : 0;
    }

    private static int? SafeParseIntNullable(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        if (s!.Contains('+'))
            s = s.Split('+')[0];
        if (s.Contains('.'))
        {
            if (double.TryParse(s, CultureInfo.InvariantCulture, out var d))
                return (int)Math.Round(d);
            return null;
        }
        return int.TryParse(s.Trim(), out var v) ? v : (int?)null;
    }

    private static double? SafeParseDouble(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        return double.TryParse(s, CultureInfo.InvariantCulture, out var v) ? v : null;
    }
}