using BrazilianSoccerCore.Data;
using BrazilianSoccerMcp.Tests.Infrastructure;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Match Queries
/// BDD scenarios for searching and comparing matches across datasets.
/// </summary>
[Collection("SoccerData")]
public class MatchQueryTests
{
    private readonly DataFixture _f;
    public MatchQueryTests(DataFixture f) => _f = f;

    // Scenario: Find matches between two teams
    //   Given the match data is loaded
    //   When I search for matches between "Flamengo" and "Fluminense"
    //   Then I should receive a list of matches
    //   And each match should have date, scores, and competition
    [Fact]
    public void HeadToHeadMatches_between_Flamengo_and_Fluminense_returns_scored_matches()
    {
        var matches = _f.Matches.HeadToHeadMatches("Flamengo", "Fluminense");

        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.True(m.Date != DateTime.MinValue, "match should have a date");
            Assert.NotNull(m.HomeGoal);
            Assert.NotNull(m.AwayGoal);
            Assert.False(string.IsNullOrEmpty(m.Competition));
            var involvesBoth =
                (TeamNormalizer.SameTeam(m.HomeTeam, "Flamengo") && TeamNormalizer.SameTeam(m.AwayTeam, "Fluminense")) ||
                (TeamNormalizer.SameTeam(m.HomeTeam, "Fluminense") && TeamNormalizer.SameTeam(m.AwayTeam, "Flamengo"));
            Assert.True(involvesBoth);
        });
    }

    // Scenario: Search matches by team and season
    //   When I search for Palmeiras matches in 2023
    //   Then every result involves Palmeiras and is from 2023
    [Fact]
    public void SearchMatches_by_team_and_season_filters_correctly()
    {
        var matches = _f.Matches.SearchMatches(team: "Palmeiras", season: 2023, limit: 500);

        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.Equal(2023, m.Season);
            Assert.True(
                TeamNormalizer.SameTeam(m.HomeTeam, "Palmeiras") ||
                TeamNormalizer.SameTeam(m.AwayTeam, "Palmeiras"));
        });
    }

    // Scenario: team name variations match (state suffix)
    //   When I search for "Flamengo" it should also match "Flamengo-RJ"
    [Fact]
    public void SearchMatches_matches_team_with_state_suffix()
    {
        var matches = _f.Matches.SearchMatches(team: "Flamengo", limit: 1000);
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.True(
                TeamNormalizer.SameTeam(m.HomeTeam, "Flamengo") ||
                TeamNormalizer.SameTeam(m.AwayTeam, "Flamengo"));
        });
    }

    // Scenario: filter by competition
    [Fact]
    public void SearchMatches_by_competition_returns_only_that_competition()
    {
        var matches = _f.Matches.SearchMatches(competition: "Libertadores", limit: 50);
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Contains("Libertadores", m.Competition, StringComparison.OrdinalIgnoreCase));
    }

    // Scenario: Last match between two teams
    [Fact]
    public void LastMatchBetween_returns_most_recent()
    {
        var last = _f.Matches.LastMatchBetween("Flamengo", "Fluminense");
        Assert.NotNull(last);
        var all = _f.Matches.HeadToHeadMatches("Flamengo", "Fluminense");
        Assert.Equal(all.Max(m => m.Date), last!.Date);
    }

    // Scenario: all 6 CSV files are loaded
    [Fact]
    public void All_datasets_loaded()
    {
        var sources = _f.Loader.Matches.Select(m => m.Source).Distinct().ToHashSet();
        Assert.Contains("Brasileirao_Matches.csv", sources);
        Assert.Contains("Brazilian_Cup_Matches.csv", sources);
        Assert.Contains("Libertadores_Matches.csv", sources);
        Assert.Contains("BR-Football-Dataset.csv", sources);
        Assert.Contains("novo_campeonato_brasileiro.csv", sources);
        Assert.True(_f.Loader.Players.Count > 10000, "FIFA player data should be loaded");
    }

    // Scenario: head-to-head record sums correctly
    [Fact]
    public void CompareTeams_record_sums_to_match_count()
    {
        var h2h = _f.Matches.CompareTeams("Palmeiras", "Santos");
        Assert.Equal(h2h.Matches, h2h.TeamAWins + h2h.TeamBWins + h2h.Draws);
    }
}