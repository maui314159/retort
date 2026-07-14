using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD-style (Given/When/Then) tests for match-level queries.
/// Maps to the "Feature: Match Queries" scenarios in TASK.md.
/// </summary>
[Collection("DataCollection")]
public class MatchQueryBddTests
{
    private readonly DataFixture _fixture;

    public MatchQueryBddTests(DataFixture fixture) => _fixture = fixture;

    [Fact]
    public void Find_matches_between_two_teams_returns_list_with_date_scores_competition()
    {
        // Given the match data is loaded
        var svc = new MatchService(_fixture.Repository);
        Assert.NotEmpty(_fixture.Repository.Matches);

        // When I search for matches between "Flamengo" and "Fluminense"
        var matches = svc.Search(team: "Flamengo", opponent: "Fluminense");

        // Then I should receive a list of matches
        Assert.NotEmpty(matches);

        // And each match should have date, scores, and competition
        Assert.All(matches, m =>
        {
            Assert.True(m.Date != DateTime.MinValue, "match date must be parsed");
            Assert.True(m.HomeGoal >= 0 && m.AwayGoal >= 0, "scores must be set");
            Assert.False(string.IsNullOrEmpty(m.Competition), "competition must be set");
            Assert.True(
                TeamNameNormalizer.NormalizeKey(m.HomeTeam) == "flamengo" ||
                TeamNameNormalizer.NormalizeKey(m.AwayTeam) == "flamengo",
                "one side must be Flamengo");
        });
    }

    [Fact]
    public void Find_matches_by_team_across_all_files()
    {
        // Given the match data is loaded
        var svc = new MatchService(_fixture.Repository);

        // When I request all Palmeiras matches
        var matches = svc.Search(team: "Palmeiras");

        // Then the result is non-empty and contains only Palmeiras matches
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.True(
                TeamNameNormalizer.NormalizeKey(m.HomeTeam) == "palmeiras" ||
                TeamNameNormalizer.NormalizeKey(m.AwayTeam) == "palmeiras");
        });
    }

    [Fact]
    public void Find_matches_by_team_and_season()
    {
        // Given the match data is loaded
        var svc = new MatchService(_fixture.Repository);

        // When I search for Palmeiras matches in 2023
        var matches = svc.Search(team: "Palmeiras", season: 2023);

        // Then all matches belong to season 2023
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(2023, m.Season));
    }

    [Fact]
    public void Find_matches_by_competition_filter()
    {
        // Given the match data is loaded
        var svc = new MatchService(_fixture.Repository);

        // When I search for CopaDoBrasil matches in a season present in the data
        var seasons = new CompetitionService(_fixture.Repository).GetSeasons("CopaDoBrasil");
        Assert.NotEmpty(seasons);
        var season = seasons.First();
        var matches = svc.Search(competition: "CopaDoBrasil", season: season);

        // Then all matches belong to the Copa do Brasil competition
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.Contains("CopaDoBrasil", m.Competition, StringComparison.OrdinalIgnoreCase);
        });
    }

    [Fact]
    public void Head_to_head_returns_wins_draws_losses_and_match_list()
    {
        // Given the match data is loaded
        var svc = new MatchService(_fixture.Repository);

        // When I compute the head-to-head for Flamengo vs Fluminense
        var h2h = svc.HeadToHead("Flamengo", "Fluminense");

        // Then the result contains a consistent tally
        Assert.True(h2h.WinsA + h2h.WinsB + h2h.Draws == h2h.Matches.Count,
            "wins + draws + losses must equal total matches");
        Assert.NotEmpty(h2h.Matches);
    }

    [Fact]
    public void Team_name_variations_are_normalized()
    {
        // Given "Palmeiras-SP" appears in the source
        // When normalizing
        var withSuffix = TeamNameNormalizer.NormalizeKey("Palmeiras-SP");
        var withoutSuffix = TeamNameNormalizer.NormalizeKey("Palmeiras");

        // Then both resolve to the same key
        Assert.Equal(withoutSuffix, withSuffix);
        Assert.Equal("palmeiras", withSuffix);
    }

    [Fact]
    public void Accented_team_names_are_folded()
    {
        // Given accented names like "São Paulo"
        // When normalizing
        var key = TeamNameNormalizer.NormalizeKey("São Paulo");

        // Then the key is ASCII-only
        Assert.Equal("saopaulo", key);
    }
}
