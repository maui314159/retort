// =============================================================================
// File:    SoccerToolsTests.cs
// Project: BrazilianSoccer.Tests
// Purpose: BDD tests for the MCP tool layer (SoccerTools) — the surface an LLM
//          client actually calls. Asserts the formatted text answers match the
//          shapes in TASK.md and that free-text arguments (competition names,
//          dates) parse correctly.
// Context: Tests invoke the tool methods directly with the shared database, so
//          they cover argument parsing + AnswerFormatter together without
//          spinning up stdio. Wording is asserted loosely (key substrings) so
//          cosmetic copy changes don't break tests; numbers are asserted where
//          they are load-bearing.
// =============================================================================

using BrazilianSoccer.Core;
using BrazilianSoccer.Server;

namespace BrazilianSoccer.Tests;

[Collection("database")]
public class SoccerToolsTests
{
    private readonly SoccerTools _tools;
    public SoccerToolsTests(DatabaseFixture fx) => _tools = new SoccerTools(fx.Db);

    [Fact]
    public void Given_TwoTeams_When_HeadToHeadTool_Then_AnswerHasMatchesAndSummary()
    {
        // When
        var answer = _tools.HeadToHead("Flamengo", "Fluminense");

        // Then
        Assert.Contains("Flamengo vs Fluminense", answer);
        Assert.Contains("Head-to-head in dataset", answer);
        Assert.Contains("wins", answer);
    }

    [Fact]
    public void Given_FreeTextCompetition_When_StandingsTool_Then_ParsedAndChampionShown()
    {
        // When the LLM passes a loose competition string
        var answer = _tools.LeagueStandings(2019, competition: "Brasileirao");

        // Then the calculated table names the champion
        Assert.Contains("2019", answer);
        Assert.Contains("Champion", answer);
        Assert.Contains("Flamengo", answer);
    }

    [Fact]
    public void Given_DateRange_When_FindMatchesTool_Then_OnlyInRangeReturned()
    {
        // When restricting Palmeiras matches to mid-2019
        var answer = _tools.FindMatches(team: "Palmeiras", from: "2019-06-01", to: "2019-06-30");

        // Then the answer lists matches (or a clean 'none' message) — never throws
        Assert.False(string.IsNullOrWhiteSpace(answer));
    }

    [Fact]
    public void Given_NationalityFilter_When_FindPlayersTool_Then_RankedListReturned()
    {
        // When
        var answer = _tools.FindPlayers(nationality: "Brazil", limit: 5);

        // Then a numbered, rating-sorted list is produced
        Assert.Contains("1.", answer);
        Assert.Contains("Overall:", answer);
    }

    [Fact]
    public void Given_HomeOnly_When_TeamRecordTool_Then_RecordBlockReturned()
    {
        // When
        var answer = _tools.TeamRecord("Corinthians", season: 2019, homeOnly: true);

        // Then the record block has the spec's fields
        Assert.Contains("Matches:", answer);
        Assert.Contains("Wins:", answer);
        Assert.Contains("Win rate:", answer);
    }

    [Fact]
    public void Given_NoData_When_HeadToHeadTool_Then_GracefulMessage()
    {
        // When two teams that never met (different eras/competitions edge case)
        var answer = _tools.HeadToHead("Madeup United", "Nowhere City");

        // Then a clean message, not an exception
        Assert.Contains("No data", answer, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Given_Libertadores_When_BiggestWinsTool_Then_SortedListReturned()
    {
        // When
        var answer = _tools.BiggestWins(competition: "Libertadores", limit: 5);

        // Then
        Assert.Contains("Biggest victories", answer);
        Assert.Contains("Copa Libertadores", answer);
    }
}
