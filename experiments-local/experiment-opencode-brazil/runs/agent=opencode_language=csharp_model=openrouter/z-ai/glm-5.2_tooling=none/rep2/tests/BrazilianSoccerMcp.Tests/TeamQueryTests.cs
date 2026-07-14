// BrazilianSoccerMcp.Tests - BDD feature: Team Queries.
// Covers win/draw/loss and goal statistics, head-to-head comparisons and
// home/away records, including the same-base disambiguation case
// (Atletico-MG vs Atletico-PR stay separate).
using BrazilianSoccerMcp.Core.Data;
using LightBDD.Framework;
using LightBDD.Framework.Scenarios;

namespace BrazilianSoccerMcp.Tests;

[FeatureDescription(
    "Team queries: win/draw/loss records, goals, head-to-head comparisons, " +
    "home/away records and same-base club disambiguation.")]
public class TeamQueryTests : SoccerFeatureFixture
{
    [Scenario]
    public void Get_team_statistics_for_a_season()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_request_statistics_for_Palmeiras_in_season_2023,
            Then_I_should_receive_wins_losses_draws_and_goals,
            And_the_match_count_should_equal_wins_plus_draws_plus_losses);
    }

    [Scenario]
    public void Compare_two_teams_head_to_head()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_compare_Palmeiras_and_Santos_head_to_head,
            Then_I_should_receive_wins_draws_and_losses_for_both_teams,
            And_the_sum_of_results_should_equal_the_match_count);
    }

    [Scenario]
    public void Same_base_clubs_are_not_merged()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_request_2019_Brasileirao_standings,
            Then_Atletico_MG_and_Atletico_PR_should_be_distinct_rows);
    }

    [Scenario]
    public void Best_home_records_are_ranked()
    {
        Runner.RunScenario(
            Given_the_match_data_is_loaded,
            When_I_request_the_best_home_records,
            Then_the_first_ranked_team_should_have_a_nonzero_win_rate);
    }

    // --- steps ------------------------------------------------------------

    private void Given_the_match_data_is_loaded() { }

    private void When_I_request_statistics_for_Palmeiras_in_season_2023()
        => ResultStats = Query.GetTeamStats("Palmeiras", season: 2023);

    private void When_I_compare_Palmeiras_and_Santos_head_to_head()
        => ResultH2H = Query.GetHeadToHead("Palmeiras", "Santos");

    private void When_I_request_2019_Brasileirao_standings()
        => ResultStandings = Query.GetStandings(2019, Competition.Brasileirao);

    private void When_I_request_the_best_home_records()
        => ResultStats = Query.BestHomeRecords(minMatches: 15).First();

    private void Then_I_should_receive_wins_losses_draws_and_goals()
    {
        Assert.NotNull(ResultStats);
        Assert.True(ResultStats!.Matches > 0);
        Assert.True(ResultStats.GoalsFor >= 0);
        Assert.True(ResultStats.GoalsAgainst >= 0);
    }

    private void And_the_match_count_should_equal_wins_plus_draws_plus_losses()
        => Assert.Equal(ResultStats!.Matches, ResultStats.Wins + ResultStats.Draws + ResultStats.Losses);

    private void Then_I_should_receive_wins_draws_and_losses_for_both_teams()
    {
        Assert.NotNull(ResultH2H);
        Assert.True(ResultH2H!.Matches > 0);
        Assert.Equal(ResultH2H.Matches, ResultH2H.TeamAWins + ResultH2H.TeamBWins + ResultH2H.Draws);
    }

    private void And_the_sum_of_results_should_equal_the_match_count()
        => Assert.Equal(ResultH2H!.Matches, ResultH2H.TeamAWins + ResultH2H.TeamBWins + ResultH2H.Draws);

    private void Then_Atletico_MG_and_Atletico_PR_should_be_distinct_rows()
    {
        var atleticoRows = ResultStandings.Where(r =>
            r.Team.StartsWith("Atletico", StringComparison.OrdinalIgnoreCase)).ToList();
        Assert.True(atleticoRows.Count >= 2,
            $"expected at least 2 Atletico rows, got {atleticoRows.Count}: " +
            string.Join(", ", atleticoRows.Select(r => r.Team)));
        // Both state-coded variants should appear.
        Assert.Contains(atleticoRows, r => r.Team.Contains("MG"));
        Assert.Contains(atleticoRows, r => r.Team.Contains("PR"));
    }

    private void Then_the_first_ranked_team_should_have_a_nonzero_win_rate()
        => Assert.True(ResultStats!.HomeWinRate > 0);
}
