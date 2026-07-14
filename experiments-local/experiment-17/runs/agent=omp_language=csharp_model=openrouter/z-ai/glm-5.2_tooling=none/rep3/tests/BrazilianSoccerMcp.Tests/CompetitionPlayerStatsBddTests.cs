// Brazilian Soccer MCP Server - BDD tests for competition, player & stats queries
// Context: Behaviour-Driven tests (Given/When/Then) for the remaining capability
// groups: competition standings (incl. the historical-era routing and the
// Atlético-MG / Athletico-PR anti-collision check), player queries against the
// FIFA database, and statistical analysis (biggest wins, goal-distribution
// analysis). Assertions are grounded in the real datasets — e.g. Flamengo's 90-
// point 2019 title, Neymar Jr's 92 overall, 827 Brazilian players, 20 players
// per present Brazilian club.

using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

[Collection("Soccer data")]
public sealed class CompetitionPlayerStatsBddTests
{
    private readonly SoccerQueryService _svc;

    public CompetitionPlayerStatsBddTests(SoccerDataFixture fixture) => _svc = fixture.Service;

    // ---------------------------------------------------------------------
    // Competition queries
    // ---------------------------------------------------------------------

    [Fact]
    public void Given_2019_Brasileirao_When_computing_standings_Then_Flamengo_is_champion_with_90_points()
    {
        // Given the 2019 Brasileirão match data
        // When I compute the standings
        var standings = _svc.ComputeStandings("Brasileirão", 2019);

        // Then Flamengo is top with 90 points (champion)
        Assert.NotEmpty(standings);
        var champion = standings[0];
        Assert.Equal("Flamengo", champion.TeamName);
        Assert.Equal(90, champion.Points);
    }

    [Fact]
    public void Given_2019_Brasileirao_When_computing_standings_Then_Atletico_MG_and_Athletico_PR_are_distinct_teams()
    {
        // Given the 2019 Brasileirão data, where "Atletico-MG" and "Atletico-PR"
        // would collide under naive suffix-stripping normalisation
        // When I compute the standings
        var standings = _svc.ComputeStandings("Brasileirão", 2019);
        var names = standings.Select(s => s.TeamName).ToList();

        // Then Atlético Mineiro and Athletico Paranaense appear as separate teams
        // (no merged ~112-point "atletico" phantom).
        Assert.Contains("Atlético Mineiro", names);
        Assert.Contains("Athletico Paranaense", names);
        Assert.DoesNotContain("atletico", names);
    }

    [Fact]
    public void Given_a_pre_2012_season_When_requesting_Brasileirao_standings_Then_it_routes_to_the_historical_dataset()
    {
        // Given a season (2009) that predates the modern Serie A CSV (which starts
        // in 2012) but is covered by the 2003-2019 historical dataset
        // When I request Brasileirão standings for 2009
        var standings = _svc.ComputeStandings("Brasileirão", 2009);

        // Then standings are returned from the historical bucket
        Assert.NotEmpty(standings);
        Assert.All(standings, t => Assert.True(t.Matches > 0));
    }

    [Theory]
    [InlineData("Brasileirão", Competition.Brasileirao)]
    [InlineData("brasileirao serie a", Competition.Brasileirao)]
    [InlineData("Copa do Brasil", Competition.CopaDoBrasil)]
    [InlineData("brazilian cup", Competition.CopaDoBrasil)]
    [InlineData("Libertadores", Competition.Libertadores)]
    [InlineData("Brasileirão (2003-2019)", Competition.BrasileiraoHistorico)]
    [InlineData("historical", Competition.BrasileiraoHistorico)]
    public void Given_competition_text_When_parsed_Then_it_maps_to_the_canonical_enum(string text, Competition expected)
    {
        // Given a free-text competition name from an LLM caller
        // When I parse it
        var parsed = SoccerQueryService.ParseCompetition(text);

        // Then it maps to the canonical competition enum
        Assert.Equal(expected, parsed);
    }

    [Theory]
    [InlineData("all")]
    [InlineData("todos")]
    [InlineData("")]
    [InlineData(null)]
    public void Given_no_competition_filter_When_parsed_Then_it_returns_null_meaning_all(string? text)
    {
        // Given an "all"/empty competition filter
        // When I parse it
        var parsed = SoccerQueryService.ParseCompetition(text);

        // Then it returns null (meaning: no filter)
        Assert.Null(parsed);
    }

    // ---------------------------------------------------------------------
    // Player queries
    // ---------------------------------------------------------------------

    [Fact]
    public void Given_fifa_data_When_searching_by_name_Neymar_Then_Neymar_Jr_is_returned_with_overall_92()
    {
        // Given the FIFA player database is loaded
        // When I search for players named "Neymar"
        var players = _svc.FindPlayers(new PlayerFilter { Name = "Neymar" });

        // Then Neymar Jr is found with an overall rating of 92
        Assert.NotEmpty(players);
        var neymar = players.Single(p => p.Name.Contains("Neymar", StringComparison.OrdinalIgnoreCase));
        Assert.Equal(92, neymar.Overall);
    }

    [Fact]
    public void Given_fifa_data_When_requesting_top_Brazilian_players_Then_results_are_sorted_by_overall_descending()
    {
        // Given the FIFA player database is loaded
        // When I request the top 5 Brazilian players by overall rating
        var top = _svc.FindPlayers(new PlayerFilter { Nationality = "Brazil", Limit = 5, SortBy = "overall" });

        // Then 5 players are returned, sorted by overall descending, and the
        // highest-rated Brazilian is Neymar Jr (92).
        Assert.Equal(5, top.Count);
        for (int i = 1; i < top.Count; i++)
            Assert.True(top[i - 1].Overall >= top[i].Overall);
        Assert.Contains(top, p => p.Name.Contains("Neymar", StringComparison.OrdinalIgnoreCase));
        Assert.Equal(92, top[0].Overall);
    }

    [Fact]
    public void Given_fifa_data_When_filtering_by_club_Santos_Then_exactly_twenty_players_are_returned()
    {
        // Given the FIFA database contains 20 players per Brazilian club present
        // When I filter players by club "Santos"
        var players = _svc.FindPlayers(new PlayerFilter { Club = "Santos" });

        // Then exactly 20 Santos players are returned, all belonging to Santos
        Assert.Equal(20, players.Count);
        Assert.All(players, p => Assert.Equal("Santos", p.ClubKey));
    }

    [Fact]
    public void Given_fifa_data_When_filtering_by_position_ST_Then_all_results_are_forwards()
    {
        // Given the FIFA database is loaded
        // When I filter players by position "ST" (striker)
        var players = _svc.FindPlayers(new PlayerFilter { Position = "ST", Limit = 20 });

        // Then every returned player is a striker
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Equal("ST", p.Position));
    }

    [Fact]
    public void Given_fifa_data_When_counting_Brazilian_players_Then_there_are_827()
    {
        // Given the FIFA database is loaded
        // When I retrieve all Brazilian players
        var brazilians = _svc.FindPlayers(new PlayerFilter { Nationality = "Brazil" });

        // Then 827 Brazilian players are present in the dataset
        Assert.Equal(827, brazilians.Count);
    }

    // ---------------------------------------------------------------------
    // Statistical analysis
    // ---------------------------------------------------------------------

    [Fact]
    public void Given_scored_matches_When_computing_biggest_wins_Then_results_are_sorted_by_goal_difference_descending()
    {
        // Given the match data with scores
        // When I request the 10 biggest wins
        var wins = _svc.BiggestWins(null, null, 10);

        // Then 10 non-draw matches are returned, sorted by goal difference (then
        // total goals) descending, and the top margin is at least 5 goals.
        Assert.Equal(10, wins.Count);
        Assert.All(wins, m => Assert.NotEqual(m.HomeGoal, m.AwayGoal));
        for (int i = 1; i < wins.Count; i++)
        {
            var prev = wins[i - 1];
            var curr = wins[i];
            Assert.True(prev.GoalDifference > curr.GoalDifference ||
                        (prev.GoalDifference == curr.GoalDifference && prev.TotalGoals >= curr.TotalGoals));
        }
        Assert.True(wins[0].GoalDifference >= 5);
    }

    [Fact]
    public void Given_Brasileirao_matches_When_computing_goal_analysis_Then_rates_sum_to_one()
    {
        // Given Brasileirão matches with scores
        // When I compute the goal-distribution analysis
        var g = _svc.ComputeGoalsAnalysis(Competition.Brasileirao, null);

        // Then matches are counted and home-win + away-win + draw rates sum to 1.0
        Assert.True(g.Matches > 0);
        Assert.True(g.AvgGoals > 0);
        var sum = g.HomeWinRate + g.AwayWinRate + g.DrawRate;
        Assert.InRange(sum, 0.999, 1.001);
    }

    [Fact]
    public void Given_a_competition_and_season_When_filtering_biggest_wins_Then_only_that_slice_is_returned()
    {
        // Given the 2019 Brasileirão matches
        // When I request the biggest wins for that slice
        var wins = _svc.BiggestWins(Competition.Brasileirao, 2019, 5);

        // Then every returned match is a 2019 Brasileirão match
        Assert.NotEmpty(wins);
        Assert.All(wins, m =>
        {
            Assert.Equal(Competition.Brasileirao, m.Competition);
            Assert.Equal(2019, m.Season);
        });
    }
}
