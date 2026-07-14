using BrazilianSoccerMCP.Models;
using BrazilianSoccerMCP.Services;
using Xunit;

namespace BrazilianSoccerMCP.Tests;

/// <summary>
/// BDD-style integration tests for Brazilian Soccer MCP Server.
/// Tests all required capabilities: match queries, team stats, player search,
/// competition standings, statistical analysis, and team name normalization.
/// </summary>
public class BrazilianSoccerTests : IDisposable
{
    private readonly DataLoader _loader;
    private readonly MatchService _matchService;
    private readonly PlayerService _playerService;
    private readonly CompetitionService _competitionService;

    public BrazilianSoccerTests()
    {
        // Find data directory relative to test project
        var dataDir = Path.Combine(Directory.GetCurrentDirectory(), "data");
        if (!Directory.Exists(dataDir))
        {
            // Try going up from the test bin directory
            var baseDir = AppContext.BaseDirectory;
            for (int i = 0; i < 5; i++)
            {
                baseDir = Path.GetDirectoryName(baseDir)!;
                dataDir = Path.Combine(baseDir, "data");
                if (Directory.Exists(dataDir))
                    break;
            }
        }

        _loader = new DataLoader(dataDir);
        _loader.LoadAll();
        _matchService = new MatchService(_loader.AllMatches);
        _playerService = new PlayerService(_loader.Players);
        _competitionService = new CompetitionService(_loader.AllMatches);
    }

    public void Dispose() { }

    // ============================================================
    // Feature: Data Loading
    // ============================================================

    [Fact]
    [Trait("Feature", "Data Loading")]
    public void Scenario_All_datasets_loaded_successfully()
    {
        // Given the data directory exists
        // When the data loader runs
        // Then all datasets should have data
        Assert.True(_loader.AllMatches.Count > 0, "Should have loaded matches");
        Assert.True(_loader.Players.Count > 0, "Should have loaded players");
    }

    [Fact]
    [Trait("Feature", "Data Loading")]
    public void Scenario_Multiple_competitions_present()
    {
        var competitions = _matchService.GetCompetitions();
        Assert.Contains(competitions, c => c == "Brasileirão");
        Assert.Contains(competitions, c => c == "Copa do Brasil");
        Assert.Contains(competitions, c => c == "Copa Libertadores");
    }

    // ============================================================
    // Feature: Match Queries
    // ============================================================

    [Fact]
    [Trait("Feature", "Match Queries")]
    public void Scenario_Find_matches_between_two_teams()
    {
        // Given the match data is loaded
        // When I search for matches between Flamengo and Fluminense
        var matches = _matchService.SearchMatches(team: "Flamengo", opponent: "Fluminense",
            competition: null, season: null, fromDate: null, toDate: null, round: null, stage: null);

        // Then I should receive a list of matches
        Assert.NotEmpty(matches);

        // And each match should have date, scores, and competition
        foreach (var m in matches)
        {
            Assert.NotEqual(default(DateTime), m.Date);
            Assert.True(m.HomeGoal >= 0);
            Assert.True(m.AwayGoal >= 0);
            Assert.False(string.IsNullOrEmpty(m.Competition));
        }
    }

    [Fact]
    [Trait("Feature", "Match Queries")]
    public void Scenario_Find_matches_by_team_and_season()
    {
        // Given the match data is loaded
        // When I request matches for Palmeiras in season 2023
        var matches = _matchService.SearchMatches(team: "Palmeiras",
            competition: null, season: 2023, fromDate: null, toDate: null, opponent: null, round: null, stage: null);

        // Then I should receive matches
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(2023, m.Season));
        Assert.All(matches, m =>
        {
            bool isPalmeiras = TeamNameNormalizer.Matches(m.HomeTeam, "Palmeiras") ||
                               TeamNameNormalizer.Matches(m.AwayTeam, "Palmeiras");
            Assert.True(isPalmeiras);
        });
    }

    [Fact]
    [Trait("Feature", "Match Queries")]
    public void Scenario_Find_matches_by_competition()
    {
        // When I search for Copa do Brasil matches
        var matches = _matchService.SearchMatches(team: null, competition: "Copa do Brasil",
            season: null, fromDate: null, toDate: null, opponent: null, round: null, stage: null);

        // Then all matches should be Copa do Brasil
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal("Copa do Brasil", m.Competition));
    }

    [Fact]
    [Trait("Feature", "Match Queries")]
    public void Scenario_Find_matches_by_date_range()
    {
        var fromDate = new DateTime(2023, 1, 1);
        var toDate = new DateTime(2023, 12, 31);

        var matches = _matchService.SearchMatches(team: null, competition: null,
            season: null, fromDate: fromDate, toDate: toDate, opponent: null, round: null, stage: null);

        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.True(m.Date >= fromDate, $"Date {m.Date} should be >= {fromDate}");
            Assert.True(m.Date <= toDate, $"Date {m.Date} should be <= {toDate}");
        });
    }

    // ============================================================
    // Feature: Team Statistics
    // ============================================================

    [Fact]
    [Trait("Feature", "Team Statistics")]
    public void Scenario_Get_team_statistics()
    {
        // Given the match data is loaded
        // When I request statistics for Palmeiras in season 2023
        var stats = _matchService.GetTeamStats("Palmeiras", season: 2023);

        // Then I should receive wins, losses, draws, and goals
        Assert.True(stats.TotalMatches > 0);
        Assert.Equal(stats.Wins + stats.Draws + stats.Losses, stats.TotalMatches);
        Assert.True(stats.GoalsFor >= 0);
        Assert.True(stats.GoalsAgainst >= 0);
        Assert.True(stats.WinRate >= 0 && stats.WinRate <= 100);
    }

    [Fact]
    [Trait("Feature", "Team Statistics")]
    public void Scenario_Get_team_home_and_away_records()
    {
        var stats = _matchService.GetTeamStats("Corinthians", season: 2022);

        Assert.True(stats.HomeMatches > 0);
        Assert.True(stats.AwayMatches > 0);
        Assert.Equal(stats.HomeWins + stats.HomeDraws + stats.HomeLosses, stats.HomeMatches);
        Assert.Equal(stats.AwayWins + stats.AwayDraws + stats.AwayLosses, stats.AwayMatches);
    }

    [Fact]
    [Trait("Feature", "Team Statistics")]
    public void Scenario_Get_overall_team_stats_across_all_seasons()
    {
        var stats = _matchService.GetTeamStats("Flamengo");

        Assert.True(stats.TotalMatches > 100);
        Assert.True(stats.GoalsFor > stats.GoalsAgainst || stats.GoalsAgainst > 0);
    }

    // ============================================================
    // Feature: Head-to-Head
    // ============================================================

    [Fact]
    [Trait("Feature", "Head-to-Head")]
    public void Scenario_Compare_two_teams_head_to_head()
    {
        // Given the match data is loaded
        // When I compare Palmeiras and Santos head-to-head
        var h2h = _matchService.GetHeadToHead("Palmeiras", "Santos");

        // Then I should receive match history and statistics
        Assert.True(h2h.TotalMatches > 0);
        Assert.Equal(h2h.Team1Wins + h2h.Team2Wins + h2h.Draws, h2h.TotalMatches);

        // And match list should be populated
        Assert.NotEmpty(h2h.Matches);
    }

    [Fact]
    [Trait("Feature", "Head-to-Head")]
    public void Scenario_Head_to_head_has_competition_details()
    {
        var h2h = _matchService.GetHeadToHead("Flamengo", "Vasco");

        foreach (var m in h2h.Matches)
        {
            Assert.False(string.IsNullOrEmpty(m.Competition));
        }
    }

    // ============================================================
    // Feature: Player Queries
    // ============================================================

    [Fact]
    [Trait("Feature", "Player Queries")]
    public void Scenario_Search_Brazilian_players()
    {
        // Given the player data is loaded
        // When I search for Brazilian players
        var players = _playerService.SearchPlayers(nationality: "Brazil", limit: 50);

        // Then I should find many Brazilian players
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality));
    }

    [Fact]
    [Trait("Feature", "Player Queries")]
    public void Scenario_Find_players_by_club()
    {
        // When I search for players at Santos
        var players = _playerService.GetTopPlayersByClub("Santos");

        // Then I should find players
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Contains("Santos", p.Club, StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    [Trait("Feature", "Player Queries")]
    public void Scenario_Find_highest_rated_players()
    {
        var players = _playerService.SearchPlayers(minRating: 90, sortBy: "overall");

        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.True(p.Overall >= 90));
        // Should be sorted descending by overall
        for (int i = 1; i < players.Count; i++)
            Assert.True(players[i - 1].Overall >= players[i].Overall);
    }

    [Fact]
    [Trait("Feature", "Player Queries")]
    public void Scenario_Find_players_by_position()
    {
        var strikers = _playerService.SearchPlayers(position: "ST", nationality: "Brazil", limit: 20);

        Assert.NotEmpty(strikers);
        Assert.All(strikers, p =>
        {
            Assert.Equal("ST", p.Position);
            Assert.Equal("Brazil", p.Nationality);
        });
    }

    [Fact]
    [Trait("Feature", "Player Queries")]
    public void Scenario_Get_specific_player_by_name()
    {
        var player = _playerService.GetPlayerByName("Neymar");

        Assert.NotNull(player);
        Assert.Contains("Neymar", player.Name, StringComparison.OrdinalIgnoreCase);
        Assert.True(player.Overall > 0);
        Assert.False(string.IsNullOrEmpty(player.Club));
    }

    // ============================================================
    // Feature: Competition Queries
    // ============================================================

    [Fact]
    [Trait("Feature", "Competition Queries")]
    public void Scenario_Get_league_standings()
    {
        // Given the match data is loaded
        // When I request standings for Brasileirão 2019
        var standings = _competitionService.GetStandings("Brasileirão", 2019);

        // Then I should receive a properly ordered standings table
        Assert.NotEmpty(standings);

        // Standings should be ordered by points descending
        for (int i = 1; i < standings.Count; i++)
            Assert.True(standings[i - 1].Points >= standings[i].Points);

        // Each entry should have consistent data
        foreach (var s in standings)
        {
            Assert.Equal(s.Wins + s.Draws + s.Losses, s.Played);
            Assert.Equal(s.Wins * 3 + s.Draws, s.Points);
            Assert.Equal(s.GoalsFor - s.GoalsAgainst, s.GoalDifference);
        }
    }

    [Fact]
    [Trait("Feature", "Competition Queries")]
    public void Scenario_Get_champion()
    {
        var champion = _competitionService.GetChampion("Brasileirão", 2019);

        Assert.NotNull(champion);
        Assert.NotEmpty(champion);
    }

    [Fact]
    [Trait("Feature", "Competition Queries")]
    public void Scenario_Get_relegated_teams()
    {
        var relegated = _competitionService.GetRelegated("Brasileirão", 2019);

        Assert.NotEmpty(relegated);
        Assert.True(relegated.Count >= 2);
    }

    // ============================================================
    // Feature: Statistical Analysis
    // ============================================================

    [Fact]
    [Trait("Feature", "Statistical Analysis")]
    public void Scenario_Get_league_statistics()
    {
        // When I request aggregate league stats for Brasileirão
        var stats = _matchService.GetLeagueStats("Brasileirão");

        // Then I should receive meaningful statistics
        Assert.True(stats.TotalMatches > 0);
        Assert.True(stats.TotalGoals > 0);
        Assert.True(stats.AverageGoalsPerMatch > 0);
        Assert.True(stats.AverageGoalsPerMatch < 10);
        Assert.True(stats.HomeWinRate >= 0 && stats.HomeWinRate <= 100);
        Assert.True(stats.AwayWinRate >= 0 && stats.AwayWinRate <= 100);
        Assert.True(stats.DrawRate >= 0 && stats.DrawRate <= 100);
    }

    [Fact]
    [Trait("Feature", "Statistical Analysis")]
    public void Scenario_Get_biggest_wins()
    {
        var biggest = _matchService.GetBiggestWins(limit: 10);

        Assert.NotEmpty(biggest);
        Assert.Equal(10, biggest.Count);

        // Should be sorted by goal difference descending
        for (int i = 1; i < biggest.Count; i++)
            Assert.True(biggest[i - 1].GoalDiff >= biggest[i].GoalDiff);

        // First entry should have a significant goal difference
        Assert.True(biggest[0].GoalDiff >= 3);
    }

    [Fact]
    [Trait("Feature", "Statistical Analysis")]
    public void Scenario_Get_average_goals_per_match_per_season()
    {
        var stats2019 = _matchService.GetLeagueStats("Brasileirão", season: 2019);
        var stats2018 = _matchService.GetLeagueStats("Brasileirão", season: 2018);

        Assert.True(stats2019.TotalMatches > 0);
        Assert.True(stats2018.TotalMatches > 0);
        Assert.True(stats2019.AverageGoalsPerMatch > 0);
        Assert.True(stats2018.AverageGoalsPerMatch > 0);
    }

    // ============================================================
    // Feature: Team Name Normalization
    // ============================================================

    [Fact]
    [Trait("Feature", "Team Name Normalization")]
    public void Scenario_Normalize_team_names_with_state_suffix()
    {
        Assert.True(TeamNameNormalizer.Matches("Palmeiras-SP", "Palmeiras"));
        Assert.True(TeamNameNormalizer.Matches("Flamengo-RJ", "Flamengo"));
        Assert.True(TeamNameNormalizer.Matches("Corinthians", "Corinthians-SP"));
        Assert.True(TeamNameNormalizer.Matches("São Paulo-SP", "São Paulo"));
    }

    [Fact]
    [Trait("Feature", "Team Name Normalization")]
    public void Scenario_Normalize_team_names_with_special_characters()
    {
        Assert.True(TeamNameNormalizer.Matches("Grêmio", "Gremio"));
        Assert.True(TeamNameNormalizer.Matches("Gremio", "Grêmio"));
        Assert.True(TeamNameNormalizer.Matches("São Paulo", "Sao Paulo"));
        Assert.True(TeamNameNormalizer.Matches("América-MG", "America MG"));
    }

    [Fact]
    [Trait("Feature", "Team Name Normalization")]
    public void Scenario_Normalize_full_club_names()
    {
        Assert.True(TeamNameNormalizer.Matches("Sport Club Corinthians Paulista", "Corinthians"));
        Assert.True(TeamNameNormalizer.Matches("Corinthians", "Sport Club Corinthians Paulista"));
    }

    [Fact]
    [Trait("Feature", "Team Name Normalization")]
    public void Scenario_Normalize_team_names_with_parentheticals()
    {
        // Libertadores has teams like "Nacional (URU)"
        Assert.True(TeamNameNormalizer.Matches("Nacional (URU)", "Nacional"));
    }

    // ============================================================
    // Feature: Data Integrity
    // ============================================================

    [Fact]
    [Trait("Feature", "Data Integrity")]
    public void Scenario_All_matches_have_valid_scores()
    {
        foreach (var m in _loader.AllMatches)
        {
            Assert.True(m.HomeGoal >= 0, $"Home goal should be >= 0: {m.HomeTeam} vs {m.AwayTeam}");
            Assert.True(m.AwayGoal >= 0, $"Away goal should be >= 0: {m.HomeTeam} vs {m.AwayTeam}");
            Assert.False(string.IsNullOrEmpty(m.HomeTeam));
            Assert.False(string.IsNullOrEmpty(m.AwayTeam));
        }
    }

    [Fact]
    [Trait("Feature", "Data Integrity")]
    public void Scenario_All_matches_have_valid_dates()
    {
        foreach (var m in _loader.AllMatches)
        {
            Assert.True(m.Date.Year >= 1900 && m.Date.Year <= 2100,
                $"Invalid date {m.Date} for {m.HomeTeam} vs {m.AwayTeam}");
        }
    }

    [Fact]
    [Trait("Feature", "Data Integrity")]
    public void Scenario_Players_have_valid_ratings()
    {
        foreach (var p in _loader.Players)
        {
            Assert.True(p.Overall >= 0 && p.Overall <= 99);
            Assert.True(p.Potential >= 0 && p.Potential <= 99);
        }
    }

    // ============================================================
    // Feature: Cross-file Queries
    // ============================================================

    [Fact]
    [Trait("Feature", "Cross-file Queries")]
    public void Scenario_Team_appears_across_multiple_competitions()
    {
        var flamengoBrasileirao = _matchService.SearchMatches(team: "Flamengo",
            competition: "Brasileirão", season: null, fromDate: null, toDate: null, opponent: null, round: null, stage: null);
        var flamengoCdB = _matchService.SearchMatches(team: "Flamengo",
            competition: "Copa do Brasil", season: null, fromDate: null, toDate: null, opponent: null, round: null, stage: null);

        Assert.NotEmpty(flamengoBrasileirao);
        Assert.NotEmpty(flamengoCdB);
    }

    [Fact]
    [Trait("Feature", "Cross-file Queries")]
    public void Scenario_Players_and_matches_can_be_correlated_by_club()
    {
        // Find top players at a club, then find matches for that club
        var clubPlayers = _playerService.GetTopPlayersByClub("Santos", limit: 5);
        Assert.NotEmpty(clubPlayers);

        var clubMatches = _matchService.SearchMatches(team: "Santos",
            competition: null, season: null, fromDate: null, toDate: null, opponent: null, round: null, stage: null, limit: 10);
        Assert.NotEmpty(clubMatches);
    }
}
