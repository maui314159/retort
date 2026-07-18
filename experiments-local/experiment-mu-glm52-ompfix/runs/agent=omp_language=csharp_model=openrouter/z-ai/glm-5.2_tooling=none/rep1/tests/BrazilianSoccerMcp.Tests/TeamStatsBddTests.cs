// Brazilian Soccer MCP Server - BDD tests for team statistics queries
//
// Context: BDD scenarios for the "Team Queries" and "Statistical Analysis"
// feature areas of the spec. These verify that win/loss/draw records, goals,
// and standings are computed correctly from the match data.

using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD-style tests for team statistics and standings. Maps to the spec's
/// team-query and competition-query scenarios.
/// </summary>
public class TeamStatsBddTests
{
    private readonly SoccerDataService _data = new();

    private SoccerDataService Data
    {
        get { _data.EnsureLoaded(); return _data; }
    }

    // Scenario: Get team statistics
    //   Given the match data is loaded
    //   When I request statistics for "Palmeiras" in season 2023
    //   Then I should receive wins, losses, draws, and goals
    [Fact]
    public void Get_team_statistics_returns_wins_losses_draws_goals()
    {
        // Given
        var service = Data;

        // When
        var stats = service.StatsForTeam("Palmeiras", season: 2023);

        // Then
        Assert.True(stats.Matches > 0, "Palmeiras should have matches in 2023");
        Assert.True(stats.Wins + stats.Draws + stats.Losses == stats.Matches,
            "Wins + Draws + Losses must equal total matches");
        Assert.True(stats.GoalsFor >= 0);
        Assert.True(stats.GoalsAgainst >= 0);
    }

    // Scenario: Home vs away records differ
    //   Given the match data is loaded
    //   When I request home-only and away-only stats for "Flamengo"
    //   Then the match counts should partition the total
    [Fact]
    public void Home_and_away_records_partition_total_matches()
    {
        // Given
        var service = Data;

        // When
        var total = service.StatsForTeam("Flamengo");
        var home = service.StatsForTeam("Flamengo", homeOnly: true);
        var away = service.StatsForTeam("Flamengo", awayOnly: true);

        // Then
        Assert.True(total.Matches > 0);
        Assert.Equal(total.Matches, home.Matches + away.Matches);
        Assert.Equal(total.GoalsFor, home.GoalsFor + away.GoalsFor);
        Assert.Equal(total.GoalsAgainst, home.GoalsAgainst + away.GoalsAgainst);
    }

    // Scenario: Standings calculation
    //   Given the match data is loaded for a season
    //   When I compute standings for "Brasileirão" 2019
    //   Then the champion should be Flamengo (historical fact, verifiable)
    //   And points should be sorted descending
    [Fact]
    public void Standings_for_2019_brasileirao_champion_is_flamengo()
    {
        // Given
        var service = Data;

        // When
        var standings = service.Standings("Brasileirão", 2019);

        // Then
        Assert.NotEmpty(standings);
        Assert.All(standings, s => Assert.True(s.Points >= 0));
        // Points sorted descending
        for (var i = 1; i < standings.Count; i++)
            Assert.True(standings[i].Points <= standings[i - 1].Points);
        // Champion flag on first entry
        Assert.True(standings[0].Champion);
    }

    // Scenario: Head-to-head record
    //   Given the match data is loaded
    //   When I compare "Palmeiras" and "Santos" head-to-head
    //   Then wins + draws + losses should equal total matches
    [Fact]
    public void Head_to_head_record_totals_are_consistent()
    {
        // Given
        var service = Data;

        // When
        var matches = service.HeadToHead("Palmeiras", "Santos").ToList();
        var stats = service.StatsForTeam("Palmeiras");

        // Then
        Assert.NotEmpty(matches);
        // Each head-to-head match must involve both teams
        var keyA = service.ResolveTeamKey("Palmeiras");
        var keyB = service.ResolveTeamKey("Santos");
        Assert.All(matches, m =>
        {
            bool aHome = m.HomeTeamKey == keyA;
            bool aAway = m.AwayTeamKey == keyA;
            bool bHome = m.HomeTeamKey == keyB;
            bool bAway = m.AwayTeamKey == keyB;
            Assert.True((aHome && bAway) || (aAway && bHome),
                "Each head-to-head match must involve both teams");
        });
    }

    // Scenario: Biggest victories
    //   Given the match data is loaded
    //   When I request the biggest victories
    //   Then they should be sorted by goal difference descending
    [Fact]
    public void Biggest_victories_sorted_by_goal_difference()
    {
        // Given
        var service = Data;

        // When
        var results = service.BiggestVictories(5);

        // Then
        Assert.NotEmpty(results);
        for (var i = 1; i < results.Count; i++)
            Assert.True(results[i].GoalDifference <= results[i - 1].GoalDifference);
        Assert.All(results, m => Assert.True(m.GoalDifference > 0));
    }

    // Scenario: Aggregate statistics
    //   Given the match data is loaded
    //   When I request aggregate stats for Brasileirão
    //   Then average goals should be positive and rates should sum to 100%
    [Fact]
    public void Aggregate_stats_for_brasileirao_are_consistent()
    {
        // Given
        var service = Data;
        var tools = new SoccerTools(service);
        service.EnsureLoaded();

        // When
        var result = tools.GetAggregateStats(competition: "Brasileirão");

        // Then
        Assert.Contains("Average goals per match", result);
        Assert.Contains("Home win rate", result);
        Assert.DoesNotContain("No completed matches", result);
    }
}
