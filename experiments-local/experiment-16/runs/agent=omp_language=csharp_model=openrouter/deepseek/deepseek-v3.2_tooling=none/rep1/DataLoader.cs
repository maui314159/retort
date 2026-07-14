using CsvHelper;
using CsvHelper.Configuration;
using System.Globalization;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMCP
{
    public class DataLoader
    {
        private readonly string _dataPath;
        private List<SoccerMatch>? _matches;
        private List<SoccerPlayer>? _players;
        
        public DataLoader(string dataPath = "data/kaggle")
        {
            _dataPath = dataPath;
        }
        
        /// <summary>
        /// Load all match data from CSV files
        /// </summary>
        public List<SoccerMatch> LoadMatches()
        {
            if (_matches != null) return _matches;
            
            _matches = new List<SoccerMatch>();
            
            try
            {
                // Load Brasileirao matches
                var brasileiraoPath = Path.Combine(_dataPath, "Brasileirao_Matches.csv");
                if (File.Exists(brasileiraoPath))
                {
                    _matches.AddRange(LoadBrasileiraoMatches(brasileiraoPath));
                    Console.WriteLine($"Loaded {_matches.Count} matches from Brasileirao_Matches.csv");
                }
                
                // Load Brazilian Cup matches
                var cupPath = Path.Combine(_dataPath, "Brazilian_Cup_Matches.csv");
                if (File.Exists(cupPath))
                {
                    _matches.AddRange(LoadBrazilianCupMatches(cupPath));
                    Console.WriteLine($"Loaded {_matches.Count - _matches.Count(m => m.SourceFile == "Brasileirao_Matches.csv")} matches from Brazilian_Cup_Matches.csv");
                }
                
                // Load Libertadores matches
                var libertadoresPath = Path.Combine(_dataPath, "Libertadores_Matches.csv");
                if (File.Exists(libertadoresPath))
                {
                    _matches.AddRange(LoadLibertadoresMatches(libertadoresPath));
                    Console.WriteLine($"Loaded {_matches.Count - _matches.Count(m => m.SourceFile == "Libertadores_Matches.csv")} matches from Libertadores_Matches.csv");
                }
                
                // Load BR-Football-Dataset
                var brFootballPath = Path.Combine(_dataPath, "BR-Football-Dataset.csv");
                if (File.Exists(brFootballPath))
                {
                    _matches.AddRange(LoadBrFootballMatches(brFootballPath));
                    Console.WriteLine($"Loaded {_matches.Count - _matches.Count(m => m.SourceFile == "BR-Football-Dataset.csv")} matches from BR-Football-Dataset.csv");
                }
                
                // Load Historical Brasileirão (2003-2019)
                var historicalPath = Path.Combine(_dataPath, "novo_campeonato_brasileiro.csv");
                if (File.Exists(historicalPath))
                {
                    _matches.AddRange(LoadHistoricalBrasileiraoMatches(historicalPath));
                    Console.WriteLine($"Loaded {_matches.Count - _matches.Count(m => m.SourceFile == "novo_campeonato_brasileiro.csv")} matches from novo_campeonato_brasileiro.csv");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error loading match data: {ex.Message}");
                throw;
            }
            
            Console.WriteLine($"Total matches loaded: {_matches.Count}");
            return _matches;
        }
        
        /// <summary>
        /// Load player data from FIFA CSV
        /// </summary>
        public List<SoccerPlayer> LoadPlayers()
        {
            if (_players != null) return _players;
            
            _players = new List<SoccerPlayer>();
            
            try
            {
                var fifaPath = Path.Combine(_dataPath, "fifa_data.csv");
                if (File.Exists(fifaPath))
                {
                    _players = LoadFifaPlayers(fifaPath);
                    Console.WriteLine($"Loaded {_players.Count} players from fifa_data.csv");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error loading player data: {ex.Message}");
                throw;
            }
            
            return _players;
        }
        
        private List<SoccerMatch> LoadBrasileiraoMatches(string filePath)
        {
            var matches = new List<SoccerMatch>();
            var config = new CsvConfiguration(CultureInfo.InvariantCulture)
            {
                HasHeaderRecord = true,
                Delimiter = ",",
                Quote = '"'
            };
            
            using var reader = new StreamReader(filePath);
            using var csv = new CsvReader(reader, config);
            
            var records = csv.GetRecords<dynamic>();
            
            foreach (var record in records)
            {
                try
                {
                    var match = new SoccerMatch
                    {
                        Date = ParseDateTime(record.datetime?.ToString() ?? ""),
                        HomeTeam = record.home_team?.ToString() ?? "",
                        AwayTeam = record.away_team?.ToString() ?? "",
                        HomeTeamNormalized = TeamNormalizer.Normalize(record.home_team?.ToString() ?? ""),
                        AwayTeamNormalized = TeamNormalizer.Normalize(record.away_team?.ToString() ?? ""),
                        HomeGoals = ParseInt(record.home_goal?.ToString()),
                        AwayGoals = ParseInt(record.away_goal?.ToString()),
                        Competition = "Brasileirão Serie A",
                        Season = ParseInt(record.season?.ToString()),
                        Round = record.round?.ToString() ?? "",
                        SourceFile = "Brasileirao_Matches.csv"
                    };
                    
                    matches.Add(match);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error parsing Brasileirao match: {ex.Message}");
                }
            }
            
            return matches;
        }
        
        private List<SoccerMatch> LoadBrazilianCupMatches(string filePath)
        {
            var matches = new List<SoccerMatch>();
            var config = new CsvConfiguration(CultureInfo.InvariantCulture)
            {
                HasHeaderRecord = true,
                Delimiter = ",",
                Quote = '"'
            };
            
            using var reader = new StreamReader(filePath);
            using var csv = new CsvReader(reader, config);
            
            var records = csv.GetRecords<dynamic>();
            
            foreach (var record in records)
            {
                try
                {
                    var match = new SoccerMatch
                    {
                        Date = ParseDateTime(record.datetime?.ToString() ?? ""),
                        HomeTeam = record.home_team?.ToString() ?? "",
                        AwayTeam = record.away_team?.ToString() ?? "",
                        HomeTeamNormalized = TeamNormalizer.Normalize(record.home_team?.ToString() ?? ""),
                        AwayTeamNormalized = TeamNormalizer.Normalize(record.away_team?.ToString() ?? ""),
                        HomeGoals = ParseInt(record.home_goal?.ToString()),
                        AwayGoals = ParseInt(record.away_goal?.ToString()),
                        Competition = "Copa do Brasil",
                        Season = ParseInt(record.season?.ToString()),
                        Round = record.round?.ToString() ?? "",
                        SourceFile = "Brazilian_Cup_Matches.csv"
                    };
                    
                    matches.Add(match);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error parsing Brazilian Cup match: {ex.Message}");
                }
            }
            
            return matches;
        }
        
        private List<SoccerMatch> LoadLibertadoresMatches(string filePath)
        {
            var matches = new List<SoccerMatch>();
            var config = new CsvConfiguration(CultureInfo.InvariantCulture)
            {
                HasHeaderRecord = true,
                Delimiter = ",",
                Quote = '"'
            };
            
            using var reader = new StreamReader(filePath);
            using var csv = new CsvReader(reader, config);
            
            var records = csv.GetRecords<dynamic>();
            
            foreach (var record in records)
            {
                try
                {
                    var match = new SoccerMatch
                    {
                        Date = ParseDateTime(record.datetime?.ToString() ?? ""),
                        HomeTeam = record.home_team?.ToString() ?? "",
                        AwayTeam = record.away_team?.ToString() ?? "",
                        HomeTeamNormalized = TeamNormalizer.Normalize(record.home_team?.ToString() ?? ""),
                        AwayTeamNormalized = TeamNormalizer.Normalize(record.away_team?.ToString() ?? ""),
                        HomeGoals = ParseInt(record.home_goal?.ToString()),
                        AwayGoals = ParseInt(record.away_goal?.ToString()),
                        Competition = "Copa Libertadores",
                        Season = ParseInt(record.season?.ToString()),
                        Stage = record.stage?.ToString() ?? "",
                        SourceFile = "Libertadores_Matches.csv"
                    };
                    
                    matches.Add(match);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error parsing Libertadores match: {ex.Message}");
                }
            }
            
            return matches;
        }
        
        private List<SoccerMatch> LoadBrFootballMatches(string filePath)
        {
            var matches = new List<SoccerMatch>();
            var config = new CsvConfiguration(CultureInfo.InvariantCulture)
            {
                HasHeaderRecord = true,
                Delimiter = ",",
                Quote = '"'
            };
            
            using var reader = new StreamReader(filePath);
            using var csv = new CsvReader(reader, config);
            
            var records = csv.GetRecords<dynamic>();
            
            foreach (var record in records)
            {
                try
                {
                    var match = new SoccerMatch
                    {
                        Date = ParseDateTime(record.date?.ToString() ?? "", record.time?.ToString() ?? ""),
                        HomeTeam = record.home?.ToString() ?? "",
                        AwayTeam = record.away?.ToString() ?? "",
                        HomeTeamNormalized = TeamNormalizer.Normalize(record.home?.ToString() ?? ""),
                        AwayTeamNormalized = TeamNormalizer.Normalize(record.away?.ToString() ?? ""),
                        HomeGoals = ParseInt(record.home_goal?.ToString()),
                        AwayGoals = ParseInt(record.away_goal?.ToString()),
                        Competition = record.tournament?.ToString() ?? "",
                        HomeCorners = ParseInt(record.home_corner?.ToString()),
                        AwayCorners = ParseInt(record.away_corner?.ToString()),
                        HomeAttacks = ParseInt(record.home_attack?.ToString()),
                        AwayAttacks = ParseInt(record.away_attack?.ToString()),
                        HomeShots = ParseInt(record.home_shots?.ToString()),
                        AwayShots = ParseInt(record.away_shots?.ToString()),
                        HalfTimeResult = $"{record.ht_result?.ToString()}-{record.at_result?.ToString()}",
                        TotalCorners = ParseInt(record.total_corners?.ToString()),
                        SourceFile = "BR-Football-Dataset.csv"
                    };
                    
                    // Try to extract season from date
                    if (match.Date != default)
                        match.Season = match.Date.Year;
                    
                    matches.Add(match);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error parsing BR-Football match: {ex.Message}");
                }
            }
            
            return matches;
        }
        
        private List<SoccerMatch> LoadHistoricalBrasileiraoMatches(string filePath)
        {
            var matches = new List<SoccerMatch>();
            var config = new CsvConfiguration(CultureInfo.InvariantCulture)
            {
                HasHeaderRecord = true,
                Delimiter = ",",
                Quote = '"'
            };
            
            using var reader = new StreamReader(filePath);
            using var csv = new CsvReader(reader, config);
            
            var records = csv.GetRecords<dynamic>();
            
            foreach (var record in records)
            {
                try
                {
                    var match = new SoccerMatch
                    {
                        Date = ParseBrazilianDate(record.Data?.ToString() ?? ""),
                        HomeTeam = record.Equipe_mandante?.ToString() ?? "",
                        AwayTeam = record.Equipe_visitante?.ToString() ?? "",
                        HomeTeamNormalized = TeamNormalizer.Normalize(record.Equipe_mandante?.ToString() ?? ""),
                        AwayTeamNormalized = TeamNormalizer.Normalize(record.Equipe_visitante?.ToString() ?? ""),
                        HomeGoals = ParseInt(record.Gols_mandante?.ToString()),
                        AwayGoals = ParseInt(record.Gols_visitante?.ToString()),
                        Competition = "Brasileirão Serie A",
                        Season = ParseInt(record.Ano?.ToString()),
                        Round = record.Rodada?.ToString() ?? "",
                        Stadium = record.Arena?.ToString() ?? "",
                        SourceFile = "novo_campeonato_brasileiro.csv"
                    };
                    
                    matches.Add(match);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error parsing historical Brasileirao match: {ex.Message}");
                }
            }
            
            return matches;
        }
        
        private List<SoccerPlayer> LoadFifaPlayers(string filePath)
        {
            var players = new List<SoccerPlayer>();
            var config = new CsvConfiguration(CultureInfo.InvariantCulture)
            {
                HasHeaderRecord = true,
                Delimiter = ",",
                Quote = '"',
                BadDataFound = null
            };
            
            using var reader = new StreamReader(filePath);
            using var csv = new CsvReader(reader, config);
            
            // Read header
            csv.Read();
            csv.ReadHeader();
            
            // Determine column names dynamically
            var headers = csv.HeaderRecord;
            
            // Map known columns
            while (csv.Read())
            {
                try
                {
                    var player = new SoccerPlayer();
                    
                    // Map known columns
                    if (headers.Contains("ID") || headers.Contains("Id"))
                        player.Id = csv.GetField<int>("ID");
                    else if (headers.Contains("id"))
                        player.Id = csv.GetField<int>("id");
                    
                    player.Name = GetFieldOrDefault(csv, "Name", "name", "Nome");
                    player.Age = GetIntFieldOrDefault(csv, "Age", "age");
                    player.Nationality = GetFieldOrDefault(csv, "Nationality", "nationality");
                    player.Overall = GetIntFieldOrDefault(csv, "Overall", "overall");
                    player.Potential = GetIntFieldOrDefault(csv, "Potential", "potential");
                    player.Club = GetFieldOrDefault(csv, "Club", "club");
                    player.Position = GetFieldOrDefault(csv, "Position", "position");
                    player.JerseyNumber = GetIntFieldOrDefault(csv, "Jersey Number", "Jersey Number", "jersey_number");
                    player.Height = GetFieldOrDefault(csv, "Height", "height");
                    player.Weight = GetFieldOrDefault(csv, "Weight", "weight");
                    
                    // Load skills from all columns that might be skill ratings
                    foreach (var header in headers)
                    {
                        if (IsSkillColumn(header))
                        {
                            var value = csv.GetField<string?>(header);
                            if (int.TryParse(value, out int skillValue))
                            {
                                player.Skills[header] = skillValue;
                            }
                        }
                    }
                    
                    players.Add(player);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error parsing player: {ex.Message}");
                }
            }
            
            return players;
        }
        
        private DateTime ParseDateTime(string dateTimeStr)
        {
            if (string.IsNullOrWhiteSpace(dateTimeStr))
                return default;
            
            // Try ISO format with time
            if (DateTime.TryParse(dateTimeStr, CultureInfo.InvariantCulture, DateTimeStyles.None, out var result))
                return result;
            
            // Try Brazilian date format
            if (DateTime.TryParseExact(dateTimeStr, "dd/MM/yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out result))
                return result;
            
            // Try date only (ISO)
            if (DateTime.TryParseExact(dateTimeStr, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out result))
                return result;
            
            return default;
        }
        
        private DateTime ParseDateTime(string dateStr, string timeStr)
        {
            var combined = $"{dateStr} {timeStr}".Trim();
            if (string.IsNullOrWhiteSpace(combined))
                return default;
            
            return ParseDateTime(combined);
        }
        
        private DateTime ParseBrazilianDate(string dateStr)
        {
            if (string.IsNullOrWhiteSpace(dateStr))
                return default;
            
            // Brazilian format: dd/MM/yyyy
            if (DateTime.TryParseExact(dateStr, "dd/MM/yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out var result))
                return result;
            
            return default;
        }
        
        private int ParseInt(string? value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return 0;
            
            if (int.TryParse(value, out int result))
                return result;
            
            return 0;
        }
        
        private string GetFieldOrDefault(CsvReader csv, params string[] fieldNames)
        {
            foreach (var field in fieldNames)
            {
                try
                {
                    var value = csv.GetField<string?>(field);
                    if (!string.IsNullOrWhiteSpace(value))
                        return value;
                }
                catch (CsvHelperException)
                {
                    // Field not found, try next
                    continue;
                }
            }
            
            return "";
        }
        
        private int GetIntFieldOrDefault(CsvReader csv, params string[] fieldNames)
        {
            foreach (var field in fieldNames)
            {
                try
                {
                    var value = csv.GetField<string?>(field);
                    if (int.TryParse(value, out int result))
                        return result;
                }
                catch (CsvHelperException)
                {
                    continue;
                }
            }
            
            return 0;
        }
        
        private bool IsSkillColumn(string columnName)
        {
            var skillNames = new[]
            {
                "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
                "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
                "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
                "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
                "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
                "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving",
                "GKHandling", "GKKicking", "GKPositioning", "GKReflexes"
            };
            
            return skillNames.Any(skill => columnName.Equals(skill, StringComparison.OrdinalIgnoreCase));
        }
    }
}