using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD scenarios for player queries.
/// Feature: Player Queries
/// </summary>
[Collection("Data")]
public sealed class PlayerQueryTests(DataFixture fixture)
{
    private DataRepository Repo => fixture.Repository;

    // Scenario: Player data loads
    //   Given the FIFA CSV file exists
    //   When the data is loaded
    //   Then players should be available
    [Fact]
    public void GivenFifaCsv_WhenLoaded_ThenPlayersExist()
    {
        Assert.NotEmpty(Repo.Players);
        Assert.True(Repo.Players.Count > 1000,
            $"Expected >1000 players, got {Repo.Players.Count}");
    }

    // Scenario: Find Brazilian players
    //   Given the player data is loaded
    //   When I search for Brazilian nationality
    //   Then I should get Brazilian players
    [Fact]
    public void GivenPlayerData_WhenSearchBrazilianNationality_ThenOnlyBrazilianPlayers()
    {
        var players = Repo.SearchPlayers(nationality: "Brazil", limit: 50);

        Assert.NotEmpty(players);
        Assert.All(players, p =>
            Assert.Contains("Brazil", p.Nationality, StringComparison.OrdinalIgnoreCase));
    }

    // Scenario: Search by name
    //   Given the player data is loaded
    //   When I search for "Neymar"
    //   Then I should find Neymar in the results
    [Fact]
    public void GivenPlayerData_WhenSearchByName_ThenMatchingPlayersReturned()
    {
        var players = Repo.SearchPlayers(name: "Neymar", limit: 5);

        Assert.NotEmpty(players);
        Assert.All(players, p =>
            Assert.Contains("Neymar", p.Name, StringComparison.OrdinalIgnoreCase));
    }

    // Scenario: Search players at a club
    [Fact]
    public void GivenPlayerData_WhenSearchByClub_ThenPlayersFromThatClub()
    {
        // The FIFA dataset contains mostly European clubs; Santos is one Brazilian club present.
        var players = Repo.SearchPlayers(club: "Santos", limit: 30);

        Assert.NotEmpty(players);
        Assert.All(players, p =>
            Assert.Contains("Santos", p.Club, StringComparison.OrdinalIgnoreCase));
    }

    // Scenario: Players sorted by overall rating descending
    [Fact]
    public void GivenPlayerData_WhenSearched_ThenResultsOrderedByOverallDescending()
    {
        var players = Repo.SearchPlayers(nationality: "Brazil", limit: 20);

        for (int i = 1; i < players.Count; i++)
            Assert.True(players[i - 1].Overall >= players[i].Overall,
                $"Players not sorted by rating: {players[i - 1].Overall} < {players[i].Overall}");
    }

    // Scenario: Filter by minimum rating
    [Fact]
    public void GivenPlayerData_WhenFilterMinRating80_ThenAllPlayersAtLeast80()
    {
        var players = Repo.SearchPlayers(minRating: 80, limit: 50);

        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.True(p.Overall >= 80,
            $"Player {p.Name} has rating {p.Overall} < 80"));
    }

    // Scenario: Filter by position
    [Fact]
    public void GivenPlayerData_WhenFilterByPosition_ThenOnlyThatPosition()
    {
        var players = Repo.SearchPlayers(position: "GK", limit: 20);

        Assert.NotEmpty(players);
        Assert.All(players, p =>
            Assert.Contains("GK", p.Position, StringComparison.OrdinalIgnoreCase));
    }

    // Scenario: Player has required fields
    [Fact]
    public void GivenPlayerData_WhenLoaded_ThenAllRequiredFieldsPresent()
    {
        var sample = Repo.Players.Take(10).ToList();
        foreach (var p in sample)
        {
            Assert.True(p.Id > 0, "Player ID should be positive");
            Assert.False(string.IsNullOrWhiteSpace(p.Name), "Player Name should not be empty");
            Assert.True(p.Overall > 0 && p.Overall <= 99, $"Overall rating {p.Overall} out of range");
            Assert.True(p.Age > 0 && p.Age < 60, $"Age {p.Age} looks invalid");
        }
    }

    // Scenario: Search players combining filters
    [Fact]
    public void GivenPlayerData_WhenSearchBrazilianForwards_ThenResultMatchBothFilters()
    {
        var players = Repo.SearchPlayers(nationality: "Brazil", position: "ST", limit: 20);

        Assert.NotEmpty(players);
        foreach (var p in players)
        {
            Assert.Contains("Brazil", p.Nationality, StringComparison.OrdinalIgnoreCase);
            Assert.Contains("ST", p.Position, StringComparison.OrdinalIgnoreCase);
        }
    }
}
