// =============================================================================
// Brazilian Soccer MCP Server
// File: TeamQueriesTests.cs
// Purpose: BDD tests for the "Team Queries" capability.
// Context: Covers the example questions from the spec: home records, H2H,
//          best home/away records.
// =============================================================================

using BrazilianSoccerMcp.Core;
using BrazilianSoccerMcp.Core.Models;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests;

[Collection("Dataset")]
public class TeamQueriesTests
{
    private readonly QueryEngine _engine;
    public TeamQueriesTests(TestDataFixture fixture) => _engine = fixture.Engine;

    // Scenario: "What is Corinthians' home record in 2022?"
    [Fact]
    public void Given_Corinthians_home_2022_When_asking_for_record_Then_returns_wins_draws_losses_goals()
    {
        var rec = _engine.GetTeamRecord("Corinthians", season: 2022,
            competition: Competition.Brasileirao, homeOrAway: "Home");
        rec.Should().NotBeNull();
        rec!.Played.Should().BeGreaterThan(0);
        (rec.Wins + rec.Draws + rec.Losses).Should().Be(rec.Played);
        rec.GoalsFor.Should().BeGreaterThanOrEqualTo(0);
        rec.GoalsAgainst.Should().BeGreaterThanOrEqualTo(0);
    }

    // Scenario: "Compare Palmeiras and Santos head-to-head"
    [Fact]
    public void Given_Palmeiras_and_Santos_When_asking_for_h2h_Then_returns_match_list_and_counts()
    {
        var h2h = _engine.HeadToHead("Palmeiras", "Santos");
        h2h.Matches.Should().NotBeEmpty();
        (h2h.AWins + h2h.BWins + h2h.Draws).Should().Be(h2h.Matches.Count);
    }

    // Scenario: "Which team has the best home record?"
    [Fact]
    public void Given_top_home_records_When_ranking_Then_winner_has_highest_win_rate()
    {
        var best = _engine.BestHomeRecords(minGames: 100, limit: 5);
        best.Should().NotBeEmpty();
        for (var i = 1; i < best.Count; i++)
            best[i].WinRate.Should().BeLessThanOrEqualTo(best[i - 1].WinRate);
    }

    // Scenario: "Which team has the best away record?"
    [Fact]
    public void Given_top_away_records_When_ranking_Then_winner_has_highest_win_rate()
    {
        var best = _engine.BestAwayRecords(minGames: 100, limit: 5);
        best.Should().NotBeEmpty();
        for (var i = 1; i < best.Count; i++)
            best[i].WinRate.Should().BeLessThanOrEqualTo(best[i - 1].WinRate);
    }

    // Scenario: team name with state suffix must produce the same record
    // as the unsuffixed form.
    [Fact]
    public void Given_team_name_with_or_without_state_suffix_When_asking_for_record_Then_results_match()
    {
        var suffixed = _engine.GetTeamRecord("Flamengo-RJ", competition: Competition.Brasileirao);
        var bare = _engine.GetTeamRecord("Flamengo", competition: Competition.Brasileirao);
        suffixed.Should().NotBeNull();
        bare.Should().NotBeNull();
        suffixed!.Played.Should().Be(bare!.Played);
        suffixed.Wins.Should().Be(bare.Wins);
        suffixed.GoalsFor.Should().Be(bare.GoalsFor);
    }

    // Scenario: combined record (no home/away scope) must equal the sum of
    // home + away record counts for the same team / season.
    [Fact]
    public void Given_team_season_When_asking_combined_record_Then_played_equals_home_plus_away()
    {
        var combined = _engine.GetTeamRecord("Palmeiras", season: 2018, competition: Competition.Brasileirao);
        var home = _engine.GetTeamRecord("Palmeiras", season: 2018, competition: Competition.Brasileirao, homeOrAway: "Home");
        var away = _engine.GetTeamRecord("Palmeiras", season: 2018, competition: Competition.Brasileirao, homeOrAway: "Away");
        combined.Should().NotBeNull();
        home.Should().NotBeNull();
        away.Should().NotBeNull();
        combined!.Played.Should().Be(home!.Played + away!.Played);
    }
}
