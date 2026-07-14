// BrazilianSoccerMcp.Tests - BDD feature: Match Queries.
// Mirrors the spec's "Feature: Match Queries" scenarios: finding matches
// between two teams and verifying each result carries date, scores and
// competition. Also covers by-team, by-season and most-recent lookups.
using BrazilianSoccerMcp.Core.Data;
using LightBDD.Framework;
using LightBDD.Framework.Scenarios;
using LightBDD.XUnit2;

namespace BrazilianSoccerMcp.Tests;

[FeatureDescription(
    "Match queries: find matches by team, between two teams, by competition/season, " +
    "and most-recent lookups across all five match CSV files.")]
public class MatchQueryTests : SoccerFeatureFixture
{
    [Scenario]
    public void Find_matches_between_two_teams()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_search_for_matches_between_Flamengo_and_Fluminense,
            Then_I_should_receive_a_list_of_matches,
            And_each_match_should_have_date_scores_and_competition);
    }

    [Scenario]
    public void Find_matches_by_team_filtered_by_season()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_request_Palmeiras_matches_for_season_2023,
            Then_every_returned_match_should_involve_Palmeiras,
            And_every_returned_match_should_be_in_season_2023);
    }

    [Scenario]
    public void Find_matches_by_team_filtered_by_competition()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_request_Copa_do_Brasil_matches_for_Flamengo,
            Then_every_returned_match_should_be_Copa_do_Brasil);
    }

    [Scenario]
    public void Find_most_recent_match_between_two_teams()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_request_the_most_recent_match_between_Flamengo_and_Corinthians,
            Then_I_should_receive_a_single_match,
            And_the_match_should_have_a_valid_score);
    }

    [Scenario]
    public void Find_derbies_in_a_season()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_request_derbies_for_season_2023,
            Then_every_returned_match_should_be_between_known_rivals);
    }

    // --- steps ------------------------------------------------------------

    private void Given_the_match_data_is_loaded() { }

    private void When_I_search_for_matches_between_Flamengo_and_Fluminense()
        => ResultMatches = Query.FindMatchesBetweenTeams("Flamengo", "Fluminense");

    private void When_I_request_Palmeiras_matches_for_season_2023()
        => ResultMatches = Query.FindMatchesByTeam("Palmeiras", season: 2023);

    private void When_I_request_Copa_do_Brasil_matches_for_Flamengo()
        => ResultMatches = Query.FindMatchesByTeam("Flamengo", competition: Competition.CopaDoBrasil);

    private void When_I_request_the_most_recent_match_between_Flamengo_and_Corinthians()
        => ResultMatch = Query.FindMostRecentMatch("Flamengo", "Corinthians");

    private void When_I_request_derbies_for_season_2023()
        => ResultMatches = Query.FindDerbies(season: 2023);

    private void Then_I_should_receive_a_list_of_matches()
        => Assert.NotEmpty(ResultMatches);

    private void And_each_match_should_have_date_scores_and_competition()
    {
        foreach (var m in ResultMatches)
        {
            Assert.True(m.Date > DateTime.MinValue, "match date parsed");
            Assert.True(m.HomeGoal >= 0 && m.AwayGoal >= 0, "scores parsed");
            Assert.True(!string.IsNullOrEmpty(m.HomeTeam) && !string.IsNullOrEmpty(m.AwayTeam));
            Assert.True(!string.IsNullOrEmpty(m.RawCompetition));
        }
    }

    private void Then_every_returned_match_should_involve_Palmeiras()
    {
        Assert.NotEmpty(ResultMatches);
        foreach (var m in ResultMatches)
            Assert.True(TeamInvolves(m, "Palmeiras"));
    }

    private void And_every_returned_match_should_be_in_season_2023()
    {
        foreach (var m in ResultMatches)
            Assert.Equal(2023, m.Season);
    }

    private void Then_every_returned_match_should_be_Copa_do_Brasil()
    {
        Assert.NotEmpty(ResultMatches);
        foreach (var m in ResultMatches)
            Assert.Equal(Competition.CopaDoBrasil, m.Competition);
    }

    private void Then_I_should_receive_a_single_match()
    {
        Assert.NotNull(ResultMatch);
        Assert.True(TeamInvolves(ResultMatch!, "Flamengo"));
        Assert.True(TeamInvolves(ResultMatch!, "Corinthians"));
    }

    private void And_the_match_should_have_a_valid_score()
        => Assert.True(ResultMatch!.HomeGoal >= 0 && ResultMatch!.AwayGoal >= 0);

    private void Then_every_returned_match_should_be_between_known_rivals()
    {
        Assert.NotEmpty(ResultMatches);
        foreach (var m in ResultMatches)
            Assert.True(IsDerby(m), $"expected derby, got {m.HomeTeam} vs {m.AwayTeam}");
    }

    // --- helpers ----------------------------------------------------------
    private static bool TeamInvolves(Match m, string team)
    {
        var key = TeamNameNormalizer.BaseKey(team);
        return TeamNameNormalizer.BaseKey(m.HomeTeam) == key
            || TeamNameNormalizer.BaseKey(m.AwayTeam) == key;
    }

    private static bool IsDerby(Match m)
    {
        var h = TeamNameNormalizer.BaseKey(m.HomeTeam);
        var a = TeamNameNormalizer.BaseKey(m.AwayTeam);
        var derbies = new[]
        {
            (TeamNameNormalizer.BaseKey("Flamengo"), TeamNameNormalizer.BaseKey("Fluminense")),
            (TeamNameNormalizer.BaseKey("Flamengo"), TeamNameNormalizer.BaseKey("Vasco")),
            (TeamNameNormalizer.BaseKey("Corinthians"), TeamNameNormalizer.BaseKey("Palmeiras")),
            (TeamNameNormalizer.BaseKey("Corinthians"), TeamNameNormalizer.BaseKey("São Paulo")),
            (TeamNameNormalizer.BaseKey("Palmeiras"), TeamNameNormalizer.BaseKey("São Paulo")),
            (TeamNameNormalizer.BaseKey("Santos"), TeamNameNormalizer.BaseKey("São Paulo")),
            (TeamNameNormalizer.BaseKey("Santos"), TeamNameNormalizer.BaseKey("Corinthians")),
            (TeamNameNormalizer.BaseKey("Grêmio"), TeamNameNormalizer.BaseKey("Internacional")),
            (TeamNameNormalizer.BaseKey("Atlético-MG"), TeamNameNormalizer.BaseKey("Cruzeiro")),
            (TeamNameNormalizer.BaseKey("Atlético Mineiro"), TeamNameNormalizer.BaseKey("Cruzeiro")),
            (TeamNameNormalizer.BaseKey("Bahia"), TeamNameNormalizer.BaseKey("Vitória")),
            (TeamNameNormalizer.BaseKey("Fortaleza"), TeamNameNormalizer.BaseKey("Ceará")),
        };
        return derbies.Contains((h, a)) || derbies.Contains((a, h));
    }
}
