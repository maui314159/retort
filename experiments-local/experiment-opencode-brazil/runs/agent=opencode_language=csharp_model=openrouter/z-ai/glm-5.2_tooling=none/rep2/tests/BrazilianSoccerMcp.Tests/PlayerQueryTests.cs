// BrazilianSoccerMcp.Tests - BDD feature: Player Queries.
// Covers FIFA player search by name, nationality (Brazilian), club and
// position, plus top-rated Brazilian players and roster lookups.
using LightBDD.Framework;
using LightBDD.Framework.Scenarios;

namespace BrazilianSoccerMcp.Tests;

[FeatureDescription(
    "Player queries: search FIFA data by name, nationality, club, position and " +
    "overall rating; top Brazilian players; roster lookups.")]
public class PlayerQueryTests : SoccerFeatureFixture
{
    [Scenario]
    public void Search_players_by_name()
    {
        Runner.RunScenario(
            Given_the_FIFA_data_is_loaded,
            When_I_search_for_players_named_Neymar,
            Then_I_should_find_at_least_one_player_whose_name_contains_Neymar);
    }

    [Scenario]
    public void Top_rated_Brazilian_players()
    {
        Runner.RunScenario(
            Given_the_FIFA_data_is_loaded,
            When_I_request_the_top_10_Brazilian_players,
            Then_every_returned_player_should_be_Brazilian,
            And_the_list_should_be_sorted_by_overall_rating_descending);
    }

    [Scenario]
    public void Find_players_by_club_and_position()
    {
        Runner.RunScenario(
            Given_the_FIFA_data_is_loaded,
            When_I_search_for_forwards_at_Cruzeiro,
            Then_every_returned_player_should_play_for_Cruzeiro,
            And_every_returned_player_should_be_a_forward_position);
    }

    [Scenario]
    public void Filter_players_by_overall_rating()
    {
        Runner.RunScenario(
            Given_the_FIFA_data_is_loaded,
            When_I_search_for_players_with_overall_at_least_85,
            Then_every_returned_player_should_have_overall_at_least_85);
    }

    // --- steps ------------------------------------------------------------

    private void Given_the_FIFA_data_is_loaded() { }

    private void When_I_search_for_players_named_Neymar()
        => ResultPlayers = Query.FindPlayers(name: "Neymar");

    private void When_I_request_the_top_10_Brazilian_players()
        => ResultPlayers = Query.TopBrazilianPlayers(top: 10);

    private void When_I_search_for_forwards_at_Cruzeiro()
        => ResultPlayers = Query.FindPlayers(club: "Cruzeiro", position: "ST");

    private void When_I_search_for_players_with_overall_at_least_85()
        => ResultPlayers = Query.FindPlayers(minOverall: 85, top: 50);

    private void Then_I_should_find_at_least_one_player_whose_name_contains_Neymar()
    {
        Assert.NotEmpty(ResultPlayers);
        Assert.Contains(ResultPlayers, p => p.Name.Contains("Neymar", StringComparison.OrdinalIgnoreCase));
    }

    private void Then_every_returned_player_should_be_Brazilian()
    {
        Assert.NotEmpty(ResultPlayers);
        Assert.All(ResultPlayers, p => Assert.Equal("Brazil", p.Nationality));
    }

    private void And_the_list_should_be_sorted_by_overall_rating_descending()
    {
        for (int i = 1; i < ResultPlayers.Count; i++)
            Assert.True(ResultPlayers[i].Overall <= ResultPlayers[i - 1].Overall);
    }

    private void Then_every_returned_player_should_play_for_Cruzeiro()
    {
        Assert.NotEmpty(ResultPlayers);
        Assert.All(ResultPlayers, p => Assert.Contains("Cruzeiro", p.Club, StringComparison.OrdinalIgnoreCase));
    }

    private void And_every_returned_player_should_be_a_forward_position()
        => Assert.All(ResultPlayers, p => Assert.Equal("ST", p.Position));

    private void Then_every_returned_player_should_have_overall_at_least_85()
    {
        Assert.NotEmpty(ResultPlayers);
        Assert.All(ResultPlayers, p => Assert.True(p.Overall >= 85));
    }
}
