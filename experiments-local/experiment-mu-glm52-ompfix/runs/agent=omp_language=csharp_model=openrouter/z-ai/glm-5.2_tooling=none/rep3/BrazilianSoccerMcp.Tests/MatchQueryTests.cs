// =============================================================================
// BrazilianSoccerMcp.Tests - Match Query BDD Tests
// -----------------------------------------------------------------------------
// Feature: Match Queries
//   Verify matches can be found by team, opponent, competition and season, and
//   that team-name variations resolve to the same club across source files.
// =============================================================================

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

[Trait("Feature", "Match Queries")]
public class MatchQueryTests : TestBase
{
    // Scenario: Find matches between two teams
    //   Given the match data is loaded
    //   When I search for matches between "Flamengo" and "Fluminense"
    //   Then I should receive a list of matches
    //   And each match should involve both teams
    [Fact]
    public void SearchMatches_BetweenTwoTeams_ReturnsOnlyFixturesInvolvingBoth()
    {
        // Given
        var repo = Repo;

        // When
        var ms = repo.SearchMatches(team: "Flamengo", opponent: "Fluminense").ToList();

        // Then
        Assert.NotEmpty(ms);
        Assert.All(ms, m =>
        {
            var involvesBoth =
                (m.HomeKey == "flamengo" && m.AwayKey == "fluminense") ||
                (m.HomeKey == "fluminense" && m.AwayKey == "flamengo");
            Assert.True(involvesBoth, $"match {m.HomeTeam}-{m.AwayTeam} does not involve both");
        });
    }

    // Scenario: Filter by competition and season
    //   Given the match data is loaded
    //   When I search for Palmeiras in the 2023 Brasileirão
    //   Then every result is a 2023 Brasileirão Série A match involving Palmeiras
    [Fact]
    public void SearchMatches_ByCompetitionAndSeason_FiltersCorrectly()
    {
        // Given / When
        var ms = Repo.SearchMatches(team: "Palmeiras", competition: "Brasileirão", season: 2022).ToList();

        // Then
        Assert.NotEmpty(ms);
        Assert.All(ms, m =>
        {
            Assert.Equal("Brasileirão Série A", m.Competition);
            Assert.Equal(2022, m.Season);
            Assert.True(m.HomeKey == "palmeiras" || m.AwayKey == "palmeiras");
        });
    }

    // Scenario: Team name variations resolve to one club
    //   Given the match data is loaded with different name conventions per file
    //   When I normalize "Palmeiras-SP", "Palmeiras - SP" and "Palmeiras"
    //   Then they all collapse to the canonical key "palmeiras"
    [Theory]
    [InlineData("Palmeiras-SP", "palmeiras")]
    [InlineData("Palmeiras - SP", "palmeiras")]
    [InlineData("Palmeiras", "palmeiras")]
    [InlineData("São Paulo-SP", "sao paulo")]
    [InlineData("Sao Paulo", "sao paulo")]
    [InlineData("Grêmio-RS", "gremio")]
    [InlineData("Gremio", "gremio")]
    public void NormalizeKey_StateSuffixedAndAccentedVariants_CollapseToCanonical(string raw, string expected)
    {
        Assert.Equal(expected, TeamNormalizer.NormalizeKey(raw));
    }

    // Scenario: Atlético cluster keeps state to disambiguate distinct clubs
    //   Given teams named "Atlético-MG", "Athletico-PR", "Atlético-GO"
    //   When normalized
    //   Then they yield distinct keys (mg vs pr vs go) and the PR spellings unify
    [Theory]
    [InlineData("Atlético-MG", "atletico mg")]
    [InlineData("Atletico Mineiro", "atletico mg")]
    [InlineData("Athletico-PR", "atletico pr")]
    [InlineData("Atletico-PR", "atletico pr")]
    [InlineData("Athletico Paranaense", "atletico pr")]
    [InlineData("Atlético-GO", "atletico go")]
    [InlineData("Atletico Goianiense", "atletico go")]
    public void NormalizeKey_AtleticoCluster_KeepsStateAndUnifiesSpellings(string raw, string expected)
    {
        var key = TeamNormalizer.NormalizeKey(raw);
        Assert.Equal(expected, key);
        // MG, PR, GO must remain distinct
        Assert.NotEqual(TeamNormalizer.NormalizeKey("Atlético-MG"), TeamNormalizer.NormalizeKey("Athletico-PR"));
    }

    // Scenario: Cross-file search finds a team in every source that has it
    //   Given the match data is loaded from all files
    //   When I search for Flamengo matches without a competition filter
    //   Then results span more than one competition
    [Fact]
    public void SearchMatches_NoCompetitionFilter_SpansMultipleCompetitions()
    {
        var ms = Repo.SearchMatches(team: "Flamengo").ToList();
        Assert.NotEmpty(ms);
        var comps = ms.Select(m => m.Competition).Distinct().Count();
        Assert.True(comps >= 2, $"expected Flamengo across >=2 competitions, got {comps}");
    }

    // Scenario: Output text is formatted with date, score and competition
    //   Given the match data is loaded
    //   When I call the SearchMatches tool for Flamengo vs Fluminense
    //   Then the returned text contains a date, a score, and a competition name
    [Fact]
    public void SearchMatches_ToolOutput_ContainsDateScoreAndCompetition()
    {
        var text = Tools.SearchMatches(team: "Flamengo", opponent: "Fluminense", limit: 3);
        Assert.Contains("Flamengo", text);
        Assert.Contains("Fluminense", text);
        Assert.Matches(@"\d{4}-\d{2}-\d{2}", text);          // a date
        Assert.Matches(@"\d+-\d+", text);                     // a score
        Assert.Contains("Brasileirão", text);                  // competition
    }
}
