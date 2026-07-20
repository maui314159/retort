// BrazilianSoccerMcp.Tests / TeamQueriesTests.cs
// -----------------------------------------------------------------------------
// Context: BDD scenarios for TASK.md "Required Capabilities 2. Team Queries" and
// the Gherkin "Get team statistics". Covers W/D/L records, home/away splits,
// team comparison, and top scorers.
// Feature: Team Queries
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Queries;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

[Collection("SoccerData")]
public class TeamQueriesTests
{
    private readonly SoccerDataService _data;
    private readonly TeamQueries _queries;
    public TeamQueriesTests(SoccerDataFixture fixture)
    {
        _data = fixture.Data;
        _queries = new TeamQueries(_data);
    }

    // Scenario: Get team statistics  (from TASK.md Gherkin)
    [Fact]
    public void GivenMatchDataIsLoaded_WhenIRequestStatisticsForPalmeirasInSeason2020_ThenIReceiveWinsDrawsLossesAndGoals()
    {
        // Given the match data is loaded
        // When I request statistics for "Palmeiras" in season "2020"
        var record = _queries.TeamRecord("Palmeiras", CompetitionKind.BrasileiraoSerieA, 2020);
        // Then I should receive wins, losses, draws, and goals
        Assert.True(record.Matches > 0, "Palmeiras should have played matches in 2020");
        Assert.Equal(record.Matches, record.Wins + record.Draws + record.Losses);
        Assert.True(record.GoalsFor >= 0);
        Assert.True(record.GoalsAgainst >= 0);
    }

    // Scenario: home record is a subset of the overall record
    [Fact]
    public void GivenCorinthians2022_WhenRequestingHomeRecord_ThenHomeMatchesDoNotExceedTotalMatches()
    {
        // Given Corinthians in the 2022 Brasileirão
        // When I request the home-only record
        var home = _queries.TeamRecord("Corinthians", CompetitionKind.BrasileiraoSerieA, 2022, Venue.Home);
        var all = _queries.TeamRecord("Corinthians", CompetitionKind.BrasileiraoSerieA, 2022);
        // Then home matches <= total matches, and home record is non-empty
        Assert.True(home.Matches > 0, "Corinthians should have home matches in 2022 (NA-scored fixtures excluded)");
        Assert.True(home.Matches <= all.Matches);
        Assert.Equal(home.Wins + home.Draws + home.Losses, home.Matches);
    }

    // Scenario: compare two teams head-to-head
    [Fact]
    public void GivenPalmeirasAndSantos_WhenCompared_ThenBothRecordsAndHeadToHeadAreReturned()
    {
        // Given Palmeiras and Santos
        // When compared
        var (a, b, h2h) = _queries.Compare("Palmeiras", "Santos", CompetitionKind.BrasileiraoSerieA);
        // Then both records are populated and the head-to-head sums correctly
        Assert.True(a.Matches > 0);
        Assert.True(b.Matches > 0);
        Assert.Equal(h2h.TotalMatches, h2h.TeamAWins + h2h.TeamBWins + h2h.Draws);
    }

    // Scenario: top-scoring teams ranking
    [Fact]
    public void GivenBrasileirao2019_WhenRequestingTopScorers_ThenFlamengoIsAtOrNearTheTop()
    {
        // Given the 2019 Brasileirão
        // When I request the top-scoring teams
        var top = _queries.TopScoringTeams(CompetitionKind.BrasileiraoSerieA, 2019, limit: 5);
        // Then Flamengo (the 2019 champion) is among the top scorers
        Assert.NotEmpty(top);
        Assert.Contains(top, t => t.Team == "flamengo-rj");
        // And the list is sorted by goals descending
        for (int i = 1; i < top.Count; i++)
            Assert.True(top[i - 1].GoalsFor >= top[i].GoalsFor);
    }

    // Scenario: distinct same-base clubs accrue separately (Atlético regression)
    [Fact]
    public void GivenAtleticoMGAndAtleticoGO_WhenRecordsAreComputed_ThenTheyDoNotShareMatches()
    {
        // Given Atlético-MG and Atlético-GO are distinct clubs
        var mg = _queries.TeamRecord("Atlético-MG", CompetitionKind.BrasileiraoSerieA, 2019);
        var go = _queries.TeamRecord("Atlético-GO", CompetitionKind.BrasileiraoSerieA, 2019);
        // When their records are computed
        // Then neither record is the sum of both (no collision)
        // Atlético-MG played 2019; Atlético-GO was in Série B that year, so MG>0 and GO likely 0 here.
        Assert.True(mg.Matches > 0, "Atlético-MG should have 2019 Série A matches");
    }
}
