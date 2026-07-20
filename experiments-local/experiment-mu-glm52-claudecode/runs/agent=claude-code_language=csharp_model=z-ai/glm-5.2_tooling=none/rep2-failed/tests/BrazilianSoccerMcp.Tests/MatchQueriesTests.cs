// BrazilianSoccerMcp.Tests / MatchQueriesTests.cs
// -----------------------------------------------------------------------------
// Context: BDD scenarios for TASK.md "Required Capabilities 1. Match Queries" and
// the Gherkin in "Testing Approach". Covers: find matches between two teams, find
// matches for a single team, competition/season/date filtering, and head-to-head.
// Feature: Match Queries
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Queries;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

[Collection("SoccerData")]
public class MatchQueriesTests
{
    private readonly SoccerDataService _data;
    private readonly MatchQueries _queries;
    public MatchQueriesTests(SoccerDataFixture fixture)
    {
        _data = fixture.Data;
        _queries = new MatchQueries(_data);
    }

    // Scenario: Find matches between two teams  (from TASK.md Gherkin)
    [Fact]
    public void GivenMatchDataIsLoaded_WhenISearchForMatchesBetweenFlamengoAndFluminense_ThenIReceiveMatchesWithDateScoresAndCompetition()
    {
        // Given the match data is loaded
        // When I search for matches between "Flamengo" and "Fluminense"
        var matches = _queries.MatchesBetween("Flamengo", "Fluminense",
            new MatchFilter { Competition = CompetitionKind.BrasileiraoSerieA });
        // Then I should receive a list of matches
        Assert.NotEmpty(matches);
        // And each match should have date, scores, and competition
        foreach (var m in matches)
        {
            Assert.True(m.HasScore, "every Fla-Flu match should carry a score");
            Assert.True(m.Date.HasValue, "every match should have a date");
            Assert.False(string.IsNullOrEmpty(m.CompetitionLabel));
            Assert.True(m.Involves("flamengo-rj") || m.Involves("fluminense-rj") ||
                        m.Involves("flamengo") || m.Involves("fluminense"));
        }
    }

    // Scenario: suffix-tolerant team lookup
    [Theory]
    [InlineData("Flamengo")]
    [InlineData("Flamengo-RJ")]
    [InlineData("flamengo")]
    [InlineData("FLAMENGO")]
    public void GivenVariantTeamNames_WhenSearchingMatchesForTeam_ThenResultsAreIdenticalRegardlessOfForm(string form)
    {
        // Given the same club expressed in different raw forms
        var matches = _queries.MatchesForTeam(form);
        // When searched, the result set is stable across forms
        Assert.NotEmpty(matches);
        var baseline = _queries.MatchesForTeam("Flamengo-RJ");
        Assert.Equal(baseline.Count, matches.Count);
    }

    // Scenario: find matches by competition+season
    [Fact]
    public void GivenBrasileirao2022_WhenRequestingMatchesByCompetition_ThenAllReturnedMatchesAreFromThatCompetitionAndSeason()
    {
        // Given the 2022 Brasileirão
        // When I request matches by competition
        var matches = _queries.MatchesByCompetition(CompetitionKind.BrasileiraoSerieA, 2022);
        // Then every returned match is from that competition and season
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.Equal(CompetitionKind.BrasileiraoSerieA, m.Competition);
            Assert.Equal(2022, m.Season);
        });
    }

    // Scenario: head-to-head summary between two teams
    [Fact]
    public void GivenTwoTeams_WhenIRequestHeadToHead_ThenWinsDrawsAndLossesSumToScoredMatchCount()
    {
        // Given Flamengo and Fluminense in the Brasileirão
        var h2h = _queries.HeadToHead("Flamengo", "Fluminense",
            new MatchFilter { Competition = CompetitionKind.BrasileiraoSerieA });
        // When the head-to-head is computed
        // Then wins + draws + losses == scored matches between them
        Assert.True(h2h.TeamAWins + h2h.TeamBWins + h2h.Draws > 0, "there should be at least one scored Fla-Flu");
        Assert.Equal(h2h.TotalMatches, h2h.TeamAWins + h2h.TeamBWins + h2h.Draws);
    }

    // Scenario: date-range filtering
    [Fact]
    public void GivenADateRange_WhenSearchingMatchesInThatRange_ThenAllMatchesFallWithinIt()
    {
        // Given a date range covering 2019
        var from = new DateTime(2019, 1, 1);
        var until = new DateTime(2019, 12, 31);
        // When searching matches in that range
        var matches = _queries.MatchesInDateRange(from, until);
        // Then every match date is within [from, until]
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.InRange(m.Date!.Value, from, until));
    }

    // Scenario: Palmeiras played multiple competitions
    [Fact]
    public void GivenPalmeiras_WhenSearchingAllMatches_ThenTheyAppearInMultipleCompetitions()
    {
        // Given Palmeiras
        // When I search all their matches
        var matches = _queries.MatchesForTeam("Palmeiras");
        // Then they appear in more than one competition (cross-file coverage)
        var competitions = matches.Select(m => m.Competition).Distinct().Count();
        Assert.True(competitions >= 2, "Palmeiras should appear across multiple competitions");
    }
}
