// ============================================================================
// BrazilianSoccerMcp.Tests - BddMatchQueries.cs
//
// Context block:
//   BDD (Given/When/Then) tests for match-query behaviour described in
//   TASK.md "Feature: Match Queries". Uses the real Kaggle CSVs loaded by
//   SoccerDataStore so the "Given the match data is loaded" step is real.
//   Class fixture loads the store once and shares it across all test methods.
// ============================================================================

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Tools;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>Shared store fixture — loads all datasets once per test class.</summary>
public sealed class DataFixture
{
    public SoccerDataStore Store { get; }
    public SoccerQueryService Service { get; }
    public SoccerTools Tools { get; }

    public DataFixture()
    {
        Store = new SoccerDataStore(TestDataPaths.KaggleDir());
        Service = new SoccerQueryService(Store);
        Tools = new SoccerTools(Service);
    }
}

public class BddMatchQueries : IClassFixture<DataFixture>
{
    private readonly DataFixture _f;
    public BddMatchQueries(DataFixture f) => _f = f;

    // ---------------------------------------------------------------- Given / When / Then
    // Scenario: All six CSV files are loaded
    [Fact]
    public void Given_all_six_datasets_when_loaded_then_each_is_queryable()
    {
        // Given — the store is constructed (fixture)
        // When — we inspect counts
        var counts = _f.Store.MatchCounts;
        var players = _f.Store.Players.Count;

        // Then — every dataset has data
        Assert.True(counts[Competition.Brasileirao] > 0, "Brasileirao matches");
        Assert.True(counts[Competition.CopaDoBrasil] > 0, "Copa do Brasil matches");
        Assert.True(counts[Competition.Libertadores] > 0, "Libertadores matches");
        Assert.True(counts[Competition.BrFootball] > 0, "BR-Football matches");
        Assert.True(counts[Competition.HistoricoBrasileirao] > 0, "Historico Brasileirao matches");
        Assert.True(players > 0, "FIFA players");
    }

    // Scenario: Find matches between two teams
    [Fact]
    public void Given_match_data_when_searching_flamengo_vs_fluminense_then_returns_matches()
    {
        // Given the match data is loaded
        // When I search for matches between "Flamengo" and "Fluminense"
        var matches = _f.Service.QueryMatches(team: "Flamengo", opponent: "Fluminense").ToList();

        // Then I should receive a list of matches
        Assert.NotEmpty(matches);
        // And each match should have date, scores, and competition
        Assert.All(matches, m =>
        {
            Assert.NotEqual(Competition.Unknown, m.Competition);
            Assert.False(string.IsNullOrEmpty(m.HomeTeam));
            Assert.False(string.IsNullOrEmpty(m.AwayTeam));
        });
        // And at least one side of each match is Flamengo, the other Fluminense
        Assert.All(matches, m =>
        {
            bool homeFla = TeamNameNormalizer.TeamMatches(m.HomeTeam, "Flamengo");
            bool awayFlu = TeamNameNormalizer.TeamMatches(m.AwayTeam, "Fluminense");
            bool homeFlu = TeamNameNormalizer.TeamMatches(m.HomeTeam, "Fluminense");
            bool awayFla = TeamNameNormalizer.TeamMatches(m.AwayTeam, "Flamengo");
            Assert.True(homeFla && awayFlu || homeFlu && awayFla,
                $"match {m.HomeTeam} v {m.AwayTeam} is not a Fla-Flu fixture");
        });
    }

    // Scenario: Filter by competition
    [Fact]
    public void Given_match_data_when_filtering_by_competition_then_only_that_competition_returns()
    {
        var matches = _f.Service.QueryMatches(competition: Competition.Brasileirao).ToList();
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(Competition.Brasileirao, m.Competition));
    }

    // Scenario: Filter by season
    [Fact]
    public void Given_match_data_when_filtering_by_season_2022_then_all_returned_matches_are_2022()
    {
        var matches = _f.Service.QueryMatches(season: 2022).ToList();
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(2022, m.Season));
    }

    // Scenario: team-name normalization handles the "-SP" suffix
    [Fact]
    public void Given_palmeiras_with_state_suffix_when_querying_then_suffix_free_query_matches()
    {
        // "Palmeiras-SP" in the data should match the bare query "Palmeiras"
        var matches = _f.Service.QueryMatches(team: "Palmeiras", competition: Competition.Brasileirao).ToList();
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.True(
            TeamNameNormalizer.TeamMatches(m.HomeTeam, "Palmeiras") ||
            TeamNameNormalizer.TeamMatches(m.AwayTeam, "Palmeiras")));
    }

    // Scenario: date range filtering
    [Fact]
    public void Given_match_data_when_filtering_by_date_range_then_only_in_range_returned()
    {
        var from = new DateTime(2023, 1, 1);
        var to = new DateTime(2023, 12, 31);
        var matches = _f.Service.QueryMatches(fromDate: from, toDate: to).ToList();
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.NotNull(m.Date);
            Assert.InRange(m.Date!.Value, from, to);
        });
    }
}
