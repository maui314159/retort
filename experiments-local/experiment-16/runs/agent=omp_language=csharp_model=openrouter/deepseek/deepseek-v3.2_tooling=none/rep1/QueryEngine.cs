using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace BrazilianSoccerMCP
{
    /// <summary>
    /// Query engine for Brazilian soccer data
    /// </summary>
    public class QueryEngine
    {
        private List<SoccerMatch> _matches = new List<SoccerMatch>();
        private List<SoccerPlayer> _players = new List<SoccerPlayer>();
        private bool _initialized = false;
        private Dictionary<string, TeamStatistics> _teamStatsCache = new Dictionary<string, TeamStatistics>();
        
        public void Initialize(List<SoccerMatch> matches, List<SoccerPlayer> players)
        {
            _matches = matches;
            _players = players;
            _initialized = true;
            BuildTeamStatsCache();
        }
        
        private void BuildTeamStatsCache()
        {
            _teamStatsCache.Clear();
            
            foreach (var match in _matches)
            {
                UpdateTeamStats(match, match.HomeTeamNormalized, match.HomeGoals, match.AwayGoals, true);
                UpdateTeamStats(match, match.AwayTeamNormalized, match.AwayGoals, match.HomeGoals, false);
            }
        }
        
        private void UpdateTeamStats(SoccerMatch match, string team, int goalsFor, int goalsAgainst, bool isHome)
        {
            if (string.IsNullOrEmpty(team))
                return;
            
            if (!_teamStatsCache.ContainsKey(team))
            {
                _teamStatsCache[team] = new TeamStatistics
                {
                    Team = team,
                    TeamNormalized = team,
                    HomeStats = new TeamStatistics(),
                    AwayStats = new TeamStatistics()
                };
            }
            
            var stats = _teamStatsCache[team];
            stats.MatchesPlayed++;
            stats.GoalsFor += goalsFor;
            stats.GoalsAgainst += goalsAgainst;
            
            if (goalsFor > goalsAgainst)
                stats.Wins++;
            else if (goalsFor < goalsAgainst)
                stats.Losses++;
            else
                stats.Draws++;
            
            // Update home/away split
            var splitStats = isHome ? stats.HomeStats : stats.AwayStats;
            if (splitStats == null)
            {
                splitStats = new TeamStatistics();
                if (isHome) stats.HomeStats = splitStats;
                else stats.AwayStats = splitStats;
            }
            splitStats.MatchesPlayed++;
            splitStats.GoalsFor += goalsFor;
            splitStats.GoalsAgainst += goalsAgainst;
            
            if (goalsFor > goalsAgainst)
                splitStats.Wins++;
            else if (goalsFor < goalsAgainst)
                splitStats.Losses++;
            else
                splitStats.Draws++;
            
            // Update by competition
            if (!stats.ByCompetition.ContainsKey(match.Competition))
            {
                stats.ByCompetition[match.Competition] = new TeamStatistics();
            }
            var compStats = stats.ByCompetition[match.Competition];
            compStats.MatchesPlayed++;
            compStats.GoalsFor += goalsFor;
            {
                stats.BySeason[match.Season] = new TeamStatistics();
            }
            var seasonStats = stats.BySeason[match.Season];
            seasonStats.MatchesPlayed++;
            seasonStats.GoalsFor += goalsFor;
            seasonStats.GoalsAgainst += goalsAgainst;
            if (goalsFor > goalsAgainst)
                seasonStats.Wins++;
            else if (goalsFor < goalsAgainst)
                seasonStats.Losses++;
            else
                seasonStats.Draws++;
        }
        
        public string SearchMatches(Dictionary<string, object> arguments)
        {
            if (!_initialized)
                return "Error: Query engine not initialized";
            
            var matches = _matches.AsEnumerable();
            
            // Apply filters
            if (arguments.TryGetValue("team", out var teamObj) && teamObj is string team)
            {
                var normalized = TeamNormalizer.Normalize(team);
                matches = matches.Where(m => 
                    m.HomeTeamNormalized.Contains(normalized, StringComparison.OrdinalIgnoreCase) ||
                    m.AwayTeamNormalized.Contains(normalized, StringComparison.OrdinalIgnoreCase));
            }
            
            if (arguments.TryGetValue("homeTeam", out var homeTeamObj) && homeTeamObj is string homeTeam)
            {
                var normalized = TeamNormalizer.Normalize(homeTeam);
                matches = matches.Where(m => 
                    m.HomeTeamNormalized.Contains(normalized, StringComparison.OrdinalIgnoreCase));
            }
            
            if (arguments.TryGetValue("awayTeam", out var awayTeamObj) && awayTeamObj is string awayTeam)
            {
                var normalized = TeamNormalizer.Normalize(awayTeam);
                matches = matches.Where(m => 
                    m.AwayTeamNormalized.Contains(normalized, StringComparison.OrdinalIgnoreCase));
            }
            
            if (arguments.TryGetValue("team1", out var team1Obj) && team1Obj is string team1 &&
                arguments.TryGetValue("team2", out var team2Obj) && team2Obj is string team2)
            {
                var normalized1 = TeamNormalizer.Normalize(team1);
                var normalized2 = TeamNormalizer.Normalize(team2);
                
                matches = matches.Where(m => 
                    (m.HomeTeamNormalized.Contains(normalized1) && m.AwayTeamNormalized.Contains(normalized2)) ||
                    (m.HomeTeamNormalized.Contains(normalized2) && m.AwayTeamNormalized.Contains(normalized1)));
            }
            
            if (arguments.TryGetValue("startDate", out var startDateObj) && startDateObj is string startDateStr &&
                DateTime.TryParse(startDateStr, out var startDate))
            {
                matches = matches.Where(m => m.Date >= startDate);
            }
            
            if (arguments.TryGetValue("endDate", out var endDateObj) && endDateObj is string endDateStr &&
                DateTime.TryParse(endDateStr, out var endDate))
            {
                matches = matches.Where(m => m.Date <= endDate);
            }
            
            if (arguments.TryGetValue("competition", out var competitionObj) && competitionObj is string competition)
            {
                if (competition != "All")
                {
                    matches = matches.Where(m => m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase));
                }
            }
            
            if (arguments.TryGetValue("season", out var seasonObj) && seasonObj is int season)
            {
                matches = matches.Where(m => m.Season == season);
            }
            
            var limit = 20;
            if (arguments.TryGetValue("limit", out var limitObj) && limitObj is int limitValue)
            {
                limit = limitValue;
            }
            
            var resultMatches = matches.OrderByDescending(m => m.Date).Take(limit).ToList();
            
            var sb = new StringBuilder();
            
            if (arguments.TryGetValue("team1", out var t1) && arguments.TryGetValue("team2", out var t2))
            {
                var team1Name = TeamNormalizer.Normalize(t1 as string ?? "");
                var team2Name = TeamNormalizer.Normalize(t2 as string ?? "");
                sb.AppendLine($"{team1Name} vs {team2Name} (head-to-head):");
            }
            else
            {
                sb.AppendLine("Matches found:");
            }
            
            sb.AppendLine();
            
            if (resultMatches.Count == 0)
            {
                sb.AppendLine("No matches found.");
                return sb.ToString();
            }
            
            foreach (var match in resultMatches)
            {
                sb.AppendLine($"- {match.Date:yyyy-MM-dd}: {match.HomeTeamNormalized} {match.HomeGoals}-{match.AwayGoals} {match.AwayTeamNormalized}");
                sb.AppendLine($"  Competition: {match.Competition}, Season: {match.Season}, Round: {match.Round}");
                
                if (!string.IsNullOrEmpty(match.Stage))
                    sb.AppendLine($"  Stage: {match.Stage}");
                    
                if (!string.IsNullOrEmpty(match.Stadium))
                    sb.AppendLine($"  Stadium: {match.Stadium}");
                    
                sb.AppendLine();
            }
            
            sb.AppendLine($"Total matches in dataset: {resultMatches.Count} (showing up to {limit})");
            
            return sb.ToString();
        }
        
        public string GetTeamStats(Dictionary<string, object> arguments)
        {
            if (!_initialized)
                return "Error: Query engine not initialized";
            
            if (!arguments.TryGetValue("team", out var teamObj) || teamObj is not string team)
                return "Error: 'team' parameter is required";
            
            var normalized = TeamNormalizer.Normalize(team);
            
            if (!_teamStatsCache.TryGetValue(normalized, out var stats))
                return $"Error: Team '{team}' not found in dataset";
            
            var season = arguments.TryGetValue("season", out var seasonObj) && seasonObj is int s ? s : (int?)null;
            var competition = arguments.TryGetValue("competition", out var compObj) && compObj is string c ? c : null;
            
            var includeHomeAway = true;
            if (arguments.TryGetValue("includeHomeAway", out var homeAwayObj) && homeAwayObj is bool b)
                includeHomeAway = b;
            
            var sb = new StringBuilder();
            
            if (season.HasValue && stats.BySeason.ContainsKey(season.Value))
            {
                var seasonStats = stats.BySeason[season.Value];
                sb.AppendLine($"{normalized} - Season {season.Value}:");
                sb.AppendLine($"  Matches: {seasonStats.MatchesPlayed}");
                sb.AppendLine($"  Wins: {seasonStats.Wins}, Draws: {seasonStats.Draws}, Losses: {seasonStats.Losses}");
                sb.AppendLine($"  Goals For: {seasonStats.GoalsFor}, Goals Against: {seasonStats.GoalsAgainst}, GD: {seasonStats.GoalDifference}");
                sb.AppendLine($"  Win Rate: {seasonStats.WinRate:F1}%");
                sb.AppendLine();
            }
            else if (!string.IsNullOrEmpty(competition) && stats.ByCompetition.ContainsKey(competition))
            {
                var compStats = stats.ByCompetition[competition];
                sb.AppendLine($"{normalized} - {competition} (all seasons):");
                sb.AppendLine($"  Matches: {compStats.MatchesPlayed}");
                sb.AppendLine($"  Wins: {compStats.Wins}, Draws: {compStats.Draws}, Losses: {compStats.Losses}");
                sb.AppendLine($"  Goals For: {compStats.GoalsFor}, Goals Against: {compStats.GoalsAgainst}, GD: {compStats.GoalDifference}");
                sb.AppendLine($"  Win Rate: {compStats.WinRate:F1}%");
                sb.AppendLine();
            }
            else
            {
                sb.AppendLine($"{normalized} - All competitions (all seasons):");
                sb.AppendLine($"  Matches: {stats.MatchesPlayed}");
                sb.AppendLine($"  Wins: {stats.Wins}, Draws: {stats.Draws}, Losses: {stats.Losses}");
                sb.AppendLine($"  Goals For: {stats.GoalsFor}, Goals Against: {stats.GoalsAgainst}, GD: {stats.GoalDifference}");
                sb.AppendLine($"  Win Rate: {stats.WinRate:F1}%");
                sb.AppendLine();
                
                // Show by competition
                if (stats.ByCompetition.Count > 0)
                {
                    sb.AppendLine("By competition:");
                    foreach (var kvp in stats.ByCompetition.OrderByDescending(c => c.Value.MatchesPlayed))
                    {
                        var comp = kvp.Value;
                        if (comp.MatchesPlayed > 0)
                        {
                            sb.AppendLine($"  {kvp.Key}: {comp.Wins}-{comp.Draws}-{comp.Losses} (GF:{comp.GoalsFor}, GA:{comp.GoalsAgainst})");
                        }
                    }
                    sb.AppendLine();
                }
                
                // Show recent seasons
                var recentSeasons = stats.BySeason.OrderByDescending(s => s.Key).Take(5).ToList();
                if (recentSeasons.Count > 0)
                {
                    sb.AppendLine("Recent seasons:");
                    foreach (var kvp in recentSeasons)
                    {
                        var seasonStats = kvp.Value;
                        sb.AppendLine($"  {kvp.Key}: {seasonStats.Wins}-{seasonStats.Draws}-{seasonStats.Losses} (GF:{seasonStats.GoalsFor}, GA:{seasonStats.GoalsAgainst})");
                    }
                    sb.AppendLine();
                }
            }
            
            if (includeHomeAway)
            {
                sb.AppendLine("Home/Away split:");
                sb.AppendLine($"  Home: {stats.HomeStats.Wins}-{stats.HomeStats.Draws}-{stats.HomeStats.Losses} (GF:{stats.HomeStats.GoalsFor}, GA:{stats.HomeStats.GoalsAgainst})");
                sb.AppendLine($"  Away: {stats.AwayStats.Wins}-{stats.AwayStats.Draws}-{stats.AwayStats.Losses} (GF:{stats.AwayStats.GoalsFor}, GA:{stats.AwayStats.GoalsAgainst})");
                sb.AppendLine();
            }
            
            return sb.ToString();
        }
        
        public string SearchPlayers(Dictionary<string, object> arguments)
        {
            if (!_initialized)
                return "Error: Query engine not initialized";
            
            var players = _players.AsEnumerable();
            
            if (arguments.TryGetValue("name", out var nameObj) && nameObj is string name)
            {
                players = players.Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));
            }
            
            if (arguments.TryGetValue("nationality", out var nationalityObj) && nationalityObj is string nationality)
            {
                players = players.Where(p => p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));
            }
            
            if (arguments.TryGetValue("club", out var clubObj) && clubObj is string club)
            {
                players = players.Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));
            }
            
            if (arguments.TryGetValue("position", out var positionObj) && positionObj is string position)
            {
                players = players.Where(p => p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));
            }
            
            if (arguments.TryGetValue("minRating", out var minRatingObj) && minRatingObj is int minRating)
            {
                players = players.Where(p => p.Overall >= minRating);
            }
            
            if (arguments.TryGetValue("maxRating", out var maxRatingObj) && maxRatingObj is int maxRating)
            {
                players = players.Where(p => p.Overall <= maxRating);
            }
            
            var limit = 20;
            if (arguments.TryGetValue("limit", out var limitObj) && limitObj is int limitValue)
            {
                limit = limitValue;
            }
            
            var resultPlayers = players.OrderByDescending(p => p.Overall).Take(limit).ToList();
            
            var sb = new StringBuilder();
            
            sb.AppendLine($"Players found: {resultPlayers.Count} (showing up to {limit})");
            sb.AppendLine();
            
            foreach (var player in resultPlayers)
            {
                sb.AppendLine($"- {player.Name} ({player.Overall}) - {player.Position}");
                sb.AppendLine($"  Club: {player.Club}, Nationality: {player.Nationality}, Age: {player.Age}");
                sb.AppendLine($"  Potential: {player.Potential}, Jersey: {player.JerseyNumber}, Height: {player.Height}, Weight: {player.Weight}");
                
                if (player.Skills.Any())
                {
                    var topSkills = player.Skills.OrderByDescending(s => s.Value).Take(3).ToList();
                    sb.AppendLine($"  Top skills: {string.Join(", ", topSkills.Select(s => $"{s.Key}: {s.Value}"))}");
                }
                
                sb.AppendLine();
            }
            
            return sb.ToString();
        }
        
        public string GetCompetitionStandings(Dictionary<string, object> arguments)
        {
            if (!_initialized)
                return "Error: Query engine not initialized";
            
            if (!arguments.TryGetValue("competition", out var competitionObj) || competitionObj is not string competition)
                return "Error: 'competition' parameter is required";
            
            if (!arguments.TryGetValue("season", out var seasonObj) || seasonObj is not int season)
                return "Error: 'season' parameter is required";
            
            var limit = 0; // 0 means all
            if (arguments.TryGetValue("limit", out var limitObj) && limitObj is int limitValue)
            {
                limit = limitValue;
            }
            
            // Get matches for this competition and season
            var competitionMatches = _matches.Where(m => 
                m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase) && 
                m.Season == season).ToList();
            
            if (competitionMatches.Count == 0)
                return $"No matches found for {competition} season {season}";
            
            // Calculate standings
            var standings = new Dictionary<string, CompetitionStanding>();
            
            foreach (var match in competitionMatches)
            {
                UpdateStanding(standings, match.HomeTeamNormalized, 
                    match.HomeGoals, match.AwayGoals, true);
                UpdateStanding(standings, match.AwayTeamNormalized, 
                    match.AwayGoals, match.HomeGoals, false);
            }
            
            var sortedStandings = standings.Values
                .OrderByDescending(s => s.Points)
                .ThenByDescending(s => s.GoalDifference)
                .ThenByDescending(s => s.GoalsFor)
                .ThenBy(s => s.Team)
                .ToList();
            
            if (limit > 0 && limit < sortedStandings.Count)
                sortedStandings = sortedStandings.Take(limit).ToList();
            
            var sb = new StringBuilder();
            sb.AppendLine($"{competition} - Season {season} Standings:");
            sb.AppendLine();
            
            for (int i = 0; i < sortedStandings.Count; i++)
            {
                var standing = sortedStandings[i];
                standing.Position = i + 1;
                sb.AppendLine($"{standing.Position,2}. {standing.Team,-25} {standing.Points,3} pts ({standing.Wins}-{standing.Draws}-{standing.Losses}) GD:{standing.GoalDifference:+0;-#} GF:{standing.GoalsFor} GA:{standing.GoalsAgainst}");
            }
            
            sb.AppendLine();
            sb.AppendLine($"Total teams: {sortedStandings.Count}, Total matches: {competitionMatches.Count}");
            
            return sb.ToString();
        }
        
        private void UpdateStanding(Dictionary<string, CompetitionStanding> standings, string team, 
            int goalsFor, int goalsAgainst, bool isHome)
        {
            if (!standings.ContainsKey(team))
            {
                standings[team] = new CompetitionStanding
                {
                    Team = team
                };
            }
            
            var standing = standings[team];
            standing.Played++;
            standing.GoalsFor += goalsFor;
            standing.GoalsAgainst += goalsAgainst;
            
            if (goalsFor > goalsAgainst)
                standing.Wins++;
            else if (goalsFor < goalsAgainst)
                standing.Losses++;
            else
                standing.Draws++;
        }
        
        public string GetHeadToHead(Dictionary<string, object> arguments)
        {
            if (!_initialized)
                return "Error: Query engine not initialized";
            
            if (!arguments.TryGetValue("team1", out var team1Obj) || team1Obj is not string team1)
                return "Error: 'team1' parameter is required";
            
            if (!arguments.TryGetValue("team2", out var team2Obj) || team2Obj is not string team2)
                return "Error: 'team2' parameter is required";
            
            var normalized1 = TeamNormalizer.Normalize(team1);
            var normalized2 = TeamNormalizer.Normalize(team2);
            
            // Get matches between these teams
            var matches = _matches.Where(m => 
                (m.HomeTeamNormalized.Contains(normalized1) && m.AwayTeamNormalized.Contains(normalized2)) ||
                (m.HomeTeamNormalized.Contains(normalized2) && m.AwayTeamNormalized.Contains(normalized1))).ToList();
            
            // Apply optional filters
            if (arguments.TryGetValue("competition", out var competitionObj) && competitionObj is string competition)
            {
                matches = matches.Where(m => m.Competition.Contains(competition)).ToList();
            }
            
            if (arguments.TryGetValue("startDate", out var startDateObj) && startDateObj is string startDateStr &&
                DateTime.TryParse(startDateStr, out var startDate))
            {
                matches = matches.Where(m => m.Date >= startDate).ToList();
            }
            
            if (arguments.TryGetValue("endDate", out var endDateObj) && endDateObj is string endDateStr &&
                DateTime.TryParse(endDateStr, out var endDate))
            {
                matches = matches.Where(m => m.Date <= endDate).ToList();
            }
            
            // Calculate head-to-head
            var record = new HeadToHeadRecord
            {
                Team1 = normalized1,
                Team2 = normalized2
            };
            
            foreach (var match in matches)
            {
                record.Matches++;
                
                var isTeam1Home = match.HomeTeamNormalized.Contains(normalized1);
                var team1Goals = isTeam1Home ? match.HomeGoals : match.AwayGoals;
                var team2Goals = isTeam1Home ? match.AwayGoals : match.HomeGoals;
                
                record.Team1Goals += team1Goals;
                record.Team2Goals += team2Goals;
                
                if (team1Goals > team2Goals)
                    record.Team1Wins++;
                else if (team1Goals < team2Goals)
                    record.Team2Wins++;
                else
                    record.Draws++;
            }
            
            var sb = new StringBuilder();
            sb.AppendLine($"{normalized1} vs {normalized2} - Head-to-head record:");
            sb.AppendLine();
            sb.AppendLine($"Total matches: {record.Matches}");
            sb.AppendLine($"{normalized1} wins: {record.Team1Wins} ({record.Team1WinRate:F1}%)");
            sb.AppendLine($"{normalized2} wins: {record.Team2Wins} ({record.Team2WinRate:F1}%)");
            sb.AppendLine($"Draws: {record.Draws} ({(record.Matches > 0 ? (double)record.Draws / record.Matches * 100 : 0):F1}%)");
            sb.AppendLine($"Goals: {normalized1} {record.Team1Goals}-{record.Team2Goals} {normalized2}");
            sb.AppendLine();
            
            // Show recent matches
            var recentMatches = matches.OrderByDescending(m => m.Date).Take(10).ToList();
            if (recentMatches.Count > 0)
            {
                sb.AppendLine("Recent matches:");
                foreach (var match in recentMatches)
                {
                    var isTeam1Home = match.HomeTeamNormalized.Contains(normalized1);
                    var team1Goals = isTeam1Home ? match.HomeGoals : match.AwayGoals;
                    var team2Goals = isTeam1Home ? match.AwayGoals : match.HomeGoals;
                    
                    sb.AppendLine($"  {match.Date:yyyy-MM-dd}: {match.HomeTeamNormalized} {match.HomeGoals}-{match.AwayGoals} {match.AwayTeamNormalized}");
                    sb.AppendLine($"    Competition: {match.Competition}, Season: {match.Season}, Winner: {match.Winner}");
                }
            }
            
            return sb.ToString();
        }
        
        public string GetStatistics(Dictionary<string, object> arguments)
        {
            if (!_initialized)
                return "Error: Query engine not initialized";
            
            if (!arguments.TryGetValue("statistic", out var statObj) || statObj is not string statistic)
                return "Error: 'statistic' parameter is required";
            
            var competitionFilter = arguments.TryGetValue("competition", out var compObj) && compObj is string comp ? comp : null;
            var seasonFilter = arguments.TryGetValue("season", out var seasonObj) && seasonObj is int season ? season : (int?)null;
            var limit = arguments.TryGetValue("limit", out var limitObj) && limitObj is int limitValue ? limitValue : 10;
            
            var filteredMatches = _matches.AsEnumerable();
            if (!string.IsNullOrEmpty(competitionFilter))
                filteredMatches = filteredMatches.Where(m => m.Competition.Contains(competitionFilter));
            if (seasonFilter.HasValue)
                filteredMatches = filteredMatches.Where(m => m.Season == seasonFilter.Value);
            
            var matches = filteredMatches.ToList();
            
            var sb = new StringBuilder();
            
            switch (statistic)
            {
                case "average_goals":
                    var avgGoals = matches.Average(m => m.TotalGoals);
                    sb.AppendLine($"Average goals per match: {avgGoals:F2}");
                    if (competitionFilter != null)
                        sb.AppendLine($"Competition: {competitionFilter}");
                    if (seasonFilter.HasValue)
                        sb.AppendLine($"Season: {seasonFilter.Value}");
                    break;
                    
                case "home_win_rate":
                    var homeWins = matches.Count(m => m.HomeGoals > m.AwayGoals);
                    var homeWinRate = matches.Count > 0 ? (double)homeWins / matches.Count * 100 : 0;
                    sb.AppendLine($"Home win rate: {homeWinRate:F1}% ({homeWins}/{matches.Count})");
                    break;
                    
                case "draw_rate":
                    var draws = matches.Count(m => m.HomeGoals == m.AwayGoals);
                    var drawRate = matches.Count > 0 ? (double)draws / matches.Count * 100 : 0;
                    sb.AppendLine($"Draw rate: {drawRate:F1}% ({draws}/{matches.Count})");
                    break;
                    
                case "biggest_wins":
                    var bigWins = matches.Where(m => m.HomeGoals != m.AwayGoals)
                                        .Select(m => new
                                        {
                                            Match = m,
                                            Margin = Math.Abs(m.HomeGoals - m.AwayGoals)
                                        })
                                        .OrderByDescending(x => x.Margin)
                                        .ThenByDescending(x => x.Match.TotalGoals)
                                        .Take(limit)
                                        .ToList();
                    
                    sb.AppendLine($"Biggest wins (by margin):");
                    foreach (var bigWin in bigWins)
                    {
                        sb.AppendLine($"  {bigWin.Match.Date:yyyy-MM-dd}: {bigWin.Match.HomeTeamNormalized} {bigWin.Match.HomeGoals}-{bigWin.Match.AwayGoals} {bigWin.Match.AwayTeamNormalized}");
                        sb.AppendLine($"    Competition: {bigWin.Match.Competition}, Season: {bigWin.Match.Season}, Margin: {bigWin.Margin} goals");
                    }
                    break;
                    
                case "most_common_score":
                    var scoreFrequency = matches
                        .GroupBy(m => $"{m.HomeGoals}-{m.AwayGoals}")
                        .Select(g => new { Score = g.Key, Count = g.Count() })
                        .OrderByDescending(x => x.Count)
                        .Take(limit)
                        .ToList();
                    
                    sb.AppendLine("Most common scores:");
                    foreach (var score in scoreFrequency)
                    {
                        sb.AppendLine($"  {score.Score}: {score.Count} matches");
                    }
                    break;
                    
                case "team_with_most_wins":
                    var teamWins = _teamStatsCache.Values
                        .OrderByDescending(t => t.Wins)
                        .Take(limit)
                        .ToList();
                    
                    sb.AppendLine("Teams with most wins:");
                    foreach (var team in teamWins)
                    {
                        sb.AppendLine($"  {team.Team}: {team.Wins} wins ({team.WinRate:F1}% win rate)");
                    }
                    break;
                    
                case "team_with_most_goals":
                    var teamGoals = _teamStatsCache.Values
                        .OrderByDescending(t => t.GoalsFor)
                        .Take(limit)
                        .ToList();
                    
                    sb.AppendLine("Teams with most goals:");
                    foreach (var team in teamGoals)
                    {
                        sb.AppendLine($"  {team.Team}: {team.GoalsFor} goals in {team.MatchesPlayed} matches (avg: {team.GoalsFor / (double)team.MatchesPlayed:F2})");
                    }
                    break;
                    
                case "top_scorers":
                    // Note: We don't have per-player goal data in the provided datasets
                    // This would require additional data or inference
                    sb.AppendLine("Goal scorer data is not available in the current datasets.");
                    sb.AppendLine("The FIFA player dataset does not contain goal statistics.");
                    break;
                    
                default:
                    return $"Error: Unknown statistic '{statistic}'";
            }
            
            return sb.ToString();
        }
        
        public string GetDataInfo(Dictionary<string, object> arguments)
        {
            if (!_initialized)
                return "Error: Query engine not initialized";
            
            if (!arguments.TryGetValue("info", out var infoObj) || infoObj is not string info)
                return "Error: 'info' parameter is required";
            
            var sb = new StringBuilder();
            
            switch (info)
            {
                case "summary":
                    sb.AppendLine("Brazilian Soccer MCP - Data Summary");
                    sb.AppendLine("====================================");
                    sb.AppendLine($"Matches loaded: {_matches.Count}");
                    sb.AppendLine($"Players loaded: {_players.Count}");
                    sb.AppendLine($"Unique teams: {_teamStatsCache.Count}");
                    sb.AppendLine($"Date range: {_matches.Min(m => m.Date):yyyy-MM-dd} to {_matches.Max(m => m.Date):yyyy-MM-dd}");
                    sb.AppendLine($"Seasons: {_matches.Select(m => m.Season).Distinct().Min()} to {_matches.Select(m => m.Season).Distinct().Max()}");
                    break;
                    
                case "teams":
                    var topTeams = _teamStatsCache.Values
                        .OrderByDescending(t => t.MatchesPlayed)
                        .Take(20)
                        .ToList();
                    
                    sb.AppendLine("Top 20 teams by matches played:");
                    foreach (var team in topTeams)
                    {
                        sb.AppendLine($"  {team.Team}: {team.MatchesPlayed} matches, {team.Wins}W {team.Draws}D {team.Losses}L, GF:{team.GoalsFor} GA:{team.GoalsAgainst}");
                    }
                    break;
                    
                case "competitions":
                    var competitions = _matches.GroupBy(m => m.Competition)
                                              .Select(g => new { Competition = g.Key, Count = g.Count() })
                                              .OrderByDescending(c => c.Count)
                                              .ToList();
                    
                    sb.AppendLine("Competitions in dataset:");
                    foreach (var comp in competitions)
                    {
                        sb.AppendLine($"  {comp.Competition}: {comp.Count} matches");
                    }
                    break;
                    
                case "seasons":
                    var seasons = _matches.GroupBy(m => m.Season)
                                         .Select(g => new { Season = g.Key, Count = g.Count() })
                                         .OrderBy(s => s.Season)
                                         .ToList();
                    
                    sb.AppendLine("Seasons in dataset:");
                    foreach (var season in seasons)
                    {
                        sb.AppendLine($"  {season.Season}: {season.Count} matches");
                    }
                    break;
                    
                case "player_count":
                    sb.AppendLine($"Total players: {_players.Count}");
                    sb.AppendLine($"Brazilian players: {_players.Count(p => p.IsBrazilian)}");
                    sb.AppendLine($"Players at Brazilian clubs: {_players.Count(p => p.PlaysForBrazilianClub)}");
                    
                    var topNationalities = _players.GroupBy(p => p.Nationality)
                                                  .Select(g => new { Nationality = g.Key, Count = g.Count() })
                                                  .OrderByDescending(n => n.Count)
                                                  .Take(10)
                                                  .ToList();
                    
                    sb.AppendLine("\nTop nationalities:");
                    foreach (var nat in topNationalities)
                    {
                        sb.AppendLine($"  {nat.Nationality}: {nat.Count} players");
                    }
                    break;
                    
                case "match_count":
                    sb.AppendLine($"Total matches: {_matches.Count}");
                    
                    var compBreakdown = _matches.GroupBy(m => m.Competition)
                                               .Select(g => new { Competition = g.Key, Count = g.Count() })
                                               .OrderByDescending(c => c.Count)
                                               .ToList();
                    
                    sb.AppendLine("\nBy competition:");
                    foreach (var comp in compBreakdown)
                    {
                        sb.AppendLine($"  {comp.Competition}: {comp.Count} matches");
                    }
                    break;
                    
                default:
                    return $"Error: Unknown info type '{info}'";
            }
            
            return sb.ToString();
        }
    }
}