using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Team Name Normalization
///   The datasets use different naming conventions (with/without state
///   suffix, full legal names). Matching must be consistent.
/// </summary>
public class NormalizationTests
{
    /*
     * Scenario: State suffixes are ignored
     *   Given names like "Palmeiras-SP" and "Palmeiras"
     *   When normalized
     *   Then they produce the same key
     */
    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("América - MG", "América")]
    [InlineData("Sport-PE", "Sport")]
    public void State_suffixes_are_ignored(string withSuffix, string without)
    {
        Assert.Equal(
            TeamNameNormalizer.NormalizeKey(without),
            TeamNameNormalizer.NormalizeKey(withSuffix));
    }

    /*
     * Scenario: Accents and case are ignored
     *   Given names with diacritics such as "São Paulo"
     *   When compared against plain spellings
     *   Then they match
     */
    [Theory]
    [InlineData("São Paulo", "sao paulo")]
    [InlineData("Grêmio", "GREMIO")]
    [InlineData("Avaí", "avai")]
    public void Accents_and_case_are_ignored(string a, string b)
    {
        Assert.True(TeamNameNormalizer.IsSameTeam(a, b), $"{a} should match {b}");
    }

    /*
     * Scenario: Full legal names match short names
     *   Given "Sport Club Corinthians Paulista"
     *   When compared with "Corinthians"
     *   Then they refer to the same team
     */
    [Theory]
    [InlineData("Sport Club Corinthians Paulista", "Corinthians")]
    [InlineData("São Paulo FC", "São Paulo")]
    public void Full_legal_names_match_short_names(string full, string shortName)
    {
        Assert.True(TeamNameNormalizer.IsSameTeam(full, shortName),
            $"{full} should match {shortName}");
    }

    /*
     * Scenario: Team queries accept any naming convention
     *   Given the match data is loaded
     *   When I search for Flamengo matches using different spellings
     *   Then all spellings resolve to the same set of dataset keys
     */
    [Fact]
    public void Team_queries_accept_any_naming_convention()
    {
        // Given
        var service = TestData.Service;

        // When
        var canonical = service.ResolveTeamKeys("Flamengo");
        var withState = service.ResolveTeamKeys("Flamengo-RJ");
        var noAccents = service.ResolveTeamKeys("Gremio");
        var withAccents = service.ResolveTeamKeys("Grêmio");

        // Then
        Assert.NotEmpty(canonical);
        Assert.Equal(canonical, withState);
        Assert.NotEmpty(noAccents);
        Assert.Equal(noAccents, withAccents);
    }
}
