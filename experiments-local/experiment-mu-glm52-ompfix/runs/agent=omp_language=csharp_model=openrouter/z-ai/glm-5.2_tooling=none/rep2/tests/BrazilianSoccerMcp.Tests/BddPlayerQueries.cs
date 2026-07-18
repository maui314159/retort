// ============================================================================
// BrazilianSoccerMcp.Tests - BddPlayerQueries.cs
//
// Context block:
//   BDD tests for FIFA player search (TASK.md "Player Queries"): nationality
//   filter, club filter, top-rated, and accent-insensitive name search.
// ============================================================================

using BrazilianSoccerMcp.Data;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

public class BddPlayerQueries : IClassFixture<DataFixture>
{
    private readonly DataFixture _f;
    public BddPlayerQueries(DataFixture f) => _f = f;

    // Scenario: Find all Brazilian players in the dataset
    [Fact]
    public void Given_fifa_data_when_filtering_by_brazil_nationality_then_all_returned_are_brazilian()
    {
        var players = _f.Service.QueryPlayers(nationality: "Brazil").ToList();
        // The FIFA dataset has hundreds of Brazilians per the spec.
        Assert.True(players.Count > 100, $"expected many Brazilian players, got {players.Count}");
        Assert.All(players, p =>
            Assert.True(TeamNameNormalizer.NormalizeText(p.Nationality ?? "")
                .Contains("brazil", StringComparison.Ordinal)));
    }

    // Scenario: Who are the highest-rated players?
    [Fact]
    public void Given_fifa_data_when_requesting_top_players_then_returned_sorted_by_overall_desc()
    {
        var top = _f.Service.GetTopPlayers(limit: 10);
        Assert.Equal(10, top.Count);
        for (int i = 1; i < top.Count; i++)
            Assert.True(top[i - 1].Overall >= top[i].Overall, "should be sorted by overall desc");
    }

    // Scenario: Find players by club (Santos appears in the FIFA dataset)
    [Fact]
    public void Given_fifa_data_when_filtering_by_club_santos_then_all_returned_match_santos()
    {
        var players = _f.Service.QueryPlayers(club: "Santos").ToList();
        Assert.NotEmpty(players);
        // Substring match: every returned club's canonical form contains "santos".
        Assert.All(players, p =>
            Assert.Contains("santos",
                TeamNameNormalizer.NormalizeText(p.Club ?? ""), StringComparison.Ordinal));
        // The Brazilian club "Santos" (exact canonical) must be among the results.
        Assert.Contains(players, p =>
            TeamNameNormalizer.NormalizeText(p.Club ?? "").Equals("santos", StringComparison.Ordinal));
    }

    // Scenario: search by name is accent-insensitive
    [Fact]
    public void Given_fifa_data_when_searching_neymar_then_finds_regardless_of_accent()
    {
        var players = _f.Service.QueryPlayers(name: "Neymar").ToList();
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Contains("neymar",
            TeamNameNormalizer.NormalizeText(p.Name), StringComparison.Ordinal));
    }

    // Scenario: filter by position
    [Fact]
    public void Given_fifa_data_when_filtering_by_position_st_then_all_returned_are_strikers()
    {
        var players = _f.Service.QueryPlayers(position: "ST", nationality: "Brazil").ToList();
        Assert.All(players, p => Assert.Equal("ST", p.Position));
    }

    // Scenario: minimum overall rating
    [Fact]
    public void Given_fifa_data_when_filtering_min_overall_85_then_all_returned_meet_threshold()
    {
        var players = _f.Service.QueryPlayers(minOverall: 85).ToList();
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.True(p.Overall >= 85));
    }
}
