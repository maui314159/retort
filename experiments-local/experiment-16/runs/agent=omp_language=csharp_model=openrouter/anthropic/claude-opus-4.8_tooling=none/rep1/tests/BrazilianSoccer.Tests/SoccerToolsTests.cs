// =============================================================================
// Context: Brazilian Soccer MCP Server — MCP tool-layer BDD tests.
//
// Verifies the SoccerTools surface that the LLM actually calls: lenient
// competition-string parsing, and that each tool returns formatted text matching
// the spec's example layouts (match lists with head-to-head, ranked players,
// standings marked with Champion, aggregate stats). Shares the same data fixture
// so the CSVs load once for the whole assembly.
// =============================================================================
using BrazilianSoccer.Core;
using BrazilianSoccer.Mcp;
using Xunit;

namespace BrazilianSoccer.Tests;

public sealed class SoccerToolsTests : IClassFixture<SoccerDataFixture>
{
    private readonly SoccerTools _tools;

    public SoccerToolsTests(SoccerDataFixture fx)
    {
        _tools = new SoccerTools(fx.Engine);
    }

    [Theory]
    [InlineData("brasileirao", CompetitionFilter.BrasileiraoSerieA)]
    [InlineData("Brasileirão", CompetitionFilter.BrasileiraoSerieA)]
    [InlineData("serie a", CompetitionFilter.BrasileiraoSerieA)]
    [InlineData("Serie B", CompetitionFilter.BrasileiraoSerieB)]
    [InlineData("copa do brasil", CompetitionFilter.CopaDoBrasil)]
    [InlineData("Libertadores", CompetitionFilter.Libertadores)]
    [InlineData("", CompetitionFilter.Any)]
    [InlineData(null, CompetitionFilter.Any)]
    public void Given_a_competition_string_When_parsed_Then_correct_filter(string? raw, CompetitionFilter expected)
    {
        // Given user competition text, When parsed, Then mapped to the right filter.
        Assert.Equal(expected, SoccerTools.ParseCompetition(raw));
    }

    [Fact]
    public void Given_two_teams_When_find_matches_Then_output_has_matches_and_head_to_head()
    {
        // Given Flamengo vs Fluminense, When find_matches runs, Then output lists matches and a head-to-head block.
        var text = _tools.FindMatches(team: "Flamengo", opponent: "Fluminense");
        Assert.Contains("Flamengo", text);
        Assert.Contains("Fluminense", text);
        Assert.Contains("Head-to-head", text);
    }

    [Fact]
    public void Given_no_matches_When_head_to_head_Then_explains_absence()
    {
        // Given a nonsense pairing, When head_to_head runs, Then it reports no matches rather than throwing.
        var text = _tools.HeadToHead("Flamengo", "ZZZ Nonexistent FC");
        Assert.Contains("No matches found", text);
    }

    [Fact]
    public void Given_brazil_When_find_players_Then_ranked_list_returned()
    {
        // Given nationality Brazil, When find_players runs, Then a numbered, Overall-sorted list returns.
        var text = _tools.FindPlayers(nationality: "Brazil", limit: 5);
        Assert.Contains("1. ", text);
        Assert.Contains("Overall:", text);
        Assert.Contains("Brazil", text);
    }

    [Fact]
    public void Given_a_known_player_When_profile_requested_Then_profile_returned()
    {
        // Given a player name, When player_profile runs, Then a profile with nationality is returned.
        var text = _tools.PlayerProfile("Neymar");
        Assert.Contains("Nationality:", text);
        Assert.Contains("Overall:", text);
    }

    [Fact]
    public void Given_2019_When_standings_requested_Then_champion_is_marked()
    {
        // Given 2019, When standings runs, Then position 1 is marked Champion.
        var text = _tools.Standings(2019);
        Assert.Contains("Final Standings", text);
        Assert.Contains("1. ", text);
        Assert.Contains("Champion", text);
    }

    [Fact]
    public void Given_serie_a_When_competition_stats_Then_average_goals_reported()
    {
        // Given Serie A, When competition_stats runs, Then it reports average goals per match.
        var text = _tools.CompetitionStats(competition: "serie a");
        Assert.Contains("Average goals per match:", text);
        Assert.Contains("Home win rate:", text);
    }

    [Fact]
    public void Given_data_When_overview_requested_Then_counts_reported()
    {
        // Given loaded data, When dataset_overview runs, Then it reports match and player counts.
        var text = _tools.DatasetOverview();
        Assert.Contains("matches", text);
        Assert.Contains("players", text);
    }
}
