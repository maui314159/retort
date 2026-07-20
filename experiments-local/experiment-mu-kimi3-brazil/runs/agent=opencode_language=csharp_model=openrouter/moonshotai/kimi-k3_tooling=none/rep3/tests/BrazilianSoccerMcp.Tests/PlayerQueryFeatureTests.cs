using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Player Queries
/// Search by name, nationality and club; ratings and attributes from the FIFA file.
/// </summary>
public class PlayerQueryFeatureTests
{
    private readonly PlayerQueryService _players = new(TestData.Graph);

    [Fact]
    public void Given_PlayerDataLoaded_When_SearchingGabrielJesus_Then_HeIsFoundWithRatingAndClub()
    {
        // Given / When (player lookup by name)
        var found = _players.Search(new PlayerQueryService.PlayerFilter { Name = "Gabriel Jesus" });

        // Then
        Assert.NotEmpty(found);
        Assert.All(found, p => Assert.Contains("Gabriel Jesus", p.Name, StringComparison.OrdinalIgnoreCase));
        Assert.All(found, p => Assert.True(p.Overall > 0));
        Assert.Contains(found, p => p.Club == "Manchester City" && p.Overall == 83);
    }

    [Fact]
    public void Given_PlayerDataLoaded_When_PlayerNotInDataset_Then_EmptyResultNotError()
    {
        // Given / When (Gabriel Barbosa is not in this FIFA edition)
        var found = _players.Search(new PlayerQueryService.PlayerFilter { Name = "Gabriel Barbosa" });

        // Then: the search degrades gracefully
        Assert.Empty(found);
    }

    [Fact]
    public void Given_PlayerDataLoaded_When_FilteringBrazilians_Then_NeymarIsTopRated()
    {
        // Given / When
        var top = _players.GetTopPlayers(nationality: "Brazil", limit: 5);

        // Then: reproduces the specification's expected answer
        Assert.Equal(5, top.Count);
        Assert.Equal("Neymar Jr", top[0].Name);
        Assert.Equal(92, top[0].Overall);
        Assert.Equal("Paris Saint-Germain", top[0].Club);
        Assert.All(top, p => Assert.Equal("Brazil", p.Nationality));
    }

    [Fact]
    public void Given_PlayerDataLoaded_When_SearchingByNameWithAccents_Then_AccentInsensitiveMatchWorks()
    {
        // Given / When (Neymar's name is plain, but search must ignore accents either way)
        var found = _players.Search(new PlayerQueryService.PlayerFilter { Name = "neymar" });

        // Then
        Assert.Contains(found, p => p.Name == "Neymar Jr");
    }

    [Fact]
    public void Given_PlayerDataLoaded_When_RequestingGremioSquad_Then_PlayersAreSortedByRating()
    {
        // Given / When
        var squad = _players.GetClubPlayers("Grêmio", 10, out _);

        // Then
        Assert.Equal(10, squad.Count);
        Assert.Equal("Ronaldo Cabrais", squad[0].Name);
        Assert.Equal(83, squad[0].Overall);
        Assert.True(squad.Zip(squad.Skip(1)).All(pair => pair.First.Overall >= pair.Second.Overall));
    }

    [Fact]
    public void Given_PlayerDataLoaded_When_FilteringForwardsAtSantos_Then_OnlyForwardsAreReturned()
    {
        // Given / When ("Show me all forwards from a Brazilian club")
        var forwards = _players.Search(new PlayerQueryService.PlayerFilter
        {
            Club = "Santos",
            ForwardsOnly = true,
            Limit = 50,
        });

        // Then
        Assert.Equal(3, forwards.Count);
        Assert.All(forwards, p => Assert.True(p.IsForward));
        Assert.All(forwards, p => Assert.Equal("Santos", p.Club));
    }

    [Fact]
    public void Given_PlayerDataLoaded_When_ClubNotInFifaFile_Then_GracefulNoteWithAlternatives()
    {
        // Given (Flamengo is absent from the FIFA file)

        // When
        var found = _players.GetClubPlayers("Flamengo", 10, out var note);

        // Then
        Assert.Empty(found);
        Assert.NotNull(note);
        Assert.Contains("Flamengo", note);
        Assert.Contains("Brazilian clubs present in the FIFA file include:", note);
        Assert.Contains("(20)", note); // squads of 20 players each are listed as alternatives
    }

    [Fact]
    public void Given_PlayerDataLoaded_When_CountingBrazilians_Then_CountIsNotCappedByResultLimit()
    {
        // Given / When (regression: Count must not inherit the display limit)
        var count = _players.Count(new PlayerQueryService.PlayerFilter { Nationality = "Brazil" });

        // Then
        Assert.Equal(827, count);
    }

    [Fact]
    public void Given_PlayerDataLoaded_When_FilteringByMinimumRating_Then_OnlyElitePlayersRemain()
    {
        // Given / When
        var elite = _players.Search(new PlayerQueryService.PlayerFilter { MinOverall = 90, Limit = 100 });

        // Then
        Assert.NotEmpty(elite);
        Assert.All(elite, p => Assert.True(p.Overall >= 90));
    }
}
