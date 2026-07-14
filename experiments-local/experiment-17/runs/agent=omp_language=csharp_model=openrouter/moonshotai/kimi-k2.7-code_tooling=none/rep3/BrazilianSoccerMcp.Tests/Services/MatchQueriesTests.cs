using BrazilianSoccerMcp.Server.Data;
using BrazilianSoccerMcp.Server.Services;
using BrazilianSoccerMcp.Tests.Data;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Services;

[Collection("SoccerData")]
public sealed class MatchQueriesTests
{
    private readonly SoccerDataContext _context;

    public MatchQueriesTests(DataFixture fixture)
    {
        _context = fixture.Context;
    }

    [Fact]
    public void Given_the_match_data_is_loaded_When_searching_for_matches_between_Flamengo_and_Fluminense_Then_should_receive_matches_with_scores_and_competition()
    {
        var service = new MatchService(_context);

        var matches = service.FindMatches(team: "Flamengo", opponent: "Fluminense");

        matches.Should().NotBeEmpty();
        matches.Should().OnlyContain(m =>
            m.InvolvesTeam("Flamengo") && m.InvolvesTeam("Fluminense"));
        matches.Should().OnlyContain(m => m.HomeGoals >= 0 && m.AwayGoals >= 0);
        matches.Should().OnlyContain(m => !string.IsNullOrWhiteSpace(m.Competition));
    }

    [Fact]
    public void Given_the_match_data_is_loaded_When_filtering_by_season_and_competition_Then_should_return_only_matching_matches()
    {
        var service = new MatchService(_context);

        var matches = service.FindMatches(team: "Palmeiras", competition: "Brasileirão", season: 2019);

        matches.Should().NotBeEmpty();
        matches.Should().OnlyContain(m => m.InvolvesTeam("Palmeiras"));
        matches.Should().OnlyContain(m => m.Season == 2019);
    }
}
