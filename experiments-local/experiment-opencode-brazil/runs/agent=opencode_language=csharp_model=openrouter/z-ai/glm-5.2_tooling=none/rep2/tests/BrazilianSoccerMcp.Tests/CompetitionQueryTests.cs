// BrazilianSoccerMcp.Tests - BDD feature: Competition Queries.
// Verifies that standings are calculated from match results, that the
// champion for 2019 Brasileirao is Flamengo (a known real-world fact the data
// must reproduce), and that available seasons are enumerated.
using BrazilianSoccerMcp.Core.Data;
using LightBDD.Framework;
using LightBDD.Framework.Scenarios;

namespace BrazilianSoccerMcp.Tests;

[FeatureDescription(
    "Competition queries: standings calculated from match results, champion " +
    "identification, and available season enumeration.")]
public class CompetitionQueryTests : SoccerFeatureFixture
{
    [Scenario]
    public void Calculate_2019_Brasileirao_standings_from_matches()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_request_the_2019_Brasileirao_standings,
            Then_I_should_receive_a_full_table,
            And_every_team_should_have_38_matches,
            And_Flamengo_should_be_the_champion_with_90_points);
    }

    [Scenario]
    public void List_available_seasons()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_request_available_seasons_for_Brasileirao,
            Then_the_season_list_should_include_2019_and_2022);
    }

    // --- steps ------------------------------------------------------------

    private void Given_the_match_data_is_loaded() { }

    private void When_I_request_the_2019_Brasileirao_standings()
        => ResultStandings = Query.GetStandings(2019, Competition.Brasileirao);

    private void When_I_request_available_seasons_for_Brasileirao()
        => ResultText = string.Join(",", Query.AvailableSeasons(Competition.Brasileirao));

    private void Then_I_should_receive_a_full_table()
    {
        Assert.NotEmpty(ResultStandings);
        Assert.Equal(1, ResultStandings.First().Position);
    }

    private void And_every_team_should_have_38_matches()
    {
        // A full Brasileirao Serie A season is 38 matches (20 teams, double round robin).
        Assert.All(ResultStandings, r => Assert.Equal(38, r.Played));
    }

    private void And_Flamengo_should_be_the_champion_with_90_points()
    {
        var champion = ResultStandings.Single(r => r.Champion);
        Assert.Equal("Flamengo", champion.Team);
        Assert.Equal(90, champion.Points);
    }

    private void Then_the_season_list_should_include_2019_and_2022()
    {
        Assert.Contains("2019", ResultText);
        Assert.Contains("2022", ResultText);
    }
}
