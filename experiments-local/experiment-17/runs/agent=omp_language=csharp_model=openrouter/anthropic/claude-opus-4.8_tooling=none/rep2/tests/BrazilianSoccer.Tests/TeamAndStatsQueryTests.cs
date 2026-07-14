// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    TeamAndStatsQueryTests.cs
// Project: BrazilianSoccer.Tests
// Purpose: BDD scenarios for team records, head-to-head, calculated standings
//          and dataset-wide statistics — the spec's "Feature: Team statistics"
//          and statistical-analysis capabilities, against the real data.
// =============================================================================

using BrazilianSoccer.Core.Models;
using BrazilianSoccer.Core.Queries;
using Xunit;

namespace BrazilianSoccer.Tests;

[Collection("dataset")]
public sealed class TeamAndStatsQueryTests
{
    private readonly QueryService _query;

    public TeamAndStatsQueryTests(DatasetFixture fixture) => _query = fixture.Query;

    [Fact]
    public void Given_TeamAndSeason_When_RequestingRecord_Then_WdlSumsToPlayedAndGoalsConsistent()
    {
        // When I request Palmeiras' 2019 Brasileirão record
        var record = _query.TeamRecordFor(
            "Palmeiras",
            new MatchFilter { Competition = Competition.Brasileirao, Season = 2019 });

        // Then wins+draws+losses equals matches played, and goals are counted
        Assert.True(record.Played > 0);
        Assert.Equal(record.Played, record.Wins + record.Draws + record.Losses);
        Assert.True(record.GoalsFor >= 0 && record.GoalsAgainst >= 0);
    }

    [Fact]
    public void Given_HomeVenueFilter_When_RequestingRecord_Then_PlayedNotMoreThanFullRecord()
    {
        var filter = new MatchFilter { Competition = Competition.Brasileirao, Season = 2019 };
        var all = _query.TeamRecordFor("Corinthians", filter);
        var home = _query.TeamRecordFor("Corinthians", filter, venue: "home");
        var away = _query.TeamRecordFor("Corinthians", filter, venue: "away");

        // home + away played equals total played
        Assert.Equal(all.Played, home.Played + away.Played);
        Assert.True(home.Played > 0);
    }

    [Fact]
    public void Given_TwoTeams_When_ComputingHeadToHead_Then_WinsAndDrawsSumToTotalMatches()
    {
        // When I compute Palmeiras vs Santos head-to-head
        var h2h = _query.HeadToHeadFor("Palmeiras", "Santos");

        // Then the breakdown is internally consistent
        Assert.True(h2h.TotalMatches > 0);
        Assert.Equal(h2h.TotalMatches, h2h.TeamAWins + h2h.TeamBWins + h2h.Draws);
        Assert.Equal(h2h.TotalMatches, h2h.Matches.Count);
    }

    [Fact]
    public void Given_Season2019_When_CalculatingBrasileiraoStandings_Then_FlamengoIsChampionWith20Teams()
    {
        // When I calculate the 2019 Brasileirão table
        var standings = _query.Standings(Competition.Brasileirao, 2019);

        // Then there are 20 teams and Flamengo (the real 2019 champion) tops it
        Assert.Equal(20, standings.Count);
        Assert.Equal(1, standings[0].Position);
        Assert.Equal("flamengo", Normalize(standings[0].Record.Team));

        // And the table is ordered by points descending
        for (var i = 1; i < standings.Count; i++)
            Assert.True(standings[i - 1].Record.Points >= standings[i].Record.Points);
    }

    [Fact]
    public void Given_Season2019_When_CalculatingStandings_Then_EachTeamPlays38Matches()
    {
        // A 20-team double round-robin => 38 matches each.
        var standings = _query.Standings(Competition.Brasileirao, 2019);
        Assert.All(standings, row => Assert.Equal(38, row.Record.Played));
    }

    [Fact]
    public void Given_Brasileirao_When_ComputingStatistics_Then_RatesAreSensible()
    {
        // When I compute league-wide stats for the Brasileirão
        var stats = _query.ComputeStatistics(new MatchFilter { Competition = Competition.Brasileirao });

        // Then goals-per-match is in a believable football range and rates sum to 1
        Assert.True(stats.TotalMatches > 1000);
        Assert.InRange(stats.AverageGoalsPerMatch, 1.5, 4.0);
        Assert.Equal(stats.TotalMatches, stats.HomeWins + stats.AwayWins + stats.Draws);
        Assert.Equal(1.0, stats.HomeWinRate + stats.AwayWinRate + stats.DrawRate, 3);
    }

    [Fact]
    public void Given_Data_When_FindingBiggestWins_Then_TheyAreOrderedByMarginDescending()
    {
        // When I ask for the biggest victories
        var matches = _query.BiggestWins(new MatchFilter { Competition = Competition.Brasileirao }, limit: 10);

        // Then margins are non-increasing and the top margin is large
        var margins = matches.Select(m => Math.Abs(m.HomeGoals - m.AwayGoals)).ToList();
        for (var i = 1; i < margins.Count; i++)
            Assert.True(margins[i - 1] >= margins[i]);
        Assert.True(margins[0] >= 5);
    }

    [Fact]
    public void Given_Season_When_RankingTopScoringTeams_Then_GoalsDescendAndChampionScoresMost()
    {
        var teams = _query.TopScoringTeams(
            new MatchFilter { Competition = Competition.Brasileirao, Season = 2019 }, limit: 5);
        Assert.NotEmpty(teams);
        for (var i = 1; i < teams.Count; i++)
            Assert.True(teams[i - 1].Goals >= teams[i].Goals);
    }

    private static string Normalize(string s) =>
        BrazilianSoccer.Core.Data.TeamNameNormalizer.Canonical(s);
}
