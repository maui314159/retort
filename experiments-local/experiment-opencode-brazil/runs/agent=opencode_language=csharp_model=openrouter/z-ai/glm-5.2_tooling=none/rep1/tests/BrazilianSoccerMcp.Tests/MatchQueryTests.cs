// Context block
// File: MatchQueryTests.cs
// Purpose: BDD/GWT tests for the MatchService of the Brazilian Soccer MCP server, covering
// the "Match Queries" feature from TASK.md: find matches between two teams, find matches
// for a team in a season, and find the most recent match between two teams. Tests run
// against the real bundled CSV data via a shared SoccerDataStore, so they verify the full
// load + normalization + query pipeline. The store is lazily loaded so the first test in
// the run pays the one-time CSV load.
// Language: C# (.NET 10) + xUnit. Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

[Collection("SoccerData")]
public class MatchQueryTests
{
    private readonly SoccerDataFixture _fixture;
    public MatchQueryTests(SoccerDataFixture fixture) => _fixture = fixture;

    // Feature: Match Queries

    // Scenario: Find matches between two teams
    //   Given the match data is loaded
    //   When I search for matches between "Flamengo" and "Fluminense"
    //   Then I should receive a list of matches
    //   And each match should have date, scores, and competition
    [Fact]
    public void Head_to_head_returns_matches_with_metadata()
    {
        var matches = _fixture.Matches.HeadToHead("Flamengo", "Fluminense");

        Assert.NotEmpty(matches.Matches);
        Assert.All(matches.Matches, m =>
        {
            Assert.True(m.Date != DateTime.MinValue);
            Assert.True((_fixture.Store.Normalizer.Matches(m.Home, "Flamengo") ||
                         _fixture.Store.Normalizer.Matches(m.Away, "Flamengo")));
            Assert.True((_fixture.Store.Normalizer.Matches(m.Home, "Fluminense") ||
                         _fixture.Store.Normalizer.Matches(m.Away, "Fluminense")));
            Assert.True(m.CompetitionType != Competition.Unknown);
        });
        Assert.Equal(matches.TotalMatches, matches.TeamAWins + matches.TeamBWins + matches.Draws);
    }

    // Scenario: Get matches for a team in a season
    //   Given the match data is loaded
    //   When I search for Palmeiras matches in season 2022 in the Brasileirao
    //   Then every returned match should involve Palmeiras and be from 2022
    [Fact]
    public void Search_matches_filters_by_team_season_competition()
    {
        var matches = _fixture.Matches.SearchMatches(
            team: "Palmeiras", competition: Competition.Brasileirao, season: 2022);

        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.Equal(2022, m.Season);
            Assert.Equal(Competition.Brasileirao, m.CompetitionType);
            Assert.True(_fixture.Store.Normalizer.Matches(m.Home, "Palmeiras") ||
                        _fixture.Store.Normalizer.Matches(m.Away, "Palmeiras"));
        });
    }

    // Scenario: Find the most recent match between two teams
    //   Given the match data is loaded
    //   When I ask for the last match between Flamengo and Corinthians
    //   Then I should get a single match
    //   And that match should involve both teams
    [Fact]
    public void Last_match_between_returns_a_match_involving_both()
    {
        var m = _fixture.Matches.LastMatchBetween("Flamengo", "Corinthians");

        Assert.NotNull(m);
        Assert.True(_fixture.Store.Normalizer.Matches(m!.Home, "Flamengo") ||
                    _fixture.Store.Normalizer.Matches(m.Away, "Flamengo"));
        Assert.True(_fixture.Store.Normalizer.Matches(m.Home, "Corinthians") ||
                    _fixture.Store.Normalizer.Matches(m.Away, "Corinthians"));
    }

    // Scenario: Find all Copa do Brasil matches in a season
    //   Given the match data is loaded
    //   When I search the Copa do Brasil for season 2021
    //   Then every returned match should be a Copa do Brasil match from 2021
    [Fact]
    public void Search_matches_filters_copa_do_brasil_season()
    {
        var matches = _fixture.Matches.SearchMatches(competition: Competition.CopaDoBrasil, season: 2021);

        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.Equal(Competition.CopaDoBrasil, m.CompetitionType);
            Assert.Equal(2021, m.Season);
        });
    }
}

// Shared fixture that loads the CSV data once for all tests in the same collection.
public sealed class SoccerDataFixture : IDisposable
{
    public SoccerDataStore Store { get; } = new();
    public MatchService Matches { get; }
    public TeamService Teams { get; }
    public PlayerService Players { get; }
    public CompetitionService Competitions { get; }
    public StatisticsService Stats { get; }
    public ResponseFormatter Formatter { get; } = new();

    public SoccerDataFixture()
    {
        Store.EnsureMatchesLoaded();
        Store.EnsurePlayersLoaded();
        Matches = new MatchService(Store);
        Teams = new TeamService(Store, Matches);
        Players = new PlayerService(Store);
        Competitions = new CompetitionService(Store, Matches);
        Stats = new StatisticsService(Store, Matches, Teams);
    }

    public void Dispose() { }
}

[CollectionDefinition("SoccerData", DisableParallelization = true)]
public sealed class SoccerDataCollection : ICollectionFixture<SoccerDataFixture> { }
