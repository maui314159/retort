using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace BrazilianSoccerMCP
{
    /// <summary>
    /// Represents a soccer match with unified schema across datasets
    /// </summary>
    public class SoccerMatch
    {
        public string Id { get; set; } = Guid.NewGuid().ToString();
        public DateTime Date { get; set; }
        public string HomeTeam { get; set; } = "";
        public string AwayTeam { get; set; } = "";
        public string HomeTeamNormalized { get; set; } = "";
        public string AwayTeamNormalized { get; set; } = "";
        public int HomeGoals { get; set; }
        public int AwayGoals { get; set; }
        public string Competition { get; set; } = "";
        public int Season { get; set; }
        public string Round { get; set; } = "";
        public string Stage { get; set; } = "";
        public string Stadium { get; set; } = "";
        public string SourceFile { get; set; } = "";
        
        // Extended statistics (from BR-Football-Dataset.csv)
        public int? HomeCorners { get; set; }
        public int? AwayCorners { get; set; }
        public int? HomeAttacks { get; set; }
        public int? AwayAttacks { get; set; }
        public int? HomeShots { get; set; }
        public int? AwayShots { get; set; }
        public string? HalfTimeResult { get; set; }
        public int? TotalCorners { get; set; }
        
        // Derived properties
        public string Winner => HomeGoals > AwayGoals ? HomeTeamNormalized : 
                               AwayGoals > HomeGoals ? AwayTeamNormalized : "Draw";
        public bool IsDraw => HomeGoals == AwayGoals;
        public int TotalGoals => HomeGoals + AwayGoals;
        
        public override string ToString()
        {
            return $"{Date:yyyy-MM-dd}: {HomeTeamNormalized} {HomeGoals}-{AwayGoals} {AwayTeamNormalized} ({Competition} {Season})";
        }
    }
    
    /// <summary>
    /// Represents a soccer player from FIFA dataset
    /// </summary>
    public class SoccerPlayer
    {
        public int Id { get; set; }
        public string Name { get; set; } = "";
        public int Age { get; set; }
        public string Nationality { get; set; } = "";
        public int Overall { get; set; }
        public int Potential { get; set; }
        public string Club { get; set; } = "";
        public string Position { get; set; } = "";
        public int JerseyNumber { get; set; }
        public string Height { get; set; } = "";
        public string Weight { get; set; } = "";
        public Dictionary<string, int> Skills { get; set; } = new Dictionary<string, int>();
        
        public bool IsBrazilian => Nationality.Equals("Brazil", StringComparison.OrdinalIgnoreCase);
        public bool PlaysForBrazilianClub => Club.Contains("-BR") || 
                                            Club.Contains("Brazil") ||
                                            (Club.Contains("Flamengo") || Club.Contains("Palmeiras") || 
                                             Club.Contains("Corinthians") || Club.Contains("São Paulo") ||
                                             Club.Contains("Santos") || Club.Contains("Grêmio") ||
                                             Club.Contains("Internacional") || Club.Contains("Atlético") ||
                                             Club.Contains("Cruzeiro") || Club.Contains("Fluminense") ||
                                             Club.Contains("Vasco") || Club.Contains("Botafogo") ||
                                             Club.Contains("Bahia") || Club.Contains("Sport") ||
                                             Club.Contains("Fortaleza") || Club.Contains("Ceará") ||
                                             Club.Contains("Athletico") || Club.Contains("Goiás"));
        
        public override string ToString()
        {
            return $"{Name} ({Overall}) - {Position} @ {Club} ({Nationality})";
        }
    }
    
    /// <summary>
    /// Team statistics aggregated from matches
    /// </summary>
    public class TeamStatistics
    {
        public string Team { get; set; } = "";
        public string TeamNormalized { get; set; } = "";
        public int MatchesPlayed { get; set; }
        public int Wins { get; set; }
        public int Draws { get; set; }
        public int Losses { get; set; }
        public int GoalsFor { get; set; }
        public int GoalsAgainst { get; set; }
        public int GoalDifference => GoalsFor - GoalsAgainst;
        public double WinRate => MatchesPlayed > 0 ? (double)Wins / MatchesPlayed * 100 : 0;
        public double PointsPerMatch => MatchesPlayed > 0 ? (Wins * 3.0 + Draws) / MatchesPlayed : 0;
        
        // Competition-specific
        public Dictionary<string, TeamStatistics> ByCompetition { get; set; } = new Dictionary<string, TeamStatistics>();
        public Dictionary<int, TeamStatistics> BySeason { get; set; } = new Dictionary<int, TeamStatistics>();
        
        // Home/Away split
        public TeamStatistics HomeStats { get; set; } = null!;
        public TeamStatistics AwayStats { get; set; } = null!;
        
        public override string ToString()
        {
            return $"{TeamNormalized}: {Wins}W {Draws}D {Losses}L, GF:{GoalsFor} GA:{GoalsAgainst} GD:{GoalDifference}";
        }
    }
    
    /// <summary>
    /// Head-to-head record between two teams
    /// </summary>
    public class HeadToHeadRecord
    {
        public string Team1 { get; set; } = "";
        public string Team2 { get; set; } = "";
        public int Matches { get; set; }
        public int Team1Wins { get; set; }
        public int Team2Wins { get; set; }
        public int Draws { get; set; }
        public int Team1Goals { get; set; }
        public int Team2Goals { get; set; }
        
        public double Team1WinRate => Matches > 0 ? (double)Team1Wins / Matches * 100 : 0;
        public double Team2WinRate => Matches > 0 ? (double)Team2Wins / Matches * 100 : 0;
        
        public override string ToString()
        {
            return $"{Team1} vs {Team2}: {Team1Wins}-{Draws}-{Team2Wins} ({Team1Goals}-{Team2Goals})";
        }
    }
    
    /// <summary>
    /// Helper for team name normalization
    /// </summary>
    public static class TeamNormalizer
    {
        private static readonly Dictionary<string, string> _teamMapping = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            // Map variations to canonical names
            { "Flamengo-RJ", "Flamengo" },
            { "Flamengo", "Flamengo" },
            { "CR Flamengo", "Flamengo" },
            { "Clube de Regatas do Flamengo", "Flamengo" },
            
            { "Palmeiras-SP", "Palmeiras" },
            { "Palmeiras", "Palmeiras" },
            { "Sociedade Esportiva Palmeiras", "Palmeiras" },
            
            { "Corinthians-SP", "Corinthians" },
            { "Corinthians", "Corinthians" },
            { "Sport Club Corinthians Paulista", "Corinthians" },
            
            { "São Paulo-SP", "São Paulo" },
            { "São Paulo", "São Paulo" },
            { "Sao Paulo-SP", "São Paulo" },
            { "Sao Paulo", "São Paulo" },
            
            { "Santos-SP", "Santos" },
            { "Santos", "Santos" },
            { "Santos FC", "Santos" },
            
            { "Grêmio-RS", "Grêmio" },
            { "Grêmio", "Grêmio" },
            { "Gremio-RS", "Grêmio" },
            { "Gremio", "Grêmio" },
            
            { "Internacional-RS", "Internacional" },
            { "Internacional", "Internacional" },
            { "SC Internacional", "Internacional" },
            
            { "Fluminense-RJ", "Fluminense" },
            { "Fluminense", "Fluminense" },
            { "Fluminense Football Club", "Fluminense" },
            
            { "Atlético-MG", "Atlético Mineiro" },
            { "Atletico-MG", "Atlético Mineiro" },
            { "Atlético Mineiro", "Atlético Mineiro" },
            { "Atletico Mineiro", "Atlético Mineiro" },
            
            { "Cruzeiro-MG", "Cruzeiro" },
            { "Cruzeiro", "Cruzeiro" },
            { "Cruzeiro EC", "Cruzeiro" },
            
            { "Vasco da Gama-RJ", "Vasco da Gama" },
            { "Vasco da Gama", "Vasco da Gama" },
            { "CR Vasco da Gama", "Vasco da Gama" },
            
            { "Botafogo-RJ", "Botafogo" },
            { "Botafogo", "Botafogo" },
            { "Botafogo FR", "Botafogo" },
            
            { "Bahia-BA", "Bahia" },
            { "Bahia", "Bahia" },
            { "EC Bahia", "Bahia" },
            
            { "Sport-PE", "Sport Recife" },
            { "Sport Recife", "Sport Recife" },
            { "Sport Club do Recife", "Sport Recife" },
            
            { "Fortaleza Esporte Clube", "Fortaleza" },
            { "Fortaleza", "Fortaleza" },
            { "Fortaleza EC", "Fortaleza" },
            
            { "Ceará", "Ceará" },
            { "Ceará SC", "Ceará" },
            
            { "Athletico-PR", "Athletico Paranaense" },
            { "Athletico Paranaense", "Athletico Paranaense" },
            { "Atlético-PR", "Athletico Paranaense" },
            { "Atlético Paranaense", "Athletico Paranaense" },
            
            { "Goiás", "Goiás" },
            { "Goiás EC", "Goiás" },
        };
        
        /// <summary>
        /// Normalize team name to canonical form
        /// </summary>
        public static string Normalize(string teamName)
        {
            if (string.IsNullOrWhiteSpace(teamName))
                return teamName;
            
            // Remove common suffixes
            var normalized = teamName.Trim();
            
            // Check mapping first
            if (_teamMapping.TryGetValue(normalized, out var mapped))
                return mapped;
            
            // Remove state suffix (e.g., -SP, -RJ, -MG)
            var suffixMatch = Regex.Match(normalized, @"^(.*?)(?:[-–]\s*[A-Z]{2}|\s*\([^)]+\))$");
            if (suffixMatch.Success)
            {
                var baseName = suffixMatch.Groups[1].Value.Trim();
                if (_teamMapping.TryGetValue(baseName, out mapped))
                    return mapped;
                return baseName;
            }
            
            // Remove common club designations
            normalized = Regex.Replace(normalized, @"\s*(?:Sport Club|Esporte Clube|Clube de Regatas|FC|SC|EC)\s*", " ", RegexOptions.IgnoreCase);
            normalized = normalized.Trim();
            
            if (_teamMapping.TryGetValue(normalized, out mapped))
                return mapped;
            
            return normalized;
        }
        
        /// <summary>
        /// Extract state abbreviation from team name
        /// </summary>
        public static string ExtractState(string teamName)
        {
            if (string.IsNullOrWhiteSpace(teamName))
                return "";
            
            var match = Regex.Match(teamName, @"[-–]\s*([A-Z]{2})($|\s|\))");
            if (match.Success)
                return match.Groups[1].Value;
            
            return "";
        }
    }
    
    /// <summary>
    /// Competition types
    /// </summary>
    public enum CompetitionType
    {
        Brasileirao,
        CopaDoBrasil,
        Libertadores,
        Other
    }
    
    /// <summary>
    /// Represents a competition standing
    /// </summary>
    public class CompetitionStanding
    {
        public string Team { get; set; } = "";
        public int Position { get; set; }
        public int Played { get; set; }
        public int Wins { get; set; }
        public int Draws { get; set; }
        public int Losses { get; set; }
        public int GoalsFor { get; set; }
        public int GoalsAgainst { get; set; }
        public int GoalDifference => GoalsFor - GoalsAgainst;
        public int Points => Wins * 3 + Draws;
        
        public override string ToString()
        {
            return $"{Position}. {Team}: {Points} pts ({Wins}-{Draws}-{Losses}, GD:{GoalDifference})";
        }
    }
}