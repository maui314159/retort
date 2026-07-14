using BrazilianSoccerMcp.Tests.Infrastructure;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Competition Queries
/// BDD scenarios for standings, champions, and relegation computed from matches.
/// </summary>
[Collection("SoccerData")]
public class CompetitionTests
{
    private readonly DataFixture _f;
    public CompetitionTests(DataFixture f) => _f = f;

    // Scenario: Who won the 2019 Brasileirão?
    //   Given the match data is loaded
    //   When I request the champion of the 2019 Brasileirão
    //   Then I should receive the top team of the standings
    [Fact]
    public void Champion_2019_Brasileirao_returns_top_team()
    {
        var champ = _f.Competitions.Champion("Brasileirão", 2019);
        Assert.NotNull(champ);
        Assert.Equal(1, champ!.Position);
        Assert.True(champ.Points > 0);
    }

    // Scenario: standings are sorted by points descending
    [Fact]
    public void Standings_sorted_by_points_descending()
    {
        var table = _f.Competitions.Standings("Brasileirão", 2019);
        Assert.NotEmpty(table);
        for (var i = 1; i < table.Count; i++)
            Assert.True(table[i - 1].Points >= table[i].Points);
    }

    // Scenario: standings points = 3*W + D for each row
    [Fact]
    public void Standings_points_equal_3wins_plus_draws()
    {
        var table = _f.Competitions.Standings("Brasileirão", 2018);
        Assert.NotEmpty(table);
        Assert.All(table, r => Assert.Equal(3 * r.Wins + r.Draws, r.Points));
    }

    // Scenario: standings goal difference = GF - GA
    [Fact]
    public void Standings_goal_difference_is_goals_for_minus_against()
    {
        var table = _f.Competitions.Standings("Brasileirão", 2019);
        Assert.All(table, r => Assert.Equal(r.GoalsFor - r.GoalsAgainst, r.GoalDifference));
    }

    // Scenario: relegated teams are the bottom N
    [Fact]
    public void Relegated_returns_bottom_four()
    {
        var table = _f.Competitions.Standings("Brasileirão", 2019);
        var relegated = _f.Competitions.Relegated("Brasileirão", 2019, 4);

        Assert.Equal(4, relegated.Count);
        Assert.Equal(table[^4].Team, relegated[0].Team);
    }

    // Scenario: top scoring teams returns non-empty list with positive goals
    [Fact]
    public void TopScoringTeams_returns_positive_goal_counts()
    {
        var teams = _f.Competitions.TopScoringTeams("Brasileirão", 2019, 5);
        Assert.NotEmpty(teams);
        Assert.All(teams, t => Assert.True(t.Goals > 0));
        for (var i = 1; i < teams.Count; i++)
            Assert.True(teams[i - 1].Goals >= teams[i].Goals);
    }

    // Scenario: seasons present in a competition
    [Fact]
    public void SeasonsInCompetition_returns_multiple_years()
    {
        var seasons = _f.Competitions.SeasonsInCompetition("Brasileirão");
        Assert.True(seasons.Count >= 2);
        Assert.Contains(2019, seasons);
    }
}