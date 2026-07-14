using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using CsvHelper;
using CsvHelper.Configuration;

public class SoccerDataManager
{
    private readonly string _dataPath;
    public List<MatchRecord> Matches { get; private set; } = new();
    public List<FifaPlayer> Players { get; private set; } = new();

    public SoccerDataManager(string dataPath)
    {
        _dataPath = dataPath;
    }

    public async Task LoadDataAsync()
    {
        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            IgnoreBlankLines = true,
            TrimOptions = TrimOptions.Trim,
            BadDataFound = null,
            MissingFieldFound = null
        };

        Matches = new List<MatchRecord>();
        Players = new List<FifaPlayer>();

        // Load Brasileirao Matches
        await LoadMatchesAsync(Path.Combine(_dataPath, "Brasileirao_Matches.csv"), Matches, config, "Brasileirão Serie A", "season");

        // Load Brazilian Cup Matches
        await LoadMatchesAsync(Path.Combine(_dataPath, "Brazilian_Cup_Matches.csv"), Matches, config, "Copa do Brasil", "season");

        // Load Libertadores Matches
        await LoadMatchesAsync(Path.Combine(_dataPath, "Libertadores_Matches.csv"), Matches, config, "Copa Libertadores", "season");

        // Load BR Football Dataset
        await LoadBrFootballDatasetAsync(Path.Combine(_dataPath, "BR-Football-Dataset.csv"), Matches, config);

        // Load Novo Campeonato Brasileiro
        await LoadNovoCampeonatoAsync(Path.Combine(_dataPath, "novo_campeonato_brasileiro.csv"), Matches, config);

        // Load FIFA Data
        await LoadFifaDataAsync(Path.Combine(_dataPath, "fifa_data.csv"), Players, config);
    }

    private async Task LoadMatchesAsync(string filePath, List<MatchRecord> target, CsvConfiguration config, string defaultCompetition, string seasonField)
    {
        if (!File.Exists(filePath)) return;

        using var reader = new StreamReader(filePath);
        using var csv = new CsvReader(reader, config);

        // Dynamic parsing to handle varying schemas
        var records = csv.GetRecords<dynamic>().ToList();
        foreach (var row in records)
        {
            var record = new MatchRecord();
            record.Competition = defaultCompetition;
            
            record.Date = ParseDate(GetField(row, "datetime") ?? GetField(row, "date") ?? GetField(row, "Data"));
            record.Season = GetField(row, seasonField) ?? GetField(row, "Ano") ?? GetField(row, "season");
            record.Round = GetField(row, "round") ?? GetField(row, "Rodada");
            
            record.HomeTeam = NormalizeTeamName(GetField(row, "home_team") ?? GetField(row, "home") ?? GetField(row, "Equipe_mandante"));
            record.AwayTeam = NormalizeTeamName(GetField(row, "away_team") ?? GetField(row, "away") ?? GetField(row, "Equipe_visitante"));
            
            record.HomeGoals = ParseInt(GetField(row, "home_goal") ?? GetField(row, "Gols_mandante"));
            record.AwayGoals = ParseInt(GetField(row, "away_goal") ?? GetField(row, "Gols_visitante"));
            record.Stage = GetField(row, "stage");

            if (!string.IsNullOrWhiteSpace(record.HomeTeam) && !string.IsNullOrWhiteSpace(record.AwayTeam))
            {
                target.Add(record);
            }
        }
    }

    private async Task LoadBrFootballDatasetAsync(string filePath, List<MatchRecord> target, CsvConfiguration config)
    {
        if (!File.Exists(filePath)) return;

        using var reader = new StreamReader(filePath);
        using var csv = new CsvReader(reader, config);

        var records = csv.GetRecords<dynamic>().ToList();
        foreach (var row in records)
        {
            var record = new MatchRecord();
            record.Competition = GetField(row, "tournament") ?? "BR Football Dataset";
            record.Date = ParseDate(GetField(row, "date"));
            record.Season = record.Date?.Year.ToString();
            
            record.HomeTeam = NormalizeTeamName(GetField(row, "home"));
            record.AwayTeam = NormalizeTeamName(GetField(row, "away"));
            
            record.HomeGoals = ParseInt(GetField(row, "home_goal"));
            record.AwayGoals = ParseInt(GetField(row, "away_goal"));

            if (!string.IsNullOrWhiteSpace(record.HomeTeam) && !string.IsNullOrWhiteSpace(record.AwayTeam))
            {
                target.Add(record);
            }
        }
    }

    private async Task LoadNovoCampeonatoAsync(string filePath, List<MatchRecord> target, CsvConfiguration config)
    {
        if (!File.Exists(filePath)) return;

        using var reader = new StreamReader(filePath);
        using var csv = new CsvReader(reader, config);

        var records = csv.GetRecords<dynamic>().ToList();
        foreach (var row in records)
        {
            var record = new MatchRecord();
            record.Competition = "Brasileirão Serie A (Historical)";
            record.Date = ParseDate(GetField(row, "Data"));
            record.Season = GetField(row, "Ano");
            record.Round = GetField(row, "Rodada");
            record.HomeTeam = NormalizeTeamName(GetField(row, "Equipe_mandante"));
            record.AwayTeam = NormalizeTeamName(GetField(row, "Equipe_visitante"));
            record.HomeGoals = ParseInt(GetField(row, "Gols_mandante"));
            record.AwayGoals = ParseInt(GetField(row, "Gols_visitante"));
            record.Stadium = GetField(row, "Arena");

            if (!string.IsNullOrWhiteSpace(record.HomeTeam) && !string.IsNullOrWhiteSpace(record.AwayTeam))
            {
                target.Add(record);
            }
        }
    }

    private async Task LoadFifaDataAsync(string filePath, List<FifaPlayer> target, CsvConfiguration config)
    {
        if (!File.Exists(filePath)) return;

        using var reader = new StreamReader(filePath);
        using var csv = new CsvReader(reader, config);

        var records = csv.GetRecords<dynamic>().ToList();
        foreach (var row in records)
        {
            var name = GetField(row, "Name");
            if (string.IsNullOrWhiteSpace(name)) continue;

            var player = new FifaPlayer
            {
                Name = name.Trim(),
                Age = ParseInt(GetField(row, "Age")),
                Nationality = GetField(row, "Nationality")?.Trim(),
                Overall = ParseInt(GetField(row, "Overall")),
                Potential = ParseInt(GetField(row, "Potential")),
                Club = NormalizeTeamName(GetField(row, "Club")),
                Position = GetField(row, "Position")?.Trim()
            };
            target.Add(player);
        }
    }

    private static string? GetField(dynamic row, string fieldName)
    {
        try
        {
            var dict = (IDictionary<string, object>)row;
            if (dict.TryGetValue(fieldName, out var val) && val != null)
            {
                return val.ToString()?.Trim();
            }
            
            // Try case-insensitive
            var key = dict.Keys.FirstOrDefault(k => k.Equals(fieldName, StringComparison.OrdinalIgnoreCase));
            if (key != null && dict[key] != null)
            {
                return dict[key].ToString()?.Trim();
            }
        }
        catch
        {
            // Ignore
        }
        return null;
    }

    private static DateTime? ParseDate(string? dateStr)
    {
        if (string.IsNullOrWhiteSpace(dateStr)) return null;

        // Try ISO format
        if (DateTime.TryParse(dateStr, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt1))
            return dt1;

        // Try Brazilian format DD/MM/YYYY
        if (DateTime.TryParseExact(dateStr, "dd/MM/yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt2))
            return dt2;

        // Try with time "yyyy-MM-dd HH:mm:ss"
        if (DateTime.TryParseExact(dateStr, "yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt3))
            return dt3;

        return null;
    }

    private static int ParseInt(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return 0;
        if (int.TryParse(value, out var result)) return result;
        if (double.TryParse(value, out var d)) return (int)d;
        return 0;
    }

    public static string NormalizeTeamName(string? name)
    {
        if (string.IsNullOrWhiteSpace(name)) return string.Empty;

        var normalized = name.Trim();
        
        // Standardize some known variations BEFORE removing state suffix
        normalized = normalized.Replace("Athletico-PR", "Athletico Paranaense")
                               .Replace("Athletico Paranaense", "Athletico Paranaense")
                               .Replace("Atletico-MG", "Atletico Mineiro")
                               .Replace("Atletico-GO", "Atletico Goianiense")
                               .Replace("Atletico-PR", "Athletico Paranaense");

        // Remove state suffix like "-SP", "-RJ", " - MG"
        normalized = Regex.Replace(normalized, @"\s*[-–]\s*[A-Z]{2,3}\s*$", "", RegexOptions.IgnoreCase).Trim();
        
        // Remove common suffixes
        normalized = Regex.Replace(normalized, @"\s*\([^)]+\)\s*$", "").Trim(); // Remove (antigo ...)

        return normalized;
    }

    public List<MatchRecord> SearchMatches(string? team, string? season, string? competition, string? dateFrom, string? dateTo)
    {
        var query = Matches.AsQueryable();

        if (!string.IsNullOrWhiteSpace(team))
        {
            var normTeam = NormalizeTeamName(team);
            query = query.Where(m => m.HomeTeam.Contains(normTeam, StringComparison.OrdinalIgnoreCase) || 
                                     m.AwayTeam.Contains(normTeam, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(season))
        {
            query = query.Where(m => m.Season != null && m.Season.Contains(season));
        }

        if (!string.IsNullOrWhiteSpace(competition))
        {
            query = query.Where(m => m.Competition != null && m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(dateFrom) && DateTime.TryParse(dateFrom, out var df))
        {
            query = query.Where(m => m.Date >= df);
        }

        if (!string.IsNullOrWhiteSpace(dateTo) && DateTime.TryParse(dateTo, out var dt))
        {
            query = query.Where(m => m.Date <= dt);
        }

        return query.OrderByDescending(m => m.Date).ToList();
    }

    public TeamStatsRecord? GetTeamStats(string team, string? season)
    {
        var normTeam = NormalizeTeamName(team);
        var teamMatches = Matches.Where(m => 
            m.HomeTeam.Contains(normTeam, StringComparison.OrdinalIgnoreCase) || 
            m.AwayTeam.Contains(normTeam, StringComparison.OrdinalIgnoreCase)).ToList();

        if (!string.IsNullOrWhiteSpace(season))
        {
            teamMatches = teamMatches.Where(m => m.Season != null && m.Season.Contains(season)).ToList();
        }

        if (!teamMatches.Any()) return null;

        int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
        foreach (var m in teamMatches)
        {
            bool isHome = m.HomeTeam.Contains(normTeam, StringComparison.OrdinalIgnoreCase);
            int teamGoals = isHome ? m.HomeGoals : m.AwayGoals;
            int oppGoals = isHome ? m.AwayGoals : m.HomeGoals;

            gf += teamGoals;
            ga += oppGoals;

            if (teamGoals > oppGoals) wins++;
            else if (teamGoals == oppGoals) draws++;
            else losses++;
        }

        return new TeamStatsRecord
        {
            Team = normTeam,
            Season = season,
            Matches = teamMatches.Count,
            Wins = wins,
            Draws = draws,
            Losses = losses,
            GoalsFor = gf,
            GoalsAgainst = ga,
            WinRate = teamMatches.Count > 0 ? (double)wins / teamMatches.Count : 0
        };
    }

    public HeadToHeadRecord? GetHeadToHead(string team1, string team2)
    {
        var norm1 = NormalizeTeamName(team1);
        var norm2 = NormalizeTeamName(team2);

        var matches = Matches.Where(m =>
            (m.HomeTeam.Contains(norm1, StringComparison.OrdinalIgnoreCase) && m.AwayTeam.Contains(norm2, StringComparison.OrdinalIgnoreCase)) ||
            (m.HomeTeam.Contains(norm2, StringComparison.OrdinalIgnoreCase) && m.AwayTeam.Contains(norm1, StringComparison.OrdinalIgnoreCase))
        ).OrderByDescending(m => m.Date).ToList();

        if (!matches.Any()) return null;

        int team1Wins = 0, team2Wins = 0, draws = 0;
        foreach (var m in matches)
        {
            bool t1Home = m.HomeTeam.Contains(norm1, StringComparison.OrdinalIgnoreCase);
            int t1Goals = t1Home ? m.HomeGoals : m.AwayGoals;
            int t2Goals = t1Home ? m.AwayGoals : m.HomeGoals;

            if (t1Goals > t2Goals) team1Wins++;
            else if (t1Goals < t2Goals) team2Wins++;
            else draws++;
        }

        return new HeadToHeadRecord
        {
            Team1 = norm1,
            Team2 = norm2,
            Team1Wins = team1Wins,
            Team2Wins = team2Wins,
            Draws = draws,
            Matches = matches
        };
    }

    public List<FifaPlayer> SearchPlayers(string? name, string? nationality, string? club, string? position, int? minOverall)
    {
        var query = Players.AsQueryable();

        if (!string.IsNullOrWhiteSpace(name))
        {
            query = query.Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));
        }
        if (!string.IsNullOrWhiteSpace(nationality))
        {
            query = query.Where(p => p.Nationality != null && p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));
        }
        if (!string.IsNullOrWhiteSpace(club))
        {
            var normClub = NormalizeTeamName(club);
            query = query.Where(p => p.Club != null && p.Club.Contains(normClub, StringComparison.OrdinalIgnoreCase));
        }
        if (!string.IsNullOrWhiteSpace(position))
        {
            query = query.Where(p => p.Position != null && p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));
        }
        if (minOverall.HasValue)
        {
            query = query.Where(p => p.Overall >= minOverall.Value);
        }

        return query.OrderByDescending(p => p.Overall).ToList();
    }

    public List<StandingRecord> GetCompetitionStandings(string competition, string season)
    {
        var compMatches = Matches.Where(m => 
            m.Competition != null && m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) &&
            m.Season != null && m.Season.Contains(season)
        ).ToList();

        var teams = compMatches.SelectMany(m => new[] { m.HomeTeam, m.AwayTeam }).Distinct().ToList();
        var standings = new List<StandingRecord>();

        foreach (var team in teams)
        {
            var teamMatches = compMatches.Where(m => m.HomeTeam == team || m.AwayTeam == team).ToList();
            int pts = 0, w = 0, d = 0, l = 0, gf = 0, ga = 0;

            foreach (var m in teamMatches)
            {
                bool isHome = m.HomeTeam == team;
                int tGoals = isHome ? m.HomeGoals : m.AwayGoals;
                int oGoals = isHome ? m.AwayGoals : m.HomeGoals;

                gf += tGoals;
                ga += oGoals;

                if (tGoals > oGoals) { w++; pts += 3; }
                else if (tGoals == oGoals) { d++; pts += 1; }
                else { l++; }
            }

            standings.Add(new StandingRecord
            {
                Team = team,
                Matches = teamMatches.Count,
                Wins = w,
                Draws = d,
                Losses = l,
                GoalsFor = gf,
                GoalsAgainst = ga,
                Points = pts
            });
        }

        return standings.OrderByDescending(s => s.Points)
                        .ThenByDescending(s => s.GoalsFor - s.GoalsAgainst)
                        .ThenByDescending(s => s.GoalsFor)
                        .Select((s, i) => { s.Rank = i + 1; return s; })
                        .ToList();
    }

    public string? GetStatisticalAnalysis(string type)
    {
        if (type == "average_goals")
        {
            if (!Matches.Any()) return "No match data available.";
            double avg = Matches.Average(m => m.HomeGoals + m.AwayGoals);
            return $"Average goals per match across all competitions: {avg:F2}";
        }
        else if (type == "biggest_wins")
        {
            var biggest = Matches
                .Where(m => m.HomeGoals >= 5 || m.AwayGoals >= 5)
                .OrderByDescending(m => Math.Abs(m.HomeGoals - m.AwayGoals))
                .Take(10)
                .Select(m => $"{m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoals} - {m.AwayGoals} {m.AwayTeam} ({m.Competition})")
                .ToList();
            
            return "Biggest victories:\n" + string.Join("\n", biggest);
        }
        else if (type == "home_win_rate")
        {
            var homeWins = Matches.Count(m => m.HomeGoals > m.AwayGoals);
            var total = Matches.Count;
            return $"Home win rate across all matches: {((double)homeWins / total):P1} ({homeWins}/{total})";
        }

        return null;
    }
}

public class MatchRecord
{
    public DateTime? Date { get; set; }
    public string? Season { get; set; }
    public string? Round { get; set; }
    public string HomeTeam { get; set; } = string.Empty;
    public string AwayTeam { get; set; } = string.Empty;
    public int HomeGoals { get; set; }
    public int AwayGoals { get; set; }
    public string? Competition { get; set; }
    public string? Stage { get; set; }
    public string? Stadium { get; set; }
}

public class FifaPlayer
{
    public string Name { get; set; } = string.Empty;
    public int Age { get; set; }
    public string? Nationality { get; set; }
    public int Overall { get; set; }
    public int Potential { get; set; }
    public string? Club { get; set; }
    public string? Position { get; set; }
}

public class TeamStatsRecord
{
    public string Team { get; set; } = string.Empty;
    public string? Season { get; set; }
    public int Matches { get; set; }
    public int Wins { get; set; }
    public int Draws { get; set; }
    public int Losses { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }
    public double WinRate { get; set; }
}

public class HeadToHeadRecord
{
    public string Team1 { get; set; } = string.Empty;
    public string Team2 { get; set; } = string.Empty;
    public int Team1Wins { get; set; }
    public int Team2Wins { get; set; }
    public int Draws { get; set; }
    public List<MatchRecord> Matches { get; set; } = new();
}

public class StandingRecord
{
    public int Rank { get; set; }
    public string Team { get; set; } = string.Empty;
    public int Matches { get; set; }
    public int Wins { get; set; }
    public int Draws { get; set; }
    public int Losses { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }
    public int Points { get; set; }
}