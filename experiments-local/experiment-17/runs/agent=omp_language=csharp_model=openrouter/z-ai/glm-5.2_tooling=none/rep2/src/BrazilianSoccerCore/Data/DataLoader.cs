using System.Globalization;
using BrazilianSoccerCore.Models;

namespace BrazilianSoccerCore.Data;

/// <summary>
/// Loads all six CSV datasets into unified Match and Player collections.
/// Handles heterogeneous date formats and team-name conventions.
/// </summary>
public sealed class DataLoader
{
    public IReadOnlyList<Match> Matches { get; }
    public IReadOnlyList<Player> Players { get; }

    public DataLoader(string dataDirectory)
    {
        var matches = new List<Match>();
        var players = new List<Player>();

        LoadBrasileirao(matches, Path.Combine(dataDirectory, "Brasileirao_Matches.csv"));
        LoadCopaDoBrasil(matches, Path.Combine(dataDirectory, "Brazilian_Cup_Matches.csv"));
        LoadLibertadores(matches, Path.Combine(dataDirectory, "Libertadores_Matches.csv"));
        LoadBrFootball(matches, Path.Combine(dataDirectory, "BR-Football-Dataset.csv"));
        LoadHistoricalBrasileirao(matches, Path.Combine(dataDirectory, "novo_campeonato_brasileiro.csv"));
        LoadFifa(players, Path.Combine(dataDirectory, "fifa_data.csv"));

        Matches = matches;
        Players = players;
    }

    // ---------- Match datasets ----------

    private static void LoadBrasileirao(List<Match> dest, string path)
    {
        if (!File.Exists(path)) return;
        var rows = CsvReader.ReadAll(path);
        if (rows.Count < 2) return;
        var header = new CsvHeader(rows[0]);
        for (var i = 1; i < rows.Count; i++)
        {
            var r = rows[i];
            if (r.Length < 9) continue;
            dest.Add(new Match
            {
                Competition = "Brasileirão",
                Source = "Brasileirao_Matches.csv",
                Date = ParseDateTime(r, header, "datetime"),
                HomeTeamRaw = r[header.IndexOf("home_team")!.Value],
                AwayTeamRaw = r[header.IndexOf("away_team")!.Value],
                HomeTeam = TeamNormalizer.Normalize(r[header.IndexOf("home_team")!.Value]),
                AwayTeam = TeamNormalizer.Normalize(r[header.IndexOf("away_team")!.Value]),
                HomeGoal = ParseInt(r, header, "home_goal"),
                AwayGoal = ParseInt(r, header, "away_goal"),
                Season = ParseInt(r, header, "season"),
                Round = r[header.IndexOf("round")!.Value],
            });
        }
    }

    private static void LoadCopaDoBrasil(List<Match> dest, string path)
    {
        if (!File.Exists(path)) return;
        var rows = CsvReader.ReadAll(path);
        if (rows.Count < 2) return;
        var header = new CsvHeader(rows[0]);
        for (var i = 1; i < rows.Count; i++)
        {
            var r = rows[i];
            if (r.Length < 7) continue;
            dest.Add(new Match
            {
                Competition = "Copa do Brasil",
                Source = "Brazilian_Cup_Matches.csv",
                Date = ParseDateTime(r, header, "datetime"),
                HomeTeamRaw = r[header.IndexOf("home_team")!.Value],
                AwayTeamRaw = r[header.IndexOf("away_team")!.Value],
                HomeTeam = TeamNormalizer.Normalize(r[header.IndexOf("home_team")!.Value]),
                AwayTeam = TeamNormalizer.Normalize(r[header.IndexOf("away_team")!.Value]),
                HomeGoal = ParseInt(r, header, "home_goal"),
                AwayGoal = ParseInt(r, header, "away_goal"),
                Season = ParseInt(r, header, "season"),
                Round = r[header.IndexOf("round")!.Value],
            });
        }
    }

    private static void LoadLibertadores(List<Match> dest, string path)
    {
        if (!File.Exists(path)) return;
        var rows = CsvReader.ReadAll(path);
        if (rows.Count < 2) return;
        var header = new CsvHeader(rows[0]);
        for (var i = 1; i < rows.Count; i++)
        {
            var r = rows[i];
            if (r.Length < 7) continue;
            dest.Add(new Match
            {
                Competition = "Libertadores",
                Source = "Libertadores_Matches.csv",
                Date = ParseDateTime(r, header, "datetime"),
                HomeTeamRaw = r[header.IndexOf("home_team")!.Value],
                AwayTeamRaw = r[header.IndexOf("away_team")!.Value],
                HomeTeam = TeamNormalizer.Normalize(r[header.IndexOf("home_team")!.Value]),
                AwayTeam = TeamNormalizer.Normalize(r[header.IndexOf("away_team")!.Value]),
                HomeGoal = ParseInt(r, header, "home_goal"),
                AwayGoal = ParseInt(r, header, "away_goal"),
                Season = ParseInt(r, header, "season"),
                Stage = r[header.IndexOf("stage")!.Value],
            });
        }
    }

    private static void LoadBrFootball(List<Match> dest, string path)
    {
        if (!File.Exists(path)) return;
        var rows = CsvReader.ReadAll(path);
        if (rows.Count < 2) return;
        var header = new CsvHeader(rows[0]);
        for (var i = 1; i < rows.Count; i++)
        {
            var r = rows[i];
            if (r.Length < 8) continue;
            var tournament = r[header.IndexOf("tournament")!.Value];
            dest.Add(new Match
            {
                Competition = NormalizeCompetition(tournament),
                Source = "BR-Football-Dataset.csv",
                Date = ParseDateOnly(r, header, "date"),
                HomeTeamRaw = r[header.IndexOf("home")!.Value],
                AwayTeamRaw = r[header.IndexOf("away")!.Value],
                HomeTeam = TeamNormalizer.Normalize(r[header.IndexOf("home")!.Value]),
                AwayTeam = TeamNormalizer.Normalize(r[header.IndexOf("away")!.Value]),
                HomeGoal = ParseInt(r, header, "home_goal"),
                AwayGoal = ParseInt(r, header, "away_goal"),
                Season = ParseDateOnly(r, header, "date").Year,
                HomeCorner = ParseInt(r, header, "home_corner"),
                AwayCorner = ParseInt(r, header, "away_corner"),
                HomeShots = ParseInt(r, header, "home_shots"),
                AwayShots = ParseInt(r, header, "away_shots"),
                HomeAttack = ParseInt(r, header, "home_attack"),
                AwayAttack = ParseInt(r, header, "away_attack"),
                TotalCorners = ParseInt(r, header, "total_corners"),
                HalfTimeResult = header.IndexOf("ht_result") is { } hti ? r[hti] : null,
            });
        }
    }

    private static void LoadHistoricalBrasileirao(List<Match> dest, string path)
    {
        if (!File.Exists(path)) return;
        var rows = CsvReader.ReadAll(path);
        if (rows.Count < 2) return;
        var header = new CsvHeader(rows[0]);
        for (var i = 1; i < rows.Count; i++)
        {
            var r = rows[i];
            if (r.Length < 8) continue;
            dest.Add(new Match
            {
                Competition = "Brasileirão (2003-2019)",
                Source = "novo_campeonato_brasileiro.csv",
                Date = ParseBrazilianDate(r, header, "Data"),
                HomeTeamRaw = r[header.IndexOf("Equipe_mandante")!.Value],
                AwayTeamRaw = r[header.IndexOf("Equipe_visitante")!.Value],
                HomeTeam = TeamNormalizer.Normalize(r[header.IndexOf("Equipe_mandante")!.Value]),
                AwayTeam = TeamNormalizer.Normalize(r[header.IndexOf("Equipe_visitante")!.Value]),
                HomeGoal = ParseInt(r, header, "Gols_mandante"),
                AwayGoal = ParseInt(r, header, "Gols_visitante"),
                Season = ParseInt(r, header, "Ano"),
                Round = header.IndexOf("Rodada") is { } rd ? r[rd] : string.Empty,
                Arena = header.IndexOf("Arena") is { } ar ? r[ar] : string.Empty,
            });
        }
    }

    // ---------- Player dataset ----------

    private static void LoadFifa(List<Player> dest, string path)
    {
        if (!File.Exists(path)) return;
        var rows = CsvReader.ReadAll(path);
        if (rows.Count < 2) return;
        var header = new CsvHeader(rows[0]);

        // Skill columns: everything that parses to an int when present.
        var skillColumns = new HashSet<string>
        {
            "Crossing","Finishing","HeadingAccuracy","ShortPassing","Volleys","Dribbling",
            "Curve","FKAccuracy","LongPassing","BallControl","Acceleration","SprintSpeed",
            "Agility","Reactions","Balance","ShotPower","Jumping","Stamina","Strength",
            "LongShots","Aggression","Interceptions","Positioning","Vision","Penalties",
            "Composure","Marking","StandingTackle","SlidingTackle","GKDiving","GKHandling",
            "GKKicking","GKPositioning","GKReflexes"
        };

        for (var i = 1; i < rows.Count; i++)
        {
            var r = rows[i];
            if (r.Length < 5) continue;

            var nameIdx = header.IndexOf("Name")!.Value;
            var name = r[nameIdx];
            if (string.IsNullOrWhiteSpace(name)) continue;

            var skills = new Dictionary<string, int?>();
            foreach (var col in skillColumns)
            {
                if (header.IndexOf(col) is { } idx && idx < r.Length)
                    skills[col] = ParseInt(r, header, col);
            }

            dest.Add(new Player
            {
                Id = ParseInt(r, header, "ID") ?? 0,
                Name = name,
                Age = ParseInt(r, header, "Age") ?? 0,
                Nationality = header.IndexOf("Nationality") is { } ni ? r[ni] : string.Empty,
                Overall = ParseInt(r, header, "Overall") ?? 0,
                Potential = ParseInt(r, header, "Potential") ?? 0,
                Club = header.IndexOf("Club") is { } ci ? r[ci] : string.Empty,
                Position = header.IndexOf("Position") is { } pi ? r[pi] : string.Empty,
                JerseyNumber = ParseInt(r, header, "Jersey Number"),
                Height = header.IndexOf("Height") is { } hi ? r[hi] : string.Empty,
                Weight = header.IndexOf("Weight") is { } wi ? r[wi] : string.Empty,
                PreferredFoot = header.IndexOf("Preferred Foot") is { } pfi ? r[pfi] : string.Empty,
                Skills = skills,
            });
        }
    }

    // ---------- Parsing helpers ----------

    private static DateTime ParseDateTime(string[] r, CsvHeader header, string col)
    {
        if (header.IndexOf(col) is not { } idx) return DateTime.MinValue;
        var val = r[idx];
        return DateTime.TryParse(val, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal, out var dt)
            ? dt : DateTime.TryParse(val, CultureInfo.GetCultureInfo("pt-BR"), DateTimeStyles.AssumeUniversal, out var dt2)
            ? dt2 : DateTime.MinValue;
    }

    private static DateTime ParseDateOnly(string[] r, CsvHeader header, string col)
    {
        if (header.IndexOf(col) is not { } idx) return DateTime.MinValue;
        var val = r[idx];
        return DateTime.TryParse(val, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal, out var dt)
            ? dt : DateTime.MinValue;
    }

    private static DateTime ParseBrazilianDate(string[] r, CsvHeader header, string col)
    {
        if (header.IndexOf(col) is not { } idx) return DateTime.MinValue;
        var val = r[idx];
        return DateTime.TryParseExact(val, "dd/MM/yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt)
            ? dt : DateTime.TryParse(val, CultureInfo.GetCultureInfo("pt-BR"), DateTimeStyles.None, out var dt2)
            ? dt2 : DateTime.MinValue;
    }

    private static int? ParseInt(string[] r, CsvHeader header, string col)
    {
        if (header.IndexOf(col) is not { } idx || idx >= r.Length) return null;
        var val = r[idx].Trim().Trim('"');
        if (string.IsNullOrWhiteSpace(val)) return null;
        // FIFA uses plain integers; goals use plain integers; some are "2".
        if (int.TryParse(val, NumberStyles.Integer, CultureInfo.InvariantCulture, out var n))
            return n;
        // BR-Football-Dataset encodes goals as floats ("1.0").
        if (double.TryParse(val, NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
            return (int)d;
        return null;
    }

    private static string NormalizeCompetition(string raw)
    {
        var n = raw.Trim();
        if (n.Contains("Brasileir", StringComparison.OrdinalIgnoreCase) || n.Contains("Serie A", StringComparison.OrdinalIgnoreCase))
            return "Brasileirão";
        if (n.Contains("Copa do Brasil", StringComparison.OrdinalIgnoreCase))
            return "Copa do Brasil";
        if (n.Contains("Libertadores", StringComparison.OrdinalIgnoreCase))
            return "Libertadores";
        return n;
    }
}