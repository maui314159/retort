using System.Globalization;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Loads all six CSV datasets into memory and provides query interfaces.
/// All data is normalised on load for consistent querying.
/// </summary>
public sealed class DataLoader
{
    private readonly string _dataDir;

    public List<MatchRecord> Matches { get; } = new();
    public List<PlayerRecord> Players { get; } = new();

    public DataLoader(string? dataDir = null)
    {
        _dataDir = dataDir ?? Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "data", "kaggle");
    }

    public void LoadAll()
    {
        Matches.Clear();
        Players.Clear();

        LoadBrasileirao();
        LoadBrazilianCup();
        LoadLibertadores();
        LoadBRFootball();
        LoadNovoBrasileirao();
        LoadFifaPlayers();
    }

    // ── Brasileirão Serie A ──────────────────────────────────────────
    private void LoadBrasileirao()
    {
        var path = Path.Combine(_dataDir, "Brasileirao_Matches.csv");
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
        });

        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var rawDate = csv.GetField("datetime") ?? "";
            var dt = MatchRecord.ParseDate(rawDate);

            Matches.Add(new MatchRecord
            {
                Date = dt,
                Season = int.TryParse(csv.GetField("season"), out var s) ? s : null,
                Competition = "Brasileirão",
                HomeTeam = TeamNormalizer.Normalize(csv.GetField("home_team")),
                AwayTeam = TeamNormalizer.Normalize(csv.GetField("away_team")),
                HomeGoals = int.TryParse(csv.GetField("home_goal"), out var hg) ? hg : 0,
                AwayGoals = int.TryParse(csv.GetField("away_goal"), out var ag) ? ag : 0,
                Round = csv.GetField("round"),
                HomeTeamState = csv.GetField("home_team_state"),
                AwayTeamState = csv.GetField("away_team_state"),
            });
        }
    }

    // ── Copa do Brasil ────────────────────────────────────────────────
    private void LoadBrazilianCup()
    {
        var path = Path.Combine(_dataDir, "Brazilian_Cup_Matches.csv");
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
        });

        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var rawDate = csv.GetField("datetime") ?? "";
            var dt = MatchRecord.ParseDate(rawDate);

            Matches.Add(new MatchRecord
            {
                Date = dt,
                Season = int.TryParse(csv.GetField("season"), out var s) ? s : null,
                Competition = "Copa do Brasil",
                HomeTeam = TeamNormalizer.Normalize(csv.GetField("home_team")),
                AwayTeam = TeamNormalizer.Normalize(csv.GetField("away_team")),
                HomeGoals = int.TryParse(csv.GetField("home_goal"), out var hg) ? hg : 0,
                AwayGoals = int.TryParse(csv.GetField("away_goal"), out var ag) ? ag : 0,
                Round = csv.GetField("round"),
            });
        }
    }

    // ── Copa Libertadores ─────────────────────────────────────────────
    private void LoadLibertadores()
    {
        var path = Path.Combine(_dataDir, "Libertadores_Matches.csv");
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
        });

        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var rawDate = csv.GetField("datetime") ?? "";
            var dt = MatchRecord.ParseDate(rawDate);

            Matches.Add(new MatchRecord
            {
                Date = dt,
                Season = int.TryParse(csv.GetField("season"), out var s) ? s : null,
                Competition = "Libertadores",
                HomeTeam = TeamNormalizer.Normalize(csv.GetField("home_team")),
                AwayTeam = TeamNormalizer.Normalize(csv.GetField("away_team")),
                HomeGoals = int.TryParse(csv.GetField("home_goal"), out var hg) ? hg : 0,
                AwayGoals = int.TryParse(csv.GetField("away_goal"), out var ag) ? ag : 0,
                Stage = csv.GetField("stage"),
            });
        }
    }

    // ── BR-Football-Dataset (extended stats) ──────────────────────────
    private void LoadBRFootball()
    {
        var path = Path.Combine(_dataDir, "BR-Football-Dataset.csv");
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
        });

        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var rawDate = csv.GetField("date") ?? "";
            var dt = MatchRecord.ParseDate(rawDate);

            Matches.Add(new MatchRecord
            {
                Date = dt,
                Competition = csv.GetField("tournament") ?? "",
                HomeTeam = TeamNormalizer.Normalize(csv.GetField("home")),
                AwayTeam = TeamNormalizer.Normalize(csv.GetField("away")),
                HomeGoals = ParseDoubleToInt(csv.GetField("home_goal")),
                AwayGoals = ParseDoubleToInt(csv.GetField("away_goal")),
                HomeCorners = ParseNullableDouble(csv.GetField("home_corner")),
                AwayCorners = ParseNullableDouble(csv.GetField("away_corner")),
                HomeShots = ParseNullableDouble(csv.GetField("home_shots")),
                AwayShots = ParseNullableDouble(csv.GetField("away_shots")),
                HalfTimeResult = csv.GetField("ht_result"),
                FullTimeResult = csv.GetField("at_result"),
            });
        }
    }

    // ── Novo Campeonato Brasileiro (2003-2019) ────────────────────────
    private void LoadNovoBrasileirao()
    {
        var path = Path.Combine(_dataDir, "novo_campeonato_brasileiro.csv");
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
        });

        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            var rawDate = csv.GetField("Data") ?? "";
            var dt = MatchRecord.ParseDate(rawDate);

            Matches.Add(new MatchRecord
            {
                Date = dt,
                Season = int.TryParse(csv.GetField("Ano"), out var s) ? s : null,
                Competition = "Brasileirão",
                HomeTeam = TeamNormalizer.Normalize(csv.GetField("Equipe_mandante")),
                AwayTeam = TeamNormalizer.Normalize(csv.GetField("Equipe_visitante")),
                HomeGoals = int.TryParse(csv.GetField("Gols_mandante"), out var hg) ? hg : 0,
                AwayGoals = int.TryParse(csv.GetField("Gols_visitante"), out var ag) ? ag : 0,
                Round = csv.GetField("Rodada"),
                HomeTeamState = csv.GetField("Mandante_UF"),
                AwayTeamState = csv.GetField("Visitante_UF"),
                Stadium = csv.GetField("Arena"),
            });
        }
    }

    // ── FIFA Player Data ──────────────────────────────────────────────
    private void LoadFifaPlayers()
    {
        var path = Path.Combine(_dataDir, "fifa_data.csv");
        if (!File.Exists(path)) return;

        using var reader = new StreamReader(path);
        // Skip BOM if present
        if (reader.Peek() == 0xFEFF) reader.Read();

        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
        });

        csv.Read();
        csv.ReadHeader();

        while (csv.Read())
        {
            Players.Add(new PlayerRecord
            {
                Id = int.TryParse(csv.GetField("ID"), out var id) ? id : 0,
                Name = csv.GetField("Name") ?? "",
                Age = int.TryParse(csv.GetField("Age"), out var age) ? age : 0,
                Nationality = csv.GetField("Nationality") ?? "",
                Overall = int.TryParse(csv.GetField("Overall"), out var ovr) ? ovr : 0,
                Potential = int.TryParse(csv.GetField("Potential"), out var pot) ? pot : 0,
                Club = csv.GetField("Club") ?? "",
                Position = csv.GetField("Position") ?? "",
                PreferredFoot = csv.GetField("Preferred Foot") ?? "",
                Height = csv.GetField("Height"),
                Weight = csv.GetField("Weight"),
                JerseyNumber = int.TryParse(csv.GetField("Jersey Number"), out var jn) ? jn : null,
                Crossing = int.TryParse(csv.GetField("Crossing"), out var cr) ? cr : 0,
                Finishing = int.TryParse(csv.GetField("Finishing"), out var fi) ? fi : 0,
                Dribbling = int.TryParse(csv.GetField("Dribbling"), out var dr) ? dr : 0,
                Passing = int.TryParse(csv.GetField("ShortPassing"), out var sp) ? sp : 0,
                Pace = Math.Max(
                    int.TryParse(csv.GetField("SprintSpeed"), out var ss) ? ss : 0,
                    int.TryParse(csv.GetField("Acceleration"), out var ac) ? ac : 0),
                Shooting = int.TryParse(csv.GetField("ShotPower"), out var sh) ? sh : 0,
                Defending = Math.Max(
                    int.TryParse(csv.GetField("StandingTackle"), out var st) ? st : 0,
                    int.TryParse(csv.GetField("SlidingTackle"), out var sl) ? sl : 0),
                Physical = int.TryParse(csv.GetField("Strength"), out var str) ? str : 0,
            });
        }
    }

    private static int ParseDoubleToInt(string? val)
    {
        if (double.TryParse(val, NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
            return (int)d;
        return 0;
    }

    private static double? ParseNullableDouble(string? val)
    {
        if (double.TryParse(val, NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
            return d;
        return null;
    }
}