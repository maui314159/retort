using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD scenarios for match queries.
/// Feature: Match Queries
/// </summary>
[Collection("Data")]
public sealed class MatchQueryTests(DataFixture fixture)
{
    private DataRepository Repo => fixture.Repository;

    // Scenario: Dataset is loaded
    [Fact]
    public void GivenAllCsvFiles_WhenDataLoaded_ThenMatchesExist()
    {
        // Then: all match files contributed records
        Assert.NotEmpty(Repo.Matches);
        Assert.True(Repo.Matches.Count > 1000,
            $"Expected >1000 matches, got {Repo.Matches.Count}");
    }

    [Fact]
    public void GivenAllCsvFiles_WhenDataLoaded_ThenAllCompetitionsPresent()
    {
        var competitions = Repo.Matches.Select(m => m.Competition).Distinct().ToHashSet();
        Assert.Contains(Competition.Brasileirao, competitions);
        Assert.Contains(Competition.CopaDoBrasil, competitions);
        Assert.Contains(Competition.Libertadores, competitions);
        Assert.Contains(Competition.HistoricoBrasileiro, competitions);
    }

    // Scenario: Find matches between two teams
    //   Given the match data is loaded
    //   When I search for matches between "Flamengo" and "Fluminense"
    //   Then I should receive a list of matches
    //   And each match should have date, scores, and competition
    [Fact]
    public void GivenMatchData_WhenSearchFlamengoVsFluminense_ThenMatchesReturnedWithRequiredFields()
    {
        var matches = Repo.SearchMatches(team: "Flamengo", opponent: "Fluminense", limit: 100);

        Assert.NotEmpty(matches);

        foreach (var m in matches)
        {
            Assert.True(m.Date != DateOnly.MinValue, "Date should be parsed");
            Assert.True(m.HomeGoals >= 0, "HomeGoals should be non-negative");
            Assert.True(m.AwayGoals >= 0, "AwayGoals should be non-negative");
            Assert.True(m.Season > 2000, "Season should be a valid year");

            // Each match must involve both teams
            bool flamengoInvolved =
                TeamNameNormalizer.Matches(m.HomeTeam, "Flamengo") ||
                TeamNameNormalizer.Matches(m.AwayTeam, "Flamengo");
            bool fluminenseInvolved =
                TeamNameNormalizer.Matches(m.HomeTeam, "Fluminense") ||
                TeamNameNormalizer.Matches(m.AwayTeam, "Fluminense");

            Assert.True(flamengoInvolved, $"Flamengo should be in match: {m.HomeTeam} vs {m.AwayTeam}");
            Assert.True(fluminenseInvolved, $"Fluminense should be in match: {m.HomeTeam} vs {m.AwayTeam}");
        }
    }

    // Scenario: Filter matches by season
    [Fact]
    public void GivenMatchData_WhenFilterBySeason2023_ThenAllMatchesAre2023()
    {
        var matches = Repo.SearchMatches(season: 2023, limit: 200);

        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(2023, m.Season));
    }

    // Scenario: Filter by competition
    [Fact]
    public void GivenMatchData_WhenFilterByCopaDoBrasil_ThenOnlyCupMatches()
    {
        var matches = Repo.SearchMatches(competition: Competition.CopaDoBrasil, limit: 50);

        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(Competition.CopaDoBrasil, m.Competition));
    }

    // Scenario: Filter Palmeiras matches
    [Fact]
    public void GivenMatchData_WhenSearchPalmeiras_ThenEveryMatchContainsPalmeiras()
    {
        var matches = Repo.SearchMatches(team: "Palmeiras", limit: 50);

        Assert.NotEmpty(matches);
        foreach (var m in matches)
        {
            bool found =
                TeamNameNormalizer.Matches(m.HomeTeam, "Palmeiras") ||
                TeamNameNormalizer.Matches(m.AwayTeam, "Palmeiras");
            Assert.True(found, $"Palmeiras not found in: {m.HomeTeam} vs {m.AwayTeam}");
        }
    }

    // Scenario: Date range filtering
    [Fact]
    public void GivenMatchData_WhenFilteredByDateRange_ThenAllMatchesWithinRange()
    {
        var from = new DateOnly(2022, 1, 1);
        var to = new DateOnly(2022, 12, 31);

        var matches = Repo.SearchMatches(fromDate: from, toDate: to, limit: 200);

        Assert.NotEmpty(matches);
        foreach (var m in matches)
        {
            if (m.Date == DateOnly.MinValue) continue; // skip unparseable
            Assert.True(m.Date >= from && m.Date <= to,
                $"Match date {m.Date} outside range {from}..{to}");
        }
    }

    // Scenario: Get biggest wins
    [Fact]
    public void GivenMatchData_WhenGetBiggestWins_ThenResultsOrderedByGoalDifference()
    {
        var wins = Repo.GetBiggestWins(limit: 10);

        Assert.NotEmpty(wins);
        Assert.All(wins, m => Assert.False(m.IsDraw));

        // Verify descending order
        for (int i = 1; i < wins.Count; i++)
            Assert.True(wins[i - 1].GoalDifference >= wins[i].GoalDifference);
    }

    // Scenario: Team name normalization strips state suffix
    [Fact]
    public void GivenTeamName_WhenNormalized_ThenStateSuffixRemoved()
    {
        Assert.Equal("Palmeiras", TeamNameNormalizer.Normalize("Palmeiras-SP"));
        Assert.Equal("Flamengo", TeamNameNormalizer.Normalize("Flamengo-RJ"));
        Assert.Equal("América", TeamNameNormalizer.Normalize("América - MG"));
        Assert.Equal("Palmeiras", TeamNameNormalizer.Normalize("Palmeiras")); // no suffix
    }

    // Scenario: Brazileirao dataset loads correctly
    [Fact]
    public void GivenBrasileiraoFile_WhenLoaded_ThenContainsExpectedMatches()
    {
        var brasileirao = Repo.Matches
            .Where(m => m.Competition == Competition.Brasileirao)
            .ToList();

        // File has ~4180 matches
        Assert.True(brasileirao.Count > 3000,
            $"Expected >3000 Brasileirao matches, got {brasileirao.Count}");
    }

    // Scenario: Libertadores dataset loads
    [Fact]
    public void GivenLibertadoresFile_WhenLoaded_ThenContainsStageInfo()
    {
        var lib = Repo.Matches
            .Where(m => m.Competition == Competition.Libertadores && m.Stage != null)
            .Take(1)
            .ToList();

        Assert.NotEmpty(lib);
    }
}
