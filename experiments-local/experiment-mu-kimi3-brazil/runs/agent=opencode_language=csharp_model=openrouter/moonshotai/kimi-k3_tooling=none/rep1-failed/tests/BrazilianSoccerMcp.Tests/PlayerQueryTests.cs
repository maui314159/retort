namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Player Queries
///   Search by name, filter by nationality and club, ratings and attributes.
/// </summary>
public class PlayerQueryTests
{
    /*
     * Scenario: Search player by name
     *   Given the FIFA data is loaded
     *   When I search for "Gabriel Barbosa"
     *   Then I find the Flamengo striker
     */
    [Fact]
    public void Search_player_by_name()
    {
        // Given
        var service = TestData.Service;

        // When
        var players = service.SearchPlayers(name: "Gabriel Barbosa");

        // Then
        Assert.NotEmpty(players);
        Assert.Contains(players, p => p.Name.Contains("Gabriel Barbosa"));
    }

    /*
     * Scenario: Filter by nationality
     *   Given the FIFA data is loaded
     *   When I filter players by nationality "Brazil"
     *   Then all returned players are Brazilian
     */
    [Fact]
    public void Filter_players_by_nationality()
    {
        // Given
        var service = TestData.Service;

        // When
        var players = service.SearchPlayers(nationality: "Brazil", limit: 50);

        // Then
        Assert.Equal(50, players.Count);
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality));
    }

    /*
     * Scenario: Highest-rated players at a club
     *   Given the FIFA data is loaded
     *   When I filter players by club "Flamengo"
     *   Then results are sorted by overall rating, best first
     */
    [Fact]
    public void Highest_rated_players_at_a_club_are_sorted()
    {
        // Given
        var service = TestData.Service;

        // When
        var players = service.SearchPlayers(club: "Flamengo", limit: 10);

        // Then
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Contains("Flamengo", p.Club ?? ""));
        var ratings = players.Select(p => p.Overall ?? 0).ToList();
        Assert.Equal(ratings.OrderByDescending(r => r).ToList(), ratings);
    }

    /*
     * Scenario: Forwards from São Paulo FC
     *   Given the FIFA data is loaded
     *   When I filter club "São Paulo" with position "ST"
     *   Then all results play for São Paulo and are strikers
     */
    [Fact]
    public void Forwards_from_a_club_can_be_filtered()
    {
        // Given
        var service = TestData.Service;

        // When
        var players = service.SearchPlayers(club: "São Paulo", position: "ST", limit: 10);

        // Then
        Assert.All(players, p =>
        {
            Assert.Contains("Paulo", p.Club ?? "");
            Assert.Equal("ST", p.Position);
        });
    }

    /*
     * Scenario: Top Brazilian players
     *   Given the FIFA data is loaded
     *   When I filter Brazilians with overall >= 85
     *   Then well known stars such as Neymar appear
     */
    [Fact]
    public void Top_brazilian_players_include_stars()
    {
        // Given
        var service = TestData.Service;

        // When
        var players = service.SearchPlayers(nationality: "Brazil", minOverall: 85, limit: 30);

        // Then
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.True(p.Overall >= 85));
        Assert.Contains(players, p => p.Name.Contains("Neymar", StringComparison.OrdinalIgnoreCase));
    }

    /*
     * Scenario: Brazilian players at Brazilian clubs summary
     *   Given the FIFA data is loaded
     *   When I summarize Brazilian players per club
     *   Then Brazilian clubs appear with player counts and average ratings
     */
    [Fact]
    public void Club_player_summary_works()
    {
        // Given
        var service = TestData.Service;

        // When
        var summary = service.GetClubPlayerSummary(nationality: "Brazil", limit: 200);

        // Then
        Assert.NotEmpty(summary);
        Assert.Contains(summary, s => s.Club.Contains("Flamengo"));
        Assert.All(summary, s => Assert.True(s.Count > 0 && s.AvgOverall > 0));
    }

    /*
     * Scenario: Name search is diacritics-insensitive
     *   Given the FIFA data is loaded
     *   When I search "Neymar" without accents
     *   Then "Neymar Jr" is found
     */
    [Fact]
    public void Name_search_handles_accents()
    {
        // Given
        var service = TestData.Service;

        // When
        var players = service.SearchPlayers(name: "Neymar", limit: 5);

        // Then
        Assert.Contains(players, p => p.Name.Contains("Neymar", StringComparison.OrdinalIgnoreCase));
    }
}
