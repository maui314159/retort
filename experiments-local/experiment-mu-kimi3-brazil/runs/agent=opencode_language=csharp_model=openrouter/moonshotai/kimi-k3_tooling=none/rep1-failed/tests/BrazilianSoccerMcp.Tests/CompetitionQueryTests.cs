namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Competition Queries
///   Standings by season (calculated from match results), champions,
///   relegation and knockout brackets.
/// </summary>
public class CompetitionQueryTests
{
    /*
     * Scenario: Who won the 2019 Brasileirão?
     *   Given the match data is loaded
     *   When I compute the 2019 Brasileirão standings
     *   Then Flamengo is champion with 20 teams in the table
     *   (Flamengo won the real 2019 title with 90 points)
     */
    [Fact]
    public void Flamengo_won_the_2019_brasileirao()
    {
        // Given
        var service = TestData.Service;

        // When
        var standings = service.GetStandings("Brasileirão Série A", 2019);

        // Then
        Assert.True(standings.Count >= 20, $"Expected >=20 teams, got {standings.Count}");
        Assert.Equal("Flamengo", standings[0].Team.Split('-')[0].Trim());
        Assert.Equal(90, standings[0].Points);
        Assert.True(standings[0].Played >= 38, $"Expected 38 rounds, got {standings[0].Played}");
    }

    /*
     * Scenario: Standings points are arithmetically consistent
     *   Given the match data is loaded
     *   When I compute any season standings
     *   Then points equal 3*wins + draws for every row
     */
    [Fact]
    public void Standings_points_are_consistent()
    {
        // Given
        var service = TestData.Service;

        // When
        var standings = service.GetStandings("Brasileirão Série A", 2022);

        // Then
        Assert.NotEmpty(standings);
        Assert.All(standings, r =>
        {
            Assert.Equal(r.Wins * 3 + r.Draws, r.Points);
            Assert.Equal(r.Played, r.Wins + r.Draws + r.Losses);
        });
    }

    /*
     * Scenario: Relegation zone is identifiable
     *   Given the match data is loaded
     *   When I compute the 2019 Brasileirão standings
     *   Then the bottom 4 teams exist (relegated to Série B)
     */
    [Fact]
    public void Relegation_zone_is_identifiable()
    {
        // Given
        var service = TestData.Service;

        // When
        var standings = service.GetStandings("Brasileirão Série A", 2019);

        // Then
        var relegated = standings.TakeLast(4).ToList();
        Assert.Equal(4, relegated.Count);
        Assert.All(relegated, r => Assert.True(r.Position > standings.Count - 4));
    }

    /*
     * Scenario: Show the 2018 Copa Libertadores bracket
     *   Given the match data is loaded
     *   When I fetch Libertadores 2018 matches
     *   Then knockout stages (round of 16, quarterfinals, semifinals, final) are present
     */
    [Fact]
    public void Libertadores_knockout_stages_are_present()
    {
        // Given
        var service = TestData.Service;

        // When
        var games = service.FindMatches(competition: "Libertadores", season: 2018, limit: 500);
        var stages = games.Select(m => m.Round).Distinct().ToList();

        // Then
        Assert.Contains(stages, s => string.Equals(s, "final", StringComparison.OrdinalIgnoreCase));
        Assert.Contains(stages, s => string.Equals(s, "semifinals", StringComparison.OrdinalIgnoreCase));
        Assert.Contains(stages, s => string.Equals(s, "quarterfinals", StringComparison.OrdinalIgnoreCase));
        Assert.Contains(stages, s => string.Equals(s, "round of 16", StringComparison.OrdinalIgnoreCase));
    }

    /*
     * Scenario: Competition listing includes match counts
     *   Given the match data is loaded
     *   When competitions are listed
     *   Then each has at least one match
     */
    [Fact]
    public void Competition_listing_is_non_empty()
    {
        // Given
        var service = TestData.Service;

        // When
        var comps = service.GetCompetitions();

        // Then
        Assert.True(comps.Count >= 5, $"Expected >=5 competitions, got {comps.Count}");
        Assert.All(comps, c =>
            Assert.True(service.Matches.Any(m => m.Competition == c)));
    }

    /*
     * Scenario: Historical dataset covers 2003 season
     *   Given the historical Brasileirão file covers 2003-2019
     *   When I compute the 2003 standings
     *   Then Cruzeiro is champion (real 2003 winner with 100 points)
     */
    [Fact]
    public void Historical_2003_standings_are_available()
    {
        // Given
        var service = TestData.Service;

        // When
        var standings = service.GetStandings("Brasileirão", 2003);

        // Then
        Assert.NotEmpty(standings);
        Assert.Contains("Cruzeiro", standings[0].Team);
        Assert.Equal(100, standings[0].Points);
    }
}
