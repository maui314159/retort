// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    SoccerToolsTests.cs
// Project: BrazilianSoccer.Tests
// Purpose: BDD scenarios exercising the MCP tool layer (SoccerTools) end-to-end
//          against the real dataset, verifying the formatted answer text an LLM
//          client would receive for representative spec questions.
// =============================================================================

using BrazilianSoccer.Core.Queries;
using BrazilianSoccer.Server;
using Xunit;

namespace BrazilianSoccer.Tests;

[Collection("dataset")]
public sealed class SoccerToolsTests
{
    private readonly QueryService _query;

    public SoccerToolsTests(DatasetFixture fixture) => _query = fixture.Query;

    [Fact]
    public void Given_Tool_When_FindMatchesForPalmeiras2019_Then_TextListsMatches()
    {
        // When the find_matches tool runs for Palmeiras in 2019
        var text = SoccerTools.FindMatches(_query, team: "Palmeiras", season: 2019, limit: 5);

        // Then the answer is the Palmeiras 2019 heading with match lines
        Assert.Contains("Palmeiras", text);
        Assert.Contains("2019", text);
        Assert.Contains("-", text); // score separator present
    }

    [Fact]
    public void Given_Tool_When_MatchesBetweenRivals_Then_HeadToHeadSummaryIncluded()
    {
        // When the matches_between tool runs for the Fla-Flu derby
        var text = SoccerTools.MatchesBetween(_query, "Flamengo", "Fluminense");

        // Then the head-to-head summary is present
        Assert.Contains("Head-to-head in dataset:", text);
        Assert.Contains("wins", text);
        Assert.Contains("draws", text);
    }

    [Fact]
    public void Given_Tool_When_Standings2019_Then_FlamengoListedAsChampion()
    {
        // When the standings tool calculates the 2019 Brasileirão
        var text = SoccerTools.Standings(_query, "Brasileirao", 2019);

        // Then Flamengo appears as champion
        Assert.Contains("Champion", text);
        Assert.Contains("Flamengo", text);
        Assert.Contains("pts", text);
    }

    [Fact]
    public void Given_Tool_When_Champion2019_Then_ReturnsFlamengo()
    {
        var text = SoccerTools.Champion(_query, "Brasileirao", 2019);
        Assert.Contains("Flamengo", text);
        Assert.Contains("champion", text, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Given_Tool_When_PlayersByNationalityBrazil_Then_NeymarRanksHigh()
    {
        var text = SoccerTools.PlayersByNationality(_query, "Brazil", limit: 10);
        Assert.Contains("Brazil", text);
        Assert.Contains("Neymar", text);
    }

    [Fact]
    public void Given_Tool_When_SearchSinglePlayer_Then_DetailedCardReturned()
    {
        // A unique-enough name yields the single-player detail card
        var text = SoccerTools.SearchPlayers(_query, "Neymar Jr", limit: 5);
        Assert.Contains("Nationality: Brazil", text);
        Assert.Contains("Overall:", text);
    }

    [Fact]
    public void Given_Tool_When_TeamRecordWithVenue_Then_ContextReflectsVenueAndSeason()
    {
        var text = SoccerTools.TeamRecord(_query, "Corinthians", competition: "Brasileirao", season: 2019, venue: "home");
        Assert.Contains("Corinthians", text);
        Assert.Contains("home", text);
        Assert.Contains("Win rate:", text);
    }

    [Fact]
    public void Given_Tool_When_Statistics_Then_AverageGoalsReported()
    {
        var text = SoccerTools.Statistics(_query, competition: "Brasileirao", season: 2019);
        Assert.Contains("Average goals per match:", text);
        Assert.Contains("Home win rate:", text);
    }

    [Fact]
    public void Given_Tool_When_BiggestWins_Then_RankedListReturned()
    {
        var text = SoccerTools.BiggestWins(_query, competition: "Brasileirao", limit: 5);
        Assert.Contains("Biggest victories", text);
        Assert.Contains("1.", text);
    }

    [Fact]
    public void Given_Tool_When_UnknownCompetitionStandings_Then_GracefulMessage()
    {
        var text = SoccerTools.Standings(_query, "Premier League", 2019);
        Assert.Contains("Unknown competition", text);
    }
}
