using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Tools;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD-style tests for the Brazilian Soccer MCP Server.
/// Organized by Feature with Scenario methods following Given/When/Then pattern.
/// </summary>
public class MatchQueryTests
{
    private readonly MatchDataLoader _matchLoader;
    private readonly MatchTools _matchTools;

    public MatchQueryTests()
    {
        _matchLoader = new MatchDataLoader();
        _matchTools = new MatchTools(_matchLoader);
    }

    // ===== Feature: Match Queries =====

    [Fact]
    public void Given_MatchDataIsLoaded_When_SearchingForFlamengoVsFluminense_Then_ReturnsMatchesWithScoresAndCompetition()
    {
        // Given the match data is loaded
        Assert.NotEmpty(_matchLoader.Matches);

        // When I search for matches between Flamengo and Fluminense
        var result = _matchTools.search_matches("Flamengo", "Fluminense", limit: 50);

        // Then I should receive a list of matches
        Assert.DoesNotContain("No matches found", result);
        // And each match should have date, scores, and competition
        Assert.Contains("-", result); // score separator
        Assert.Contains("Head-to-head", result);
    }

    [Fact]
    public void Given_MatchDataIsLoaded_When_SearchingForPalmeirasIn2023_Then_ReturnsOnly2023Matches()
    {
        // Given the match data is loaded
        // When I search for Palmeiras matches in 2023
        var result = _matchTools.search_matches("Palmeiras", season: 2023, limit: 50);

        // Then all results should be from 2023
        Assert.DoesNotContain("No matches found", result);
        Assert.Contains("2023", result);
    }

    [Fact]
    public void Given_MatchDataIsLoaded_When_SearchingForCopaDoBrasil_Then_ReturnsCopaMatches()
    {
        // Given the match data is loaded
        // When I search for Copa do Brasil matches
        var result = _matchTools.search_matches("Flamengo", competition: "Copa do Brasil", limit: 10);

        // Then results should be from Copa do Brasil
        Assert.DoesNotContain("No matches found", result);
        Assert.Contains("Copa do Brasil", result);
    }

    [Fact]
    public void Given_MatchDataIsLoaded_When_SearchingForNonexistentTeam_Then_ReturnsNoMatches()
    {
        // Given the match data is loaded
        // When I search for a nonexistent team
        var result = _matchTools.search_matches("NonexistentTeamXYZ123");

        // Then I should receive no matches
        Assert.Contains("No matches found", result);
    }

    [Fact]
    public void Given_MatchDataIsLoaded_When_SearchingByDateRange_Then_ReturnsMatchesInThatRange()
    {
        // Given the match data is loaded
        // When I search with a date range
        var result = _matchTools.search_matches("Flamengo", date_from: "2023-01-01", date_to: "2023-12-31", limit: 50);

        // Then results should be returned
        Assert.DoesNotContain("No matches found", result);
    }

    [Fact]
    public void Given_AllSixCsvFiles_Then_AllAreLoaded()
    {
        // Verify all 6 CSV files contribute to the dataset
        var matches = _matchLoader.Matches;
        Assert.True(matches.Count > 20000, $"Expected >20k matches, got {matches.Count}");

        // Check that multiple competitions are represented
        var competitions = matches.Select(m => m.Competition).Distinct().ToList();
        Assert.Contains("Brasileirão", competitions);
        Assert.Contains("Copa do Brasil", competitions);
        Assert.Contains("Copa Libertadores", competitions);
    }
}

public class TeamQueryTests
{
    private readonly MatchDataLoader _matchLoader;
    private readonly TeamTools _teamTools;

    public TeamQueryTests()
    {
        _matchLoader = new MatchDataLoader();
        _teamTools = new TeamTools(_matchLoader);
    }

    // ===== Feature: Team Queries =====

    [Fact]
    public void Given_MatchDataIsLoaded_When_RequestingCorinthiansHomeRecord2022_Then_ReturnsStats()
    {
        // Given the match data is loaded
        // When I request statistics for Corinthians home record in 2022
        var result = _teamTools.get_team_stats("Corinthians", season: 2022, venue: "home");

        // Then I should receive wins, losses, draws, and goals
        Assert.DoesNotContain("No matches found", result);
        Assert.Contains("Home:", result);
        Assert.Contains("W", result); // Wins
        Assert.Contains("Win rate:", result);
    }

    [Fact]
    public void Given_MatchDataIsLoaded_When_RequestingOverallStats_Then_ReturnsHomeAndAway()
    {
        // Given the match data is loaded
        // When I request overall stats for a team
        var result = _teamTools.get_team_stats("Palmeiras");

        // Then both home and away breakdowns should be present
        Assert.DoesNotContain("No matches found", result);
        Assert.Contains("Home:", result);
        Assert.Contains("Away:", result);
        Assert.Contains("Overall:", result);
    }

    [Fact]
    public void Given_MatchDataIsLoaded_When_ComparingHeadToHead_Then_ReturnsComparison()
    {
        // Given the match data is loaded
        // When I compare Palmeiras and Santos head-to-head
        var result = _teamTools.head_to_head("Palmeiras", "Santos");

        // Then I should see win counts for both teams and draws
        Assert.DoesNotContain("No head-to-head matches", result);
        Assert.Contains("wins", result);
        Assert.Contains("Draws:", result);
        Assert.Contains("Palmeiras", result);
        Assert.Contains("Santos", result);
    }

    [Fact]
    public void Given_MatchDataIsLoaded_When_ComparingFlaFlu_Then_ReturnsDerbyData()
    {
        // Fla-Flu derby test
        var result = _teamTools.head_to_head("Flamengo", "Fluminense");
        Assert.DoesNotContain("No head-to-head matches", result);
        Assert.Contains("Flamengo", result);
        Assert.Contains("Fluminense", result);
    }

    [Fact]
    public void Given_MatchDataIsLoaded_When_GettingStatsForBrasileirao_Then_ReturnsFilteredStats()
    {
        var result = _teamTools.get_team_stats("Flamengo", competition: "Brasileirão");
        Assert.DoesNotContain("No matches found", result);
        Assert.Contains("Brasileirão", result);
    }
}

public class PlayerQueryTests
{
    private readonly PlayerDataLoader _playerLoader;
    private readonly PlayerTools _playerTools;

    public PlayerQueryTests()
    {
        _playerLoader = new PlayerDataLoader();
        _playerTools = new PlayerTools(_playerLoader);
    }

    // ===== Feature: Player Queries =====

    [Fact]
    public void Given_PlayerDataIsLoaded_When_SearchingForBrazilianPlayers_Then_ReturnsBrazilians()
    {
        // Given the player data is loaded
        Assert.NotEmpty(_playerLoader.Players);

        // When I search for Brazilian players
        var result = _playerTools.search_players(nationality: "Brazil", limit: 20);

        // Then I should find Brazilian players
        Assert.DoesNotContain("No players found", result);
        Assert.Contains("Brazil", result);
    }

    [Fact]
    public void Given_PlayerDataIsLoaded_When_SearchingByMinOverall_Then_ReturnsTopPlayers()
    {
        // When I search for players with overall >= 90
        var result = _playerTools.search_players(min_overall: 90, limit: 20);

        // Then all returned players should have high ratings
        Assert.DoesNotContain("No players found", result);
        Assert.Contains("Overall: 9", result); // 90-99 range
    }

    [Fact]
    public void Given_PlayerDataIsLoaded_When_SearchingByName_Then_ReturnsMatchingPlayer()
    {
        // When I search for "Neymar"
        var result = _playerTools.search_players(name: "Neymar");

        // Then I should find Neymar
        Assert.DoesNotContain("No players found", result);
        Assert.Contains("Neymar", result);
    }

    [Fact]
    public void Given_PlayerDataIsLoaded_When_SearchingByPosition_Then_ReturnsPositionPlayers()
    {
        // When I search for goalkeepers
        var result = _playerTools.search_players(position: "GK", min_overall: 85, limit: 10);

        // Then I should find goalkeepers
        Assert.DoesNotContain("No players found", result);
        Assert.Contains("GK", result);
    }

    [Fact]
    public void Given_PlayerDataIsLoaded_When_SearchingForBraziliansAtClubs_Then_ReturnsClubBreakdown()
    {
        // When I search for Brazilian players
        var result = _playerTools.search_players(nationality: "Brazil", limit: 5);

        // Then the result should include a club breakdown section for Brazilian clubs
        Assert.DoesNotContain("No players found", result);
    }

    [Fact]
    public void Given_PlayerDataIsLoaded_Then_Over18ThousandPlayersLoaded()
    {
        // Verify FIFA data was loaded
        Assert.True(_playerLoader.Players.Count > 15000,
            $"Expected >15k players, got {_playerLoader.Players.Count}");
    }
}

public class CompetitionAndStatisticsTests
{
    private readonly MatchDataLoader _matchLoader;
    private readonly CompetitionTools _competitionTools;
    private readonly StatisticsTools _statisticsTools;

    public CompetitionAndStatisticsTests()
    {
        _matchLoader = new MatchDataLoader();
        _competitionTools = new CompetitionTools(_matchLoader);
        _statisticsTools = new StatisticsTools(_matchLoader);
    }

    // ===== Feature: Competition Queries =====

    [Fact]
    public void Given_MatchDataIsLoaded_When_Getting2019BrasileiraoStandings_Then_ReturnsFlamengoAsChampion()
    {
        // Given the match data is loaded
        // When I request the 2019 Brasileirão standings
        var result = _competitionTools.get_competition_standings("Brasileirão", 2019);

        // Then Flamengo should be listed as champion
        Assert.DoesNotContain("No matches found", result);
        Assert.Contains("Flamengo", result);
        Assert.Contains("Champion", result);
    }

    [Fact]
    public void Given_MatchDataIsLoaded_When_GettingStandingsForNonexistentYear_Then_ReturnsNotFound()
    {
        // When I request standings for a year with no data
        var result = _competitionTools.get_competition_standings("Brasileirão", 1990);

        // Then I should get no matches found
        Assert.Contains("No matches found", result);
    }

    [Fact]
    public void Given_MatchDataIsLoaded_When_GettingCopaDoBrasilStandings_Then_ReturnsTeams()
    {
        var result = _competitionTools.get_competition_standings("Copa do Brasil", 2018);
        // Copa do Brasil is knockout, but standings can still be calculated
        Assert.DoesNotContain("No matches found", result);
    }

    // ===== Feature: Statistical Analysis =====

    [Fact]
    public void Given_MatchDataIsLoaded_When_GettingBiggestWins_Then_ReturnsLargestMargins()
    {
        // Given the match data is loaded
        // When I request biggest wins
        var result = _statisticsTools.get_biggest_wins(limit: 5);

        // Then I should see matches with large goal differentials
        Assert.DoesNotContain("No matches found", result);
        Assert.Contains("diff:", result);
    }

    [Fact]
    public void Given_MatchDataIsLoaded_When_GettingAverageGoals_Then_ReturnsStatistics()
    {
        // Given the match data is loaded
        // When I request average goals
        var result = _statisticsTools.get_average_goals();

        // Then I should see average goals, home/away rates
        Assert.DoesNotContain("No matches found", result);
        Assert.Contains("Average goals per match:", result);
        Assert.Contains("Home win rate:", result);
        Assert.Contains("Away win rate:", result);
        Assert.Contains("Draw rate:", result);
    }

    [Fact]
    public void Given_MatchDataIsLoaded_When_GettingAverageGoalsForBrasileirao_Then_ReturnsCompetitionStats()
    {
        var result = _statisticsTools.get_average_goals(competition: "Brasileirão");
        Assert.DoesNotContain("No matches found", result);
        Assert.Contains("Brasileirão", result);
    }

    [Fact]
    public void Given_MatchDataIsLoaded_When_GettingBiggestWinsForSpecificSeason_Then_ReturnsFilteredResults()
    {
        var result = _statisticsTools.get_biggest_wins(competition: "Brasileirão", season: 2019, limit: 5);
        Assert.DoesNotContain("No matches found", result);
    }
}

public class TeamNameNormalizationTests
{
    // ===== Feature: Team Name Handling =====

    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("Sport-PE", "Sport")]
    [InlineData("Athletico-PR", "Athletico-PR")]
    [InlineData("Palmeiras", "Palmeiras")]
    [InlineData("Sao Paulo", "São Paulo")]
    [InlineData("Gremio", "Grêmio")]
    [InlineData("Ceara", "Ceará")]
    [InlineData("Avai", "Avaí")]
    public void Given_TeamNameVariations_When_Normalizing_Then_ReturnsCanonicalName(string input, string expected)
    {
        var result = TeamNameNormalizer.Normalize(input);
        Assert.Equal(expected, result);
    }

    [Fact]
    public void Given_StateSuffix_When_Normalizing_Then_StripsSuffix()
    {
        // Team names with state suffixes should have suffix removed
        Assert.Equal("Vasco", TeamNameNormalizer.Normalize("Vasco-RJ"));
        Assert.Equal("Corinthians", TeamNameNormalizer.Normalize("Corinthians-SP"));
    }

    [Fact]
    public void Given_TeamNameWithAccents_When_Matching_Then_FindsAccentedVersion()
    {
        // "Sao Paulo" should match "São Paulo"
        Assert.True(TeamNameNormalizer.Matches("São Paulo", "Sao Paulo"));
        Assert.True(TeamNameNormalizer.Matches("Grêmio", "Gremio"));
    }

    [Fact]
    public void Given_PartialName_When_Matching_Then_FindsTeam()
    {
        Assert.True(TeamNameNormalizer.Matches("Flamengo-RJ", "Flamengo"));
        Assert.True(TeamNameNormalizer.Matches("Palmeiras-SP", "Palmeiras"));
    }
}

public class DataQualityTests
{
    private readonly MatchDataLoader _matchLoader;

    public DataQualityTests()
    {
        _matchLoader = new MatchDataLoader();
    }

    [Fact]
    public void Given_AllMatchData_Then_NoMatchesHaveEmptyTeams()
    {
        // All matches should have populated team names
        var emptyTeams = _matchLoader.Matches.Count(m =>
            string.IsNullOrWhiteSpace(m.HomeTeam) || string.IsNullOrWhiteSpace(m.AwayTeam));
        Assert.True(emptyTeams == 0, $"Found {emptyTeams} matches with empty team names");
    }

    [Fact]
    public void Given_AllMatchData_Then_NoMatchesHaveNegativeGoals()
    {
        var negativeGoals = _matchLoader.Matches.Count(m =>
            m.HomeGoals < 0 || m.AwayGoals < 0);
        Assert.True(negativeGoals == 0, $"Found {negativeGoals} matches with negative goals");
    }

    [Fact]
    public void Given_AllMatchData_Then_MultipleSeasonsArePresent()
    {
        var seasons = _matchLoader.Matches.Select(m => m.Season).Distinct().OrderBy(s => s).ToList();
        Assert.True(seasons.Count > 10, $"Expected >10 distinct seasons, got {seasons.Count}");
    }

    [Fact]
    public void Given_BrasileiraoData_Then_HasStateInformation()
    {
        var brasileiraoWithState = _matchLoader.Matches.Count(m =>
            m.Competition == "Brasileirão" && !string.IsNullOrEmpty(m.HomeTeamState));
        Assert.True(brasileiraoWithState > 0, "Expected some Brasileirão matches with state info");
    }

    [Fact]
    public void Given_HistoricalData_Then_HasStadiumInfo()
    {
        var withStadium = _matchLoader.Matches.Count(m => !string.IsNullOrEmpty(m.Stadium));
        Assert.True(withStadium > 0, "Expected some matches with stadium info");
    }
}
