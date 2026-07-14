// Brazilian Soccer MCP Server - BDD tests for match & team queries
// Context: Behaviour-Driven tests structured as Given/When/Then. Each test name
// spells out the GWT scenario and the body carries the matching Gherkin-style
// comments. These cover the "Match Queries" and "Team Queries" capability
// groups from the spec, plus the team-name-normalisation invariants that are
// load-bearing for every other aggregate (alias collision between
// Atlético-MG / Athletico-PR / Atlético-GO would corrupt standings and H2H).

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

[Collection("Soccer data")]
public sealed class MatchAndTeamBddTests
{
    private readonly SoccerQueryService _svc;

    public MatchAndTeamBddTests(SoccerDataFixture fixture) => _svc = fixture.Service;

    // ---------------------------------------------------------------------
    // Match queries
    // ---------------------------------------------------------------------

    [Fact]
    public void Given_match_data_loaded_When_searching_Flamengo_vs_Fluminense_Then_each_match_has_date_scores_and_competition()
    {
        // Given the match data is loaded
        // When I search for matches between "Flamengo" and "Fluminense"
        var matches = _svc.FindMatches(new MatchFilter { Team = "Flamengo", Opponent = "Fluminense" });

        // Then I should receive a list of matches
        Assert.NotEmpty(matches);
        // And each match should involve both teams and carry date, scores and competition
        foreach (var m in matches)
        {
            Assert.True(m.HomeTeamKey == "Flamengo" || m.AwayTeamKey == "Flamengo");
            Assert.True(m.HomeTeamKey == "Fluminense" || m.AwayTeamKey == "Fluminense");
            Assert.False(string.IsNullOrEmpty(m.CompetitionLabel));
        }
        // And the list is ordered newest-first
        for (int i = 1; i < matches.Count; i++)
            Assert.True(matches[i - 1].Date >= matches[i].Date);
    }

    [Fact]
    public void Given_match_data_loaded_When_searching_Palmeiras_in_2023_Then_results_come_from_the_extended_stats_dataset()
    {
        // Given the match data is loaded
        // When I search for Palmeiras matches in season 2023
        var matches = _svc.FindMatches(new MatchFilter { Team = "Palmeiras", Season = 2023 });

        // Then I should receive matches (the modern Serie A CSV ends in 2022, but
        // the BR-Football extended stats dataset covers 2023, so cross-file
        // search still answers the question).
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(2023, m.Season));
    }

    [Fact]
    public void Given_match_data_loaded_When_searching_by_competition_filter_Then_only_that_competition_is_returned()
    {
        // Given the match data is loaded
        // When I search Libertadores matches in 2019
        var matches = _svc.FindMatches(new MatchFilter { Competition = Competition.Libertadores, Season = 2019 });

        // Then every match is a Libertadores match from that season
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.Equal(Competition.Libertadores, m.Competition);
            Assert.Equal(2019, m.Season);
        });
    }

    [Fact]
    public void Given_match_data_loaded_When_asking_for_last_Flamengo_match_Then_the_most_recent_is_returned()
    {
        // Given the match data is loaded
        // When I request the last match for Flamengo
        var last = _svc.LastMatch("Flamengo");

        // Then a match is returned and it is the newest Flamengo fixture in the data
        Assert.NotNull(last);
        var allFla = _svc.FindMatches(new MatchFilter { Team = "Flamengo" });
        Assert.Equal(allFla[0].Date, last!.Date);
    }

    // ---------------------------------------------------------------------
    // Team queries
    // ---------------------------------------------------------------------

    [Fact]
    public void Given_match_data_loaded_When_requesting_Flamengo_2019_statistics_Then_wins_plus_draws_plus_losses_equals_matches()
    {
        // Given the match data is loaded
        // When I request statistics for Flamengo in the 2019 Brasileirão
        var stats = _svc.ComputeTeamStats("Flamengo", Competition.Brasileirao, 2019, Venue.All);

        // Then the win/draw/loss tally is consistent and Flamengo scored 90 points (champions)
        Assert.NotEmpty(_svc.FindMatches(new MatchFilter { Team = "Flamengo", Competition = Competition.Brasileirao, Season = 2019 }));
        Assert.Equal(stats.Matches, stats.Wins + stats.Draws + stats.Losses);
        Assert.Equal(90, stats.Points);
    }

    [Fact]
    public void Given_match_data_loaded_When_requesting_home_record_Then_only_home_matches_are_counted()
    {
        // Given the match data is loaded
        // When I request Flamengo's home record for 2019 Brasileirão
        var home = _svc.ComputeTeamStats("Flamengo", Competition.Brasileirao, 2019, Venue.Home);
        var away = _svc.ComputeTeamStats("Flamengo", Competition.Brasileirao, 2019, Venue.Away);

        // Then home + away matches equal the overall total
        var all = _svc.ComputeTeamStats("Flamengo", Competition.Brasileirao, 2019, Venue.All);
        Assert.Equal(all.Matches, home.Matches + away.Matches);
        Assert.True(home.Matches > 0 && away.Matches > 0);
    }

    [Fact]
    public void Given_two_teams_When_computing_head_to_head_Then_win_counts_plus_draws_equals_total_matches()
    {
        // Given the match data is loaded
        // When I compare Palmeiras and Santos head-to-head
        var hh = _svc.ComputeHeadToHead("Palmeiras", "Santos", null, null);

        // Then the result tallies are internally consistent
        Assert.Equal(hh.Matches.Count, hh.Team1Wins + hh.Team2Wins + hh.Draws);
        Assert.All(hh.Matches, m =>
        {
            var keys = new[] { m.HomeTeamKey, m.AwayTeamKey };
            Assert.Contains("Palmeiras", keys);
            Assert.Contains("Santos", keys);
        });
    }

    [Fact]
    public void Given_a_team_When_listing_competitions_Then_Palmeiras_appears_in_more_than_one_competition()
    {
        // Given the match data is loaded
        // When I list competitions Palmeiras has played in
        var comps = _svc.TeamCompetitions("Palmeiras");

        // Then Palmeiras appears in the Brasileirão and at least one other competition
        Assert.NotEmpty(comps);
        Assert.Contains(Competition.Brasileirao, comps.Keys);
        Assert.True(comps.Count > 1, "Palmeiras should appear in more than one competition across the datasets.");
    }

    // ---------------------------------------------------------------------
    // Team-name normalisation
    // ---------------------------------------------------------------------

    [Theory]
    [InlineData("Flamengo", "Flamengo")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("flamengo", "Flamengo")]
    [InlineData("São Paulo FC", "São Paulo")]
    [InlineData("Sao Paulo", "São Paulo")]
    [InlineData("América - MG", "América Mineiro")]
    [InlineData("América-MG", "América Mineiro")]
    [InlineData("Atletico-MG", "Atlético Mineiro")]
    [InlineData("Atlético Mineiro", "Atlético Mineiro")]
    public void Given_team_name_variants_When_normalised_Then_they_map_to_one_canonical_name(string raw, string expected)
    {
        // Given team names appear in many variants across the datasets
        // When I normalise each variant
        var key = TeamNormalizer.Normalize(raw);

        // Then they all resolve to the same canonical name
        Assert.Equal(expected, key);
    }

    [Fact]
    public void Given_short_named_state_suffixed_clubs_When_normalised_Then_they_do_not_collide()
    {
        // Given clubs that share a base name but differ by state (Atletico-MG,
        // Atletico-PR, Atletico-GO) — a naive suffix-stripping normaliser would
        // collapse all three into "atletico" and corrupt standings.
        // When I normalise each
        var mg = TeamNormalizer.Normalize("Atletico-MG");
        var pr = TeamNormalizer.Normalize("Atletico-PR");
        var go = TeamNormalizer.Normalize("Atletico-GO");

        // Then they resolve to three distinct canonical clubs
        Assert.Equal("Atlético Mineiro", mg);
        Assert.Equal("Athletico Paranaense", pr);
        Assert.NotEqual(mg, pr);
        Assert.NotEqual(mg, go);
        Assert.NotEqual(pr, go);
    }

    [Fact]
    public void Given_unknown_team_When_normalised_Then_it_falls_back_to_a_stable_key()
    {
        // Given a team not in the alias map (an international Libertadores opponent)
        // When I normalise it
        var key = TeamNormalizer.Normalize("Barcelona-EQU");

        // Then it falls back to a stable, lowercased, suffix-preserving key
        Assert.Equal("barcelona-equ", key);
    }

    [Fact]
    public void Given_parenthetical_annotated_team_When_displayed_Then_the_annotation_is_stripped()
    {
        // Given a team name carrying a parenthetical annotation
        // When I ask for its display name
        var display = TeamNormalizer.DisplayName("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ");

        // Then the parenthetical is removed but the rest is preserved
        Assert.DoesNotContain("antigo", display);
        Assert.Contains("Boavista Sport Club", display);
    }
}
