namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Team Queries
///   Match history, W/D/L records, goals and head-to-head comparisons.
/// </summary>
public class TeamQueryTests
{
    /*
     * Scenario: Get team statistics
     *   Given the match data is loaded
     *   When I request statistics for "Palmeiras" in season "2023"
     *   Then I should receive wins, losses, draws, and goals
     */
    [Fact]
    public void Get_team_statistics_for_a_season()
    {
        // Given
        var service = TestData.Service;

        // When
        var record = service.GetTeamRecord("Palmeiras", season: 2023);

        // Then
        Assert.True(record.Matches > 0);
        Assert.Equal(record.Matches, record.Wins + record.Draws + record.Losses);
        Assert.True(record.GoalsFor >= 0);
        Assert.True(record.GoalsAgainst >= 0);
    }

    /*
     * Scenario: Home record differs from away record
     *   Given the match data is loaded
     *   When I request Corinthians' home record in 2022
     *   Then only home matches are counted
     */
    [Fact]
    public void Home_record_counts_only_home_matches()
    {
        // Given
        var service = TestData.Service;
        var cor = service.ResolveTeamKeys("Corinthians");

        // When
        var home = service.GetTeamRecord("Corinthians", season: 2022, venue: "home");
        var all = service.GetTeamRecord("Corinthians", season: 2022, venue: "all");

        // Then
        Assert.True(home.Matches > 0);
        Assert.True(all.Matches >= home.Matches);

        // cross-check against raw match list
        var expectedHome = service.Matches.Count(m =>
            cor.Contains(m.HomeTeamKey) && (m.Season == 2022 || m.Date?.Year == 2022));
        Assert.Equal(expectedHome, home.Matches);
    }

    /*
     * Scenario: Compare Palmeiras and Santos head-to-head
     *   Given the match data is loaded
     *   When I request the head-to-head
     *   Then win/draw counts are consistent with the match list
     */
    [Fact]
    public void Head_to_head_counts_are_consistent()
    {
        // Given
        var service = TestData.Service;

        // When
        var h2h = service.GetHeadToHead("Palmeiras", "Santos");

        // Then
        Assert.NotEmpty(h2h.Matches);
        Assert.Equal(h2h.Matches.Count, h2h.Team1Wins + h2h.Team2Wins + h2h.Draws);

        // and every match really involves both teams
        var pal = service.ResolveTeamKeys("Palmeiras");
        var san = service.ResolveTeamKeys("Santos");
        Assert.All(h2h.Matches, m =>
            Assert.True(
                (pal.Contains(m.HomeTeamKey) && san.Contains(m.AwayTeamKey)) ||
                (san.Contains(m.HomeTeamKey) && pal.Contains(m.AwayTeamKey))));
    }

    /*
     * Scenario: Which team scored the most goals in Série A 2023
     *   Given the match data is loaded
     *   When I aggregate goals for all teams in the 2023 Brasileirão
     *   Then the top scorer team has more goals than the median team
     */
    [Fact]
    public void Top_scoring_team_can_be_computed()
    {
        // Given
        var service = TestData.Service;

        // When
        var standings = service.GetStandings("Brasileirão Série A", 2023);
        var topGoals = standings.OrderByDescending(r => r.GoalsFor).First();

        // Then
        Assert.True(standings.Count >= 20, $"Expected >=20 teams, got {standings.Count}");
        Assert.True(topGoals.GoalsFor > standings.Select(r => r.GoalsFor).OrderBy(x => x)
            .ElementAt(standings.Count / 2));
    }

    /*
     * Scenario: What competitions has Palmeiras played in?
     *   Given the match data is loaded
     *   When I list competitions for Palmeiras
     *   Then Brasileirão, Copa do Brasil and Libertadores all appear
     */
    [Fact]
    public void Competitions_for_a_team_are_listed()
    {
        // Given
        var service = TestData.Service;

        // When
        var comps = service.GetCompetitionsForTeam("Palmeiras");

        // Then
        Assert.Contains(comps, c => c.Contains("Brasileirão"));
        Assert.Contains(comps, c => c.Contains("Copa do Brasil"));
        Assert.Contains(comps, c => c.Contains("Libertadores"));
    }
}
