using System.Globalization;
using BrazilianSoccerMcp.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Data;

public sealed class MatchDataLoader
{
    private List<SoccerMatch>? _matches;

    public IReadOnlyList<SoccerMatch> Matches => _matches ??= LoadAllMatches();

    private List<SoccerMatch> LoadAllMatches()
    {
        var matches = new List<SoccerMatch>();
        var dataDir = FindDataDirectory();

        matches.AddRange(LoadBrasileiraoMatches(Path.Combine(dataDir, "Brasileirao_Matches.csv")));
        matches.AddRange(LoadCopaDoBrasilMatches(Path.Combine(dataDir, "Brazilian_Cup_Matches.csv")));
        matches.AddRange(LoadLibertadoresMatches(Path.Combine(dataDir, "Libertadores_Matches.csv")));
        matches.AddRange(LoadBrFootballDataset(Path.Combine(dataDir, "BR-Football-Dataset.csv")));
        matches.AddRange(LoadHistoricalBrasileirao(Path.Combine(dataDir, "novo_campeonato_brasileiro.csv")));

        return matches;
    }

    private static string FindDataDirectory()
    {
        // Look for data/kaggle relative to current directory and parent directories
        var dir = Directory.GetCurrentDirectory();
        for (int i = 0; i < 6; i++)
        {
            var candidate = Path.Combine(dir, "data", "kaggle");
            if (Directory.Exists(candidate))
                return candidate;
            var parent = Directory.GetParent(dir);
            if (parent is null) break;
            dir = parent.FullName;
        }
        throw new DirectoryNotFoundException("Could not find data/kaggle directory");
    }

    private static List<SoccerMatch> LoadBrasileiraoMatches(string path)
    {
        if (!File.Exists(path)) return [];
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            MissingFieldFound = null,
            BadDataFound = null,
        });

        return csv.GetRecords<BrasileiraoRow>().Select(r => new SoccerMatch
        {
            Date = ParseDateTime(r.datetime),
            HomeTeam = r.home_team?.Trim('"') ?? "",
            AwayTeam = r.away_team?.Trim('"') ?? "",
            HomeGoals = int.TryParse(r.home_goal, out var hg) ? hg : 0,
            AwayGoals = int.TryParse(r.away_goal, out var ag) ? ag : 0,
            Competition = "Brasileirão",
            Season = int.TryParse(r.season, out var s) ? s : 0,
            Round = r.round ?? "",
            HomeTeamState = r.home_team_state?.Trim('"'),
            AwayTeamState = r.away_team_state?.Trim('"'),
        }).ToList();
    }

    private static List<SoccerMatch> LoadCopaDoBrasilMatches(string path)
    {
        if (!File.Exists(path)) return [];
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            MissingFieldFound = null,
            BadDataFound = null,
        });

        return csv.GetRecords<CopaDoBrasilRow>().Select(r => new SoccerMatch
        {
            Date = ParseDateTime(r.datetime),
            HomeTeam = r.home_team?.Trim('"') ?? "",
            AwayTeam = r.away_team?.Trim('"') ?? "",
            HomeGoals = int.TryParse(r.home_goal, out var hg) ? hg : 0,
            AwayGoals = int.TryParse(r.away_goal, out var ag) ? ag : 0,
            Competition = "Copa do Brasil",
            Season = int.TryParse(r.season, out var s) ? s : 0,
            Round = r.round ?? "",
        }).ToList();
    }

    private static List<SoccerMatch> LoadLibertadoresMatches(string path)
    {
        if (!File.Exists(path)) return [];
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            MissingFieldFound = null,
            BadDataFound = null,
        });

        return csv.GetRecords<LibertadoresRow>().Select(r => new SoccerMatch
        {
            Date = ParseDateTime(r.datetime),
            HomeTeam = r.home_team?.Trim('"') ?? "",
            AwayTeam = r.away_team?.Trim('"') ?? "",
            HomeGoals = int.TryParse(r.home_goal, out var hg) ? hg : 0,
            AwayGoals = int.TryParse(r.away_goal, out var ag) ? ag : 0,
            Competition = "Copa Libertadores",
            Season = int.TryParse(r.season, out var s) ? s : 0,
            Round = "",
            Stage = r.stage?.Trim('"'),
        }).ToList();
    }

    private static List<SoccerMatch> LoadBrFootballDataset(string path)
    {
        if (!File.Exists(path)) return [];
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            MissingFieldFound = null,
            BadDataFound = null,
        });

        return csv.GetRecords<BrFootballRow>().Select(r => new SoccerMatch
        {
            Date = ParseDate(r.date),
            HomeTeam = r.home ?? "",
            AwayTeam = r.away ?? "",
            HomeGoals = int.TryParse(r.home_goal, out var hg) ? hg : 0,
            AwayGoals = int.TryParse(r.away_goal, out var ag) ? ag : 0,
            Competition = NormalizeCompetitionName(r.tournament),
            Season = ParseDate(r.date).Year,
            Round = "",
            HomeCorners = double.TryParse(r.home_corner, out var hc) ? hc : null,
            AwayCorners = double.TryParse(r.away_corner, out var ac) ? ac : null,
            HomeAttacks = double.TryParse(r.home_attack, out var ha) ? ha : null,
            AwayAttacks = double.TryParse(r.away_attack, out var aa) ? aa : null,
            HomeShots = double.TryParse(r.home_shots, out var hs) ? hs : null,
            AwayShots = double.TryParse(r.away_shots, out var @as) ? @as : null,
            TotalCorners = double.TryParse(r.total_corners, out var tc) ? tc : null,
            HalfTimeResult = r.ht_result,
        }).ToList();
    }

    private static List<SoccerMatch> LoadHistoricalBrasileirao(string path)
    {
        if (!File.Exists(path)) return [];
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(new CultureInfo("pt-BR"))
        {
            MissingFieldFound = null,
            BadDataFound = null,
            Delimiter = ",",
        });

        return csv.GetRecords<HistoricalRow>().Select(r => new SoccerMatch
        {
            Date = ParseBrazilianDate(r.Data),
            HomeTeam = r.Equipe_mandante ?? "",
            AwayTeam = r.Equipe_visitante ?? "",
            HomeGoals = int.TryParse(r.Gols_mandante, out var hg) ? hg : 0,
            AwayGoals = int.TryParse(r.Gols_visitante, out var ag) ? ag : 0,
            Competition = "Brasileirão",
            Season = int.TryParse(r.Ano, out var s) ? s : 0,
            Round = r.Rodada ?? "",
            HomeTeamState = r.Mandante_UF,
            AwayTeamState = r.Visitante_UF,
            Stadium = r.Arena,
        }).ToList();
    }

    private static DateTime ParseDateTime(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return DateTime.MinValue;
        return DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt)
            ? dt : DateTime.MinValue;
    }

    private static DateTime ParseDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return DateTime.MinValue;
        return DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt)
            ? dt : DateTime.MinValue;
    }

    private static DateTime ParseBrazilianDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return DateTime.MinValue;
        return DateTime.TryParseExact(s, "dd/MM/yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt)
            ? dt : DateTime.TryParse(s, CultureInfo.InvariantCulture, out dt) ? dt : DateTime.MinValue;
    }

    // CSV row mappings
    private sealed class BrasileiraoRow
    {
        public string datetime { get; set; } = "";
        public string home_team { get; set; } = "";
        public string home_team_state { get; set; } = "";
        public string away_team { get; set; } = "";
        public string away_team_state { get; set; } = "";
        public string home_goal { get; set; } = "";
        public string away_goal { get; set; } = "";
        public string season { get; set; } = "";
        public string round { get; set; } = "";
    }

    private sealed class CopaDoBrasilRow
    {
        public string round { get; set; } = "";
        public string datetime { get; set; } = "";
        public string home_team { get; set; } = "";
        public string away_team { get; set; } = "";
        public string home_goal { get; set; } = "";
        public string away_goal { get; set; } = "";
        public string season { get; set; } = "";
    }

    private sealed class LibertadoresRow
    {
        public string datetime { get; set; } = "";
        public string home_team { get; set; } = "";
        public string away_team { get; set; } = "";
        public string home_goal { get; set; } = "";
        public string away_goal { get; set; } = "";
        public string season { get; set; } = "";
        public string stage { get; set; } = "";
    }

    private sealed class BrFootballRow
    {
        public string tournament { get; set; } = "";
        public string home { get; set; } = "";
        public string away { get; set; } = "";
        public string home_goal { get; set; } = "";
        public string away_goal { get; set; } = "";
        public string home_corner { get; set; } = "";
        public string away_corner { get; set; } = "";
        public string home_attack { get; set; } = "";
        public string away_attack { get; set; } = "";
        public string home_shots { get; set; } = "";
        public string away_shots { get; set; } = "";
        public string time { get; set; } = "";
        public string date { get; set; } = "";
        public string ht_result { get; set; } = "";
        public string at_result { get; set; } = "";
        public string total_corners { get; set; } = "";
    }

    private static string NormalizeCompetitionName(string? tournament) => tournament?.Trim() switch
    {
        "Serie A" => "Brasileirão",
        "Serie B" => "Brasileirão Série B",
        "Serie C" => "Brasileirão Série C",
        "Copa do Brasil" => "Copa do Brasil",
        "Copa Libertadores" => "Copa Libertadores",
        null or "" => "Unknown",
        var s => s
    };

    private sealed class HistoricalRow
    {
        public string ID { get; set; } = "";
        public string Data { get; set; } = "";
        public string Ano { get; set; } = "";
        public string Rodada { get; set; } = "";
        public string Equipe_mandante { get; set; } = "";
        public string Equipe_visitante { get; set; } = "";
        public string Gols_mandante { get; set; } = "";
        public string Gols_visitante { get; set; } = "";
        public string? Mandante_UF { get; set; }
        public string? Visitante_UF { get; set; }
        public string? Vencedor { get; set; }
        public string? Arena { get; set; }
        public string? OBS { get; set; }
    }
}
