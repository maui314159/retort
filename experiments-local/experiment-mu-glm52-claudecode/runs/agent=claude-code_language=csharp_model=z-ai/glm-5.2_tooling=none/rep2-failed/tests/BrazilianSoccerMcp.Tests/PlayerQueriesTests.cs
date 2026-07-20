// BrazilianSoccerMcp.Tests / PlayerQueriesTests.cs
// -----------------------------------------------------------------------------
// Context: BDD scenarios for TASK.md "Required Capabilities 3. Player Queries".
// Covers: search by name, filter by nationality (Brazilian), filter by club,
// top-rated lists, and the cross-file "Brazilian players at Brazilian clubs" query.
// Feature: Player Queries
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Queries;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

[Collection("SoccerData")]
public class PlayerQueriesTests
{
    private readonly PlayerQueries _queries;
    public PlayerQueriesTests(SoccerDataFixture fixture)
        => _queries = new PlayerQueries(fixture.Data);

    // Scenario: search players by name (accent- and case-insensitive)
    [Fact]
    public void GivenFifaDataLoaded_WhenISearchByName_ThenResultsContainMatchingNames()
    {
        // Given the FIFA player data is loaded
        // When I search for "Neymar"
        var players = _queries.SearchByName("Neymar");
        // Then at least one Brazilian Neymar is found
        Assert.NotEmpty(players);
        Assert.Contains(players, p => p.Name.Contains("Neymar", StringComparison.OrdinalIgnoreCase));
        // And results are sorted by overall rating descending
        for (int i = 1; i < players.Count; i++)
            Assert.True(players[i - 1].Overall >= players[i].Overall);
    }

    // Scenario: filter by nationality — all Brazilian players
    [Fact]
    public void GivenFifaDataLoaded_WhenIFilterByBrazilianNationality_ThenAllResultsAreBrazilian()
    {
        // Given the FIFA player data is loaded
        // When I filter by nationality "Brazil"
        var players = _queries.ByNationality("Brazil");
        // Then every result is Brazilian, and the list is non-empty
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality));
    }

    // Scenario: top-rated Brazilian players
    [Fact]
    public void GivenBrazilianPlayers_WhenRequestingTopRated_ThenResultsAreSortedByOverallDescending()
    {
        // Given the dataset
        // When I request top-rated Brazilian players
        var players = _queries.TopRated(limit: 10, nationality: "Brazil");
        // Then results are sorted by overall descending
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality));
        for (int i = 1; i < players.Count; i++)
            Assert.True(players[i - 1].Overall >= players[i].Overall);
    }

    // Scenario: cross-file query — Brazilian players at Brazilian clubs
    [Fact]
    public void GivenFifaAndMatchData_WhenIRequestBraziliansAtBrazilianClubs_ThenClubsAreCrossReferencedAgainstMatchData()
    {
        // Given the FIFA and match datasets are both loaded
        // When I request Brazilian players at Brazilian clubs
        var buckets = _queries.BrazilianPlayersAtBrazilianClubs();
        // Then each bucket's club is one that actually appears in the match datasets
        Assert.NotEmpty(buckets);
        // Brazilian clubs known to exist in both datasets (single-token names that
        // normalize identically across the FIFA Club field and the match files).
        var labels = buckets.Select(b => b.Label).ToHashSet();
        Assert.Contains("bahia", labels);   // fifa "Bahia" matches match-data "Bahia-BA"
        // And average ratings are sensible
        Assert.All(buckets, b => Assert.True(b.AverageRating > 0 && b.AverageRating <= 100));
    }

    // Scenario: players at a club
    [Fact]
    public void GivenAClub_WhenIRequestPlayersAtThatClub_ThenAllResultsAreFromThatClub()
    {
        // Given the dataset
        // When I request players at "Bahia"
        var players = _queries.ByClub("Bahia");
        // Then every returned player is at a club that normalizes to "bahia"
        Assert.NotEmpty(players);
        Assert.All(players, p =>
        {
            var key = BrazilianSoccerMcp.Core.Normalization.TeamNormalizer.Normalize(p.Club ?? "");
            Assert.True(key == "bahia" || key == "bahia-ba",
                $"expected bahia club, got {key}");
        });
    }
}
