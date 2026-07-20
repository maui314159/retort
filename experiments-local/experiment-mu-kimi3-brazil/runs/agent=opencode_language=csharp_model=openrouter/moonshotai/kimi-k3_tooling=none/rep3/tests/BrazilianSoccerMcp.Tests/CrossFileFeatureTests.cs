using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Cross-file knowledge-graph queries
/// Player data (FIFA file) and match data (five match files) share the same
/// team normalization, so queries can traverse both worlds.
/// </summary>
public class CrossFileFeatureTests
{
    [Fact]
    public void Given_TheGraph_When_InspectingStats_Then_AllNodeKindsArePopulated()
    {
        // Given / When
        var stats = TestData.Graph.Stats();

        // Then
        Assert.True(stats.TeamNodes > 100);
        Assert.Equal(18_207, stats.PlayerNodes);
        Assert.True(stats.CompetitionNodes >= 5);
        Assert.True(stats.SeasonNodes >= 20);
        Assert.True(stats.MatchNodes > 10_000);
        Assert.True(stats.Edges > stats.MatchNodes * 4);
    }

    [Fact]
    public void Given_TheGraph_When_ResolvingTeamNames_Then_FifaClubAndMatchTeamShareOneNode()
    {
        // Given / When
        var fromMatchName = TestData.Graph.ResolveTeam("Grêmio-RS");
        var fromFifaName = TestData.Graph.ResolveTeam("Grêmio");

        // Then
        Assert.True(fromMatchName.Found);
        Assert.True(fromFifaName.Found);
        Assert.Equal(fromMatchName.Team!.Key, fromFifaName.Team!.Key);
    }

    [Fact]
    public void Given_TheGraph_When_ResolvingAmbiguousName_Then_MostRelevantClubWinsWithNote()
    {
        // Given / When ("atletico" matches Atlético-MG, Atlético-GO and Athletico-PR)
        var resolution = TestData.Graph.ResolveTeam("atletico");

        // Then: the club with most matches in the dataset wins, and the choice is disclosed
        Assert.True(resolution.Found);
        Assert.Equal("atletico mg", resolution.Team!.Key);
        Assert.NotNull(resolution.Note);
        Assert.Contains("Interpreted", resolution.Note);
    }

    [Fact]
    public void Given_TheGraph_When_QueryingPlayersAtABrazilianClub_Then_ClubKeyJoinsMatchTeams()
    {
        // Given: the FIFA "Santos" club key must equal the match-data "santos" team key
        var teamResolution = TestData.Graph.ResolveTeam("Santos");

        // When
        var players = new PlayerQueryService(TestData.Graph).GetClubPlayers("Santos", 5, out _);

        // Then
        Assert.True(teamResolution.Found);
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Equal(teamResolution.Team!.Key, p.ClubKey));
    }

    [Fact]
    public void Given_TheGraph_When_ComputingPlayerClubSummary_Then_BrazilianClubsAreRanked()
    {
        // Given / When
        var summary = new PlayerQueryService(TestData.Graph).GetBrazilianClubSummary(5);

        // Then: every listed club exists in the match-data graph as well
        Assert.NotEmpty(summary);
        Assert.All(summary, row =>
        {
            Assert.True(row.Count > 0);
            Assert.True(TestData.Graph.ResolveTeam(row.Club).Found, $"{row.Club} should resolve to a match team");
        });
    }

    [Fact]
    public void Given_TheGraph_When_LookingUpPlayerHistory_Then_PlayerAndMatchWorldsCoexist()
    {
        // Given: Neymar (player world) vs Santos (his formative club, match world)
        var players = new PlayerQueryService(TestData.Graph);
        var neymar = players.Search(new PlayerQueryService.PlayerFilter { Name = "Neymar" });
        var santos = TestData.Graph.ResolveTeam("Santos");

        // When / Then
        Assert.NotEmpty(neymar);
        Assert.True(santos.Found);
        Assert.True(santos.Team!.Matches.Count > 300, "Santos should have a rich match history in the graph");
    }
}
