using System.Globalization;
using System.Text.RegularExpressions;
using BrazilianSoccerMcp.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Services;

public class SoccerDataService
{
    private readonly List<SoccerMatch> _matches = new();
    private readonly List<Player> _players = new();
    private readonly string _dataDirectory;

    public SoccerDataService(string dataDirectory)
    {
        _dataDirectory = dataDirectory;
        LoadData();
    }

    public IReadOnlyList<SoccerMatch> Matches => _matches;
    public IReadOnlyList<Player> Players => _players;

    private void LoadData()
    {
        LoadBrasileirao();
        LoadBrazilianCup();
        LoadLibertadores();
        LoadExtended();
        LoadHistorical();
        LoadPlayers();
    }

    private void LoadBrasileirao()
    {
        var path = Path.Combine(_dataDirectory, "Brasileirao_Matches.csv");
        if (!File.Exists(path)) return;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null
        };

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, config);
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            _matches.Add(new SoccerMatch
            {
                Competition = "Brasileirão Serie A",
                Date = ParseDate(csv.GetField("datetime")),
                Season = csv.GetField("season"),
                Round = csv.GetField("round"),
                HomeTeam = NormalizeTeamName(csv.GetField("home_team")),
                AwayTeam = NormalizeTeamName(csv.GetField("away_team")),
                HomeGoals = ParseInt(csv.GetField("home_goal")),
                AwayGoals = ParseInt(csv.GetField("away_goal")),
                SourceFile = "Brasileirao_Matches.csv"
            });
        }
    }

    private void LoadBrazilianCup()
    {
        var path = Path.Combine(_dataDirectory, "Brazilian_Cup_Matches.csv");
        if (!File.Exists(path)) return;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null
        };

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, config);
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            _matches.Add(new SoccerMatch
            {
                Competition = "Copa do Brasil",
                Date = ParseDate(csv.GetField("datetime")),
                Season = csv.GetField("season"),
                Round = csv.GetField("round"),
                HomeTeam = NormalizeTeamName(csv.GetField("home_team")),
                AwayTeam = NormalizeTeamName(csv.GetField("away_team")),
                HomeGoals = ParseInt(csv.GetField("home_goal")),
                AwayGoals = ParseInt(csv.GetField("away_goal")),
                SourceFile = "Brazilian_Cup_Matches.csv"
            });
        }
    }

    private void LoadLibertadores()
    {
        var path = Path.Combine(_dataDirectory, "Libertadores_Matches.csv");
        if (!File.Exists(path)) return;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null
        };

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, config);
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            _matches.Add(new SoccerMatch
            {
                Competition = "Copa Libertadores",
                Date = ParseDate(csv.GetField("datetime")),
                Season = csv.GetField("season"),
                Round = csv.GetField("stage"),
                Stage = csv.GetField("stage"),
                HomeTeam = NormalizeTeamName(csv.GetField("home_team")),
                AwayTeam = NormalizeTeamName(csv.GetField("away_team")),
                HomeGoals = ParseInt(csv.GetField("home_goal")),
                AwayGoals = ParseInt(csv.GetField("away_goal")),
                SourceFile = "Libertadores_Matches.csv"
            });
        }
    }

    private void LoadExtended()
    {
        var path = Path.Combine(_dataDirectory, "BR-Football-Dataset.csv");
        if (!File.Exists(path)) return;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null
        };

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, config);
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            _matches.Add(new SoccerMatch
            {
                Competition = csv.GetField("tournament") ?? "Unknown",
                Date = ParseDate(csv.GetField("date")),
                Season = ParseDate(csv.GetField("date")).Year.ToString(),
                Round = "",
                HomeTeam = NormalizeTeamName(csv.GetField("home")),
                AwayTeam = NormalizeTeamName(csv.GetField("away")),
                HomeGoals = ParseInt(csv.GetField("home_goal")),
                AwayGoals = ParseInt(csv.GetField("away_goal")),
                HomeCorners = ParseNullableInt(csv.GetField("home_corner")),
                AwayCorners = ParseNullableInt(csv.GetField("away_corner")),
                SourceFile = "BR-Football-Dataset.csv"
            });
        }
    }

    private void LoadHistorical()
    {
        var path = Path.Combine(_dataDirectory, "novo_campeonato_brasileiro.csv");
        if (!File.Exists(path)) return;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null
        };

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, config);
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            _matches.Add(new SoccerMatch
            {
                Competition = "Brasileirão Serie A",
                Date = ParseDate(csv.GetField("Data")),
                Season = csv.GetField("Ano"),
                Round = csv.GetField("Rodada"),
                HomeTeam = NormalizeTeamName(csv.GetField("Equipe_mandante")),
                AwayTeam = NormalizeTeamName(csv.GetField("Equipe_visitante")),
                HomeGoals = ParseInt(csv.GetField("Gols_mandante")),
                AwayGoals = ParseInt(csv.GetField("Gols_visitante")),
                Arena = csv.GetField("Arena"),
                SourceFile = "novo_campeonato_brasileiro.csv"
            });
        }
    }

    private void LoadPlayers()
    {
        var path = Path.Combine(_dataDirectory, "fifa_data.csv");
        if (!File.Exists(path)) return;

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            PrepareHeaderForMatch = args => args.Header.Trim('\uFEFF', ' ', '\t')
        };

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, config);
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            _players.Add(new Player
            {
                Id = ParseInt(csv.GetField("ID")),
                Name = csv.GetField("Name") ?? string.Empty,
                Age = ParseInt(csv.GetField("Age")),
                Nationality = csv.GetField("Nationality") ?? string.Empty,
                Overall = ParseInt(csv.GetField("Overall")),
                Potential = ParseInt(csv.GetField("Potential")),
                Club = csv.GetField("Club") ?? string.Empty,
                Position = csv.GetField("Position") ?? string.Empty,
                Height = csv.GetField("Height"),
                Weight = csv.GetField("Weight")
            });
        }
    }

    private static string NormalizeTeamName(string? name)
    {
        if (string.IsNullOrWhiteSpace(name)) return string.Empty;
        
        var normalized = Regex.Replace(name.Trim(), @"-\w{2}$", "").Trim();
        
        normalized = normalized.Replace("Sport Club Corinthians Paulista", "Corinthians")
                               .Replace("Clube de Regatas do Flamengo", "Flamengo")
                               .Replace("Sociedade Esportiva Palmeiras", "Palmeiras")
                               .Replace("São Paulo Futebol Clube", "São Paulo")
                               .Replace("Grêmio Foot-Ball Porto Alegrense", "Grêmio")
                               .Replace("Internacional", "Internacional")
                               .Replace("Clube Atlético Mineiro", "Atlético Mineiro")
                               .Replace("Cruzeiro Esporte Clube", "Cruzeiro")
                               .Replace("Botafogo de Futebol e Regatas", "Botafogo")
                               .Replace("Vasco da Gama", "Vasco")
                               .Replace("Santos Futebol Clube", "Santos")
                               .Replace("Fluminense Football Club", "Fluminense");

        return normalized;
    }

    private static DateTime ParseDate(string? dateStr)
    {
        if (string.IsNullOrWhiteSpace(dateStr)) return DateTime.MinValue;

        var formats = new[] 
        { 
            "yyyy-MM-dd HH:mm:ss", 
            "yyyy-MM-dd", 
            "dd/MM/yyyy", 
            "dd/MM/yyyy HH:mm:ss" 
        };

        if (DateTime.TryParseExact(dateStr.Trim(), formats, CultureInfo.InvariantCulture, DateTimeStyles.None, out var result))
        {
            return result;
        }

        if (DateTime.TryParse(dateStr, CultureInfo.InvariantCulture, DateTimeStyles.None, out result))
        {
            return result;
        }

        return DateTime.MinValue;
    }

    private static int ParseInt(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return 0;
        if (int.TryParse(value.Trim(), out var result)) return result;
        if (double.TryParse(value.Trim(), out var doubleResult)) return (int)doubleResult;
        return 0;
    }

    private static int? ParseNullableInt(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        if (int.TryParse(value.Trim(), out var result)) return result;
        if (double.TryParse(value.Trim(), out var doubleResult)) return (int)doubleResult;
        return null;
    }

    public List<SoccerMatch> SearchSoccerMatches(string? team = null, string? competition = null, 
                                     string? season = null, DateTime? startDate = null, DateTime? endDate = null, int limit = 50)
    {
        var query = _matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(team))
        {
            var normalizedTeam = NormalizeTeamName(team);
            query = query.Where(m => m.HomeTeam.Contains(normalizedTeam, StringComparison.OrdinalIgnoreCase) ||
                                     m.AwayTeam.Contains(normalizedTeam, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(competition))
        {
            query = query.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(season))
        {
            query = query.Where(m => m.Season == season);
        }

        if (startDate.HasValue)
        {
            query = query.Where(m => m.Date >= startDate.Value);
        }

        if (endDate.HasValue)
        {
            query = query.Where(m => m.Date <= endDate.Value);
        }

        return query.OrderByDescending(m => m.Date).Take(limit).ToList();
    }

    public Dictionary<string, object> GetTeamStatistics(string team, string? season = null)
    {
        var normalizedTeam = NormalizeTeamName(team);
        var query = _matches.Where(m => m.HomeTeam.Equals(normalizedTeam, StringComparison.OrdinalIgnoreCase) ||
                                        m.AwayTeam.Equals(normalizedTeam, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(season))
        {
            query = query.Where(m => m.Season == season);
        }

        var matchesList = query.ToList();
        int wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0, homeWins = 0, homeDraws = 0, homeLosses = 0;

        foreach (var m in matchesList)
        {
            bool isHome = m.HomeTeam.Equals(normalizedTeam, StringComparison.OrdinalIgnoreCase);
            int teamGoals = isHome ? m.HomeGoals : m.AwayGoals;
            int oppGoals = isHome ? m.AwayGoals : m.HomeGoals;

            goalsFor += teamGoals;
            goalsAgainst += oppGoals;

            if (teamGoals > oppGoals) 
            { 
                wins++; 
                if (isHome) homeWins++;
            }
            else if (teamGoals == oppGoals) 
            { 
                draws++; 
                if (isHome) homeDraws++;
            }
            else 
            { 
                losses++; 
                if (isHome) homeLosses++;
            }
        }

        var totalMatches = matchesList.Count;
        var winRate = totalMatches > 0 ? (double)wins / totalMatches * 100 : 0;

        return new Dictionary<string, object>
        {
            ["Team"] = normalizedTeam,
            ["Season"] = season ?? "All",
            ["TotalMatches"] = totalMatches,
            ["Wins"] = wins,
            ["Draws"] = draws,
            ["Losses"] = losses,
            ["GoalsFor"] = goalsFor,
            ["GoalsAgainst"] = goalsAgainst,
            ["WinRate"] = $"{winRate:F1}%",
            ["HomeRecord"] = $"W:{homeWins} D:{homeDraws} L:{homeLosses}"
        };
    }

    public List<Player> SearchPlayers(string? name = null, string? nationality = null, 
                                      string? club = null, string? position = null, int limit = 50)
    {
        var query = _players.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(name))
        {
            query = query.Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(nationality))
        {
            query = query.Where(p => p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(club))
        {
            query = query.Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(position))
        {
            query = query.Where(p => p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));
        }

        return query.OrderByDescending(p => p.Overall).Take(limit).ToList();
    }

    public List<Dictionary<string, object>> GetHeadToHead(string team1, string team2, string? season = null)
    {
        var t1 = NormalizeTeamName(team1);
        var t2 = NormalizeTeamName(team2);

        var query = _matches.Where(m => 
            (m.HomeTeam.Equals(t1, StringComparison.OrdinalIgnoreCase) && m.AwayTeam.Equals(t2, StringComparison.OrdinalIgnoreCase)) ||
            (m.HomeTeam.Equals(t2, StringComparison.OrdinalIgnoreCase) && m.AwayTeam.Equals(t1, StringComparison.OrdinalIgnoreCase)));

        if (!string.IsNullOrWhiteSpace(season))
        {
            query = query.Where(m => m.Season == season);
        }

        var matchesList = query.OrderByDescending(m => m.Date).ToList();
        int t1Wins = 0, t2Wins = 0, draws = 0;

        var results = new List<Dictionary<string, object>>();

        foreach (var m in matchesList)
        {
            bool t1IsHome = m.HomeTeam.Equals(t1, StringComparison.OrdinalIgnoreCase);
            int t1Goals = t1IsHome ? m.HomeGoals : m.AwayGoals;
            int t2Goals = t1IsHome ? m.AwayGoals : m.HomeGoals;

            if (t1Goals > t2Goals) t1Wins++;
            else if (t2Goals > t1Goals) t2Wins++;
            else draws++;

            results.Add(new Dictionary<string, object>
            {
                ["Date"] = m.Date.ToString("yyyy-MM-dd"),
                ["Competition"] = m.Competition,
                ["HomeTeam"] = m.HomeTeam,
                ["AwayTeam"] = m.AwayTeam,
                ["Score"] = $"{m.HomeGoals}-{m.AwayGoals}",
                ["Round"] = m.Round
            });
        }

        results.Insert(0, new Dictionary<string, object>
        {
            ["Summary"] = $"{t1} {t1Wins} wins, {t2} {t2Wins} wins, {draws} draws"
        });

        return results;
    }

    public Dictionary<string, object> GetStatisticalAnalysis(string? competition = null, string? season = null)
    {
        var query = _matches.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(competition))
        {
            query = query.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
        }

        if (!string.IsNullOrWhiteSpace(season))
        {
            query = query.Where(m => m.Season == season);
        }

        var matchesList = query.ToList();
        if (matchesList.Count == 0) return new Dictionary<string, object> { ["Error"] = "No matches found for criteria" };

        double totalGoals = matchesList.Sum(m => m.HomeGoals + m.AwayGoals);
        double avgGoals = totalGoals / matchesList.Count;
        
        int homeWins = matchesList.Count(m => m.HomeGoals > m.AwayGoals);
        double homeWinRate = (double)homeWins / matchesList.Count * 100;

        var biggestWins = matchesList
            .OrderByDescending(m => Math.Abs(m.HomeGoals - m.AwayGoals))
            .ThenByDescending(m => Math.Max(m.HomeGoals, m.AwayGoals))
            .Take(5)
            .Select(m => new Dictionary<string, object>
            {
                ["Date"] = m.Date.ToString("yyyy-MM-dd"),
                ["MatchStr"] = $"{m.HomeTeam} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeam}",
                ["Competition"] = m.Competition
            })
            .ToList();

        return new Dictionary<string, object>
        {
            ["TotalMatches"] = matchesList.Count,
            ["AverageGoalsPerMatch"] = Math.Round(avgGoals, 2),
            ["HomeWinRate"] = $"{homeWinRate:F1}%",
            ["BiggestWins"] = biggestWins
        };
    }

    public List<Dictionary<string, object>> GetCompetitionStandings(string competition, string season)
    {
        var query = _matches.Where(m => 
            m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) && 
            m.Season == season);

        var matchesList = query.ToList();
        var standings = new Dictionary<string, Dictionary<string, int>>();

        foreach (var m in matchesList)
        {
            if (!standings.ContainsKey(m.HomeTeam))
                standings[m.HomeTeam] = new Dictionary<string, int> { ["P"] = 0, ["W"] = 0, ["D"] = 0, ["L"] = 0, ["GF"] = 0, ["GA"] = 0, ["Pts"] = 0 };
            
            if (!standings.ContainsKey(m.AwayTeam))
                standings[m.AwayTeam] = new Dictionary<string, int> { ["P"] = 0, ["W"] = 0, ["D"] = 0, ["L"] = 0, ["GF"] = 0, ["GA"] = 0, ["Pts"] = 0 };

            standings[m.HomeTeam]["P"]++;
            standings[m.AwayTeam]["P"]++;
            standings[m.HomeTeam]["GF"] += m.HomeGoals;
            standings[m.HomeTeam]["GA"] += m.AwayGoals;
            standings[m.AwayTeam]["GF"] += m.AwayGoals;
            standings[m.AwayTeam]["GA"] += m.HomeGoals;

            if (m.HomeGoals > m.AwayGoals)
            {
                standings[m.HomeTeam]["W"]++;
                standings[m.HomeTeam]["Pts"] += 3;
                standings[m.AwayTeam]["L"]++;
            }
            else if (m.HomeGoals < m.AwayGoals)
            {
                standings[m.AwayTeam]["W"]++;
                standings[m.AwayTeam]["Pts"] += 3;
                standings[m.HomeTeam]["L"]++;
            }
            else
            {
                standings[m.HomeTeam]["D"]++;
                standings[m.HomeTeam]["Pts"] += 1;
                standings[m.AwayTeam]["D"]++;
                standings[m.AwayTeam]["Pts"] += 1;
            }
        }

        return standings
            .OrderByDescending(kvp => kvp.Value["Pts"])
            .ThenByDescending(kvp => kvp.Value["GF"] - kvp.Value["GA"])
            .ThenByDescending(kvp => kvp.Value["GF"])
            .Select((kvp, index) => new Dictionary<string, object>
            {
                ["Pos"] = index + 1,
                ["Team"] = kvp.Key,
                ["P"] = kvp.Value["P"],
                ["W"] = kvp.Value["W"],
                ["D"] = kvp.Value["D"],
                ["L"] = kvp.Value["L"],
                ["GF"] = kvp.Value["GF"],
                ["GA"] = kvp.Value["GA"],
                ["GD"] = kvp.Value["GF"] - kvp.Value["GA"],
                ["Pts"] = kvp.Value["Pts"]
            })
            .ToList();
    }
}
