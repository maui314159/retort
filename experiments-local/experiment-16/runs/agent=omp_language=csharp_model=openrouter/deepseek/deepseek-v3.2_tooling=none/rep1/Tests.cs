using System;
using System.Collections.Generic;
using System.Linq;

namespace BrazilianSoccerMCP.Tests
{
    /// <summary>
    /// BDD-style test scenarios for Brazilian Soccer MCP
    /// </summary>
    public class Tests
    {
        private readonly DataLoader _dataLoader;
        private readonly QueryEngine _queryEngine;
        private List<SoccerMatch> _matches = new List<SoccerMatch>();
        private List<SoccerPlayer> _players = new List<SoccerPlayer>();
        
        public Tests()
        {
            _dataLoader = new DataLoader();
            _queryEngine = new QueryEngine();
        }
        
        public void RunAllTests()
        {
            Console.WriteLine("Running Brazilian Soccer MCP Tests");
            Console.WriteLine("===================================");
            
            LoadData();
            
            TestMatchQueries();
            TestTeamQueries();
            TestPlayerQueries();
            TestCompetitionQueries();
            TestHeadToHead();
            TestStatistics();
            TestDataInfo();
            
            Console.WriteLine("\nAll tests completed!");
        }
        
        private void LoadData()
        {
            Console.WriteLine("\n1. Loading data...");
            _matches = _dataLoader.LoadMatches();
            _players = _dataLoader.LoadPlayers();
            _queryEngine.Initialize(_matches, _players);
            Console.WriteLine($"   Loaded {_matches.Count} matches and {_players.Count} players");
        }
        
        private void TestMatchQueries()
        {
            Console.WriteLine("\n2. Testing match queries...");
            
            // Scenario: Find matches between two teams
            Console.WriteLine("\n   Scenario: Find matches between Flamengo and Fluminense");
            var matches = _queryEngine.SearchMatches(new Dictionary<string, object>
            {
                ["team1"] = "Flamengo",
                ["team2"] = "Fluminense",
                ["limit"] = 5
            });
            Console.WriteLine(matches);
            
            // Scenario: Find matches by team
            Console.WriteLine("\n   Scenario: Find matches for Corinthians");
            matches = _queryEngine.SearchMatches(new Dictionary<string, object>
            {
                ["team"] = "Corinthians",
                ["limit"] = 3
            });
            Console.WriteLine(matches);
            
            // Scenario: Find matches by competition
            Console.WriteLine("\n   Scenario: Find Libertadores matches");
            matches = _queryEngine.SearchMatches(new Dictionary<string, object>
            {
                ["competition"] = "Libertadores",
                ["limit"] = 3
            });
            Console.WriteLine(matches);
        }
        
        private void TestTeamQueries()
        {
            Console.WriteLine("\n3. Testing team queries...");
            
            // Scenario: Get team statistics
            Console.WriteLine("\n   Scenario: Get statistics for Palmeiras");
            var stats = _queryEngine.GetTeamStats(new Dictionary<string, object>
            {
                ["team"] = "Palmeiras"
            });
            Console.WriteLine(stats);
            
            // Scenario: Get team statistics for specific season
            Console.WriteLine("\n   Scenario: Get statistics for Santos in 2019");
            stats = _queryEngine.GetTeamStats(new Dictionary<string, object>
            {
                ["team"] = "Santos",
                ["season"] = 2019
            });
            Console.WriteLine(stats);
        }
        
        private void TestPlayerQueries()
        {
            Console.WriteLine("\n4. Testing player queries...");
            
            // Scenario: Search for Brazilian players
            Console.WriteLine("\n   Scenario: Search for Brazilian players");
            var players = _queryEngine.SearchPlayers(new Dictionary<string, object>
            {
                ["nationality"] = "Brazil",
                ["limit"] = 5
            });
            Console.WriteLine(players);
            
            // Scenario: Search for players by name
            Console.WriteLine("\n   Scenario: Search for players named 'Neymar'");
            players = _queryEngine.SearchPlayers(new Dictionary<string, object>
            {
                ["name"] = "Neymar",
                ["limit"] = 3
            });
            Console.WriteLine(players);
            
            // Scenario: Search for high-rated players
            Console.WriteLine("\n   Scenario: Search for top-rated players");
            players = _queryEngine.SearchPlayers(new Dictionary<string, object>
            {
                ["minRating"] = 90,
                ["limit"] = 5
            });
            Console.WriteLine(players);
        }
        
        private void TestCompetitionQueries()
        {
            Console.WriteLine("\n5. Testing competition queries...");
            
            // Scenario: Get competition standings
            Console.WriteLine("\n   Scenario: Get Brasileirão 2019 standings");
            var standings = _queryEngine.GetCompetitionStandings(new Dictionary<string, object>
            {
                ["competition"] = "Brasileirão",
                ["season"] = 2019,
                ["limit"] = 5
            });
            Console.WriteLine(standings);
        }
        
        private void TestHeadToHead()
        {
            Console.WriteLine("\n6. Testing head-to-head queries...");
            
            // Scenario: Get head-to-head record
            Console.WriteLine("\n   Scenario: Get head-to-head between Flamengo and Corinthians");
            var h2h = _queryEngine.GetHeadToHead(new Dictionary<string, object>
            {
                ["team1"] = "Flamengo",
                ["team2"] = "Corinthians"
            });
            Console.WriteLine(h2h);
        }
        
        private void TestStatistics()
        {
            Console.WriteLine("\n7. Testing statistical analysis...");
            
            // Scenario: Get average goals
            Console.WriteLine("\n   Scenario: Get average goals per match");
            var stats = _queryEngine.GetStatistics(new Dictionary<string, object>
            {
                ["statistic"] = "average_goals"
            });
            Console.WriteLine(stats);
            
            // Scenario: Get home win rate
            Console.WriteLine("\n   Scenario: Get home win rate");
            stats = _queryEngine.GetStatistics(new Dictionary<string, object>
            {
                ["statistic"] = "home_win_rate"
            });
            Console.WriteLine(stats);
            
            // Scenario: Get biggest wins
            Console.WriteLine("\n   Scenario: Get biggest wins");
            stats = _queryEngine.GetStatistics(new Dictionary<string, object>
            {
                ["statistic"] = "biggest_wins",
                ["limit"] = 3
            });
            Console.WriteLine(stats);
        }
        
        private void TestDataInfo()
        {
            Console.WriteLine("\n8. Testing data information...");
            
            // Scenario: Get data summary
            Console.WriteLine("\n   Scenario: Get data summary");
            var info = _queryEngine.GetDataInfo(new Dictionary<string, object>
            {
                ["info"] = "summary"
            });
            Console.WriteLine(info);
            
            // Scenario: Get team list
            Console.WriteLine("\n   Scenario: Get top teams");
            info = _queryEngine.GetDataInfo(new Dictionary<string, object>
            {
                ["info"] = "teams"
            });
            // Show just first 5 lines
            var lines = info.Split('\n').Take(10);
            Console.WriteLine(string.Join("\n", lines));
        }
        
        public void TestSampleQueries()
        {
            Console.WriteLine("\nTesting Sample Questions from Specification");
            Console.WriteLine("===========================================");
            
            // Sample questions from TASK.md
            var sampleQueries = new Dictionary<string, Action>
            {
                ["Show me all Flamengo vs Fluminense matches"] = () =>
                {
                    Console.WriteLine("\nQ: Show me all Flamengo vs Fluminense matches");
                    var result = _queryEngine.SearchMatches(new Dictionary<string, object>
                    {
                        ["team1"] = "Flamengo",
                        ["team2"] = "Fluminense",
                        ["limit"] = 5
                    });
                    Console.WriteLine(result);
                },
                
                ["What matches did Palmeiras play in 2023?"] = () =>
                {
                    Console.WriteLine("\nQ: What matches did Palmeiras play in 2023?");
                    var result = _queryEngine.SearchMatches(new Dictionary<string, object>
                    {
                        ["team"] = "Palmeiras",
                        ["season"] = 2023,
                        ["limit"] = 5
                    });
                    Console.WriteLine(result);
                },
                
                ["What is Corinthians' home record in 2022?"] = () =>
                {
                    Console.WriteLine("\nQ: What is Corinthians' home record in 2022?");
                    var result = _queryEngine.GetTeamStats(new Dictionary<string, object>
                    {
                        ["team"] = "Corinthians",
                        ["season"] = 2022
                    });
                    Console.WriteLine(result);
                },
                
                ["Find all Brazilian players in the dataset"] = () =>
                {
                    Console.WriteLine("\nQ: Find all Brazilian players in the dataset");
                    var result = _queryEngine.SearchPlayers(new Dictionary<string, object>
                    {
                        ["nationality"] = "Brazil",
                        ["limit"] = 5
                    });
                    Console.WriteLine(result);
                },
                
                ["Who are the highest-rated players at Flamengo?"] = () =>
                {
                    Console.WriteLine("\nQ: Who are the highest-rated players at Flamengo?");
                    var result = _queryEngine.SearchPlayers(new Dictionary<string, object>
                    {
                        ["club"] = "Flamengo",
                        ["limit"] = 5
                    });
                    Console.WriteLine(result);
                },
                
                ["Who won the 2019 Brasileirão?"] = () =>
                {
                    Console.WriteLine("\nQ: Who won the 2019 Brasileirão?");
                    var result = _queryEngine.GetCompetitionStandings(new Dictionary<string, object>
                    {
                        ["competition"] = "Brasileirão",
                        ["season"] = 2019,
                        ["limit"] = 3
                    });
                    Console.WriteLine(result);
                },
                
                ["What's the average goals per match in the Brasileirão?"] = () =>
                {
                    Console.WriteLine("\nQ: What's the average goals per match in the Brasileirão?");
                    var result = _queryEngine.GetStatistics(new Dictionary<string, object>
                    {
                        ["statistic"] = "average_goals",
                        ["competition"] = "Brasileirão"
                    });
                    Console.WriteLine(result);
                },
                
                ["Which team has the best home record?"] = () =>
                {
                    Console.WriteLine("\nQ: Which team has the best home record?");
                    // We'll get teams with highest home win rate
                    var teams = _matches.Select(m => m.HomeTeamNormalized).Distinct().ToList();
                    var homeRecords = new List<(string Team, int Wins, int Matches)>();
                    
                    foreach (var team in teams.Take(20)) // Sample 20 teams for performance
                    {
                        var homeMatches = _matches.Where(m => m.HomeTeamNormalized == team).ToList();
                        var homeWins = homeMatches.Count(m => m.HomeGoals > m.AwayGoals);
                        homeRecords.Add((team, homeWins, homeMatches.Count));
                    }
                    
                    var bestHome = homeRecords.OrderByDescending(r => r.Matches > 0 ? (double)r.Wins / r.Matches : 0).First();
                    Console.WriteLine($"{bestHome.Team}: {bestHome.Wins} wins in {bestHome.Matches} home matches ({(bestHome.Matches > 0 ? (double)bestHome.Wins / bestHome.Matches * 100 : 0):F1}% win rate)");
                }
            };
            
            foreach (var query in sampleQueries)
            {
                try
                {
                    query.Value();
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error: {ex.Message}");
                }
            }
        }
    }
}