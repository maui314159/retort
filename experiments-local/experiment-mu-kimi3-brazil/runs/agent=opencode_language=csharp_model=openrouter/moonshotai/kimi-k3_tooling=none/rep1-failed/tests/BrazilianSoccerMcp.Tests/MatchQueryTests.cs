namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Match Queries
///   Find matches by team, date range, competition and season.
/// </summary>
public class MatchQueryTests
{
    /*
     * Scenario: Find matches between two teams
     *   Given the match data is loaded
     *   When I search for matches between "Flamengo" and "Fluminense"
     *   Then I should receive a list of matches
     *   And each match should have date, scores, and competition
     */
    [Fact]
    public void Find_matches_between_two_teams()
    {
        // Given
        var service = TestData.Service;

        // When
        var matches = service.FindMatches(team1: "Flamengo", team2: "Fluminense");

        // Then
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.NotNull(m.Date);
            Assert.False(string.IsNullOrWhiteSpace(m.Competition));
            // score is part of the record by construction
            Assert.True(m.HomeGoals >= 0 && m.AwayGoals >= 0);
        });
    }

    /*
     * Scenario: Fla-Flu matches involve the right teams
     *   Given the match data is loaded
     *   When I search for matches between "Flamengo" and "Fluminense"
     *   Then every returned match has Flamengo and Fluminense as participants
     */
    [Fact]
    public void Fla_flu_matches_involve_the_right_teams()
    {
        // Given
        var service = TestData.Service;

        // When
        var matches = service.FindMatches(team1: "Flamengo", team2: "Fluminense");

        // Then
        var fla = service.ResolveTeamKeys("Flamengo");
        var flu = service.ResolveTeamKeys("Fluminense");
        Assert.All(matches, m =>
            Assert.True(
                (fla.Contains(m.HomeTeamKey) && flu.Contains(m.AwayTeamKey)) ||
                (flu.Contains(m.HomeTeamKey) && fla.Contains(m.AwayTeamKey)),
                $"Unexpected participants: {m.HomeTeam} vs {m.AwayTeam}"));
    }

    /*
     * Scenario: Find matches by team and season
     *   Given the match data is loaded
     *   When I search for matches of "Palmeiras" in season 2023
     *   Then all returned matches involve Palmeiras and belong to 2023
     */
    [Fact]
    public void Find_matches_by_team_and_season()
    {
        // Given
        var service = TestData.Service;

        // When
        var matches = service.FindMatches(team1: "Palmeiras", season: 2023);

        // Then
        Assert.NotEmpty(matches);
        var pal = service.ResolveTeamKeys("Palmeiras");
        Assert.All(matches, m =>
        {
            Assert.True(pal.Contains(m.HomeTeamKey) || pal.Contains(m.AwayTeamKey));
            Assert.True(m.Season == 2023 || m.Date?.Year == 2023);
        });
    }

    /*
     * Scenario: Find matches by competition
     *   Given the match data is loaded
     *   When I search for Copa do Brasil matches in 2023
     *   Then only Copa do Brasil matches are returned
     */
    [Fact]
    public void Find_matches_by_competition()
    {
        // Given
        var service = TestData.Service;

        // When
        var matches = service.FindMatches(competition: "Copa do Brasil", season: 2023);

        // Then
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Contains("Copa do Brasil", m.Competition));
    }

    /*
     * Scenario: Find Copa do Brasil finals-equivalent late rounds
     *   Given the match data is loaded
     *   When I search Libertadores matches at the "final" stage
     *   Then only final-stage matches are returned
     */
    [Fact]
    public void Find_libertadores_finals()
    {
        // Given
        var service = TestData.Service;

        // When
        var finals = service.FindMatches(competition: "Libertadores", limit: 2000)
            .Where(m => string.Equals(m.Round, "final", StringComparison.OrdinalIgnoreCase))
            .ToList();

        // Then
        Assert.NotEmpty(finals);
        Assert.All(finals, m => Assert.Equal("Copa Libertadores", m.Competition));
    }

    /*
     * Scenario: Find matches by date range
     *   Given the match data is loaded
     *   When I search matches between 2023-09-01 and 2023-09-30
     *   Then every returned match date falls inside the range
     */
    [Fact]
    public void Find_matches_by_date_range()
    {
        // Given
        var service = TestData.Service;
        var from = new DateTime(2023, 9, 1);
        var to = new DateTime(2023, 9, 30, 23, 59, 59);

        // When
        var matches = service.FindMatches(from: from, to: to);

        // Then
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.NotNull(m.Date);
            Assert.InRange(m.Date!.Value, from, to);
        });
    }

    /*
     * Scenario: When did Flamengo last play Corinthians?
     *   Given the match data is loaded
     *   When I search for matches between "Flamengo" and "Corinthians" limited to 1
     *   Then I receive the most recent match with its score
     */
    [Fact]
    public void Most_recent_match_between_two_teams_is_returned_first()
    {
        // Given
        var service = TestData.Service;

        // When
        var latest = service.FindMatches(team1: "Flamengo", team2: "Corinthians", limit: 1);

        // Then
        Assert.Single(latest);
        Assert.True(latest[0].Date >= new DateTime(2020, 1, 1),
            "Expected a recent Fla x Corinthians match");
    }

    /*
     * Scenario: Unknown team yields an empty result, not an error
     *   Given the match data is loaded
     *   When I search for a nonexistent team
     *   Then an empty list is returned
     */
    [Fact]
    public void Unknown_team_yields_empty_result()
    {
        // Given
        var service = TestData.Service;

        // When
        var matches = service.FindMatches(team1: "Nonexistent FC XYZZY");

        // Then
        Assert.Empty(matches);
    }
}
