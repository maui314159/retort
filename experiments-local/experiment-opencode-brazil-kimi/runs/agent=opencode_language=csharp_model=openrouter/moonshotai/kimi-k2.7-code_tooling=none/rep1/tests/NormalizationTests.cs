/*
 * Brazilian Soccer MCP Server - Normalization Tests
 *
 * Verifies team name normalization and date parsing across datasets.
 */
using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

public class NormalizationTests
{
    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("São Paulo", "sao paulo")]
    [InlineData("Nacional (URU)", "nacional")]
    [InlineData("Sport Club Corinthians Paulista", "sport club corinthians paulista")]
    public void GivenTeamNameWithVariations_WhenNormalized_ThenCanonicalFormIsUsed(string input, string expected)
    {
        var normalized = TeamNameNormalizer.Normalize(input);
        Assert.Equal(expected, normalized, StringComparer.OrdinalIgnoreCase);
    }

    [Fact]
    public void GivenDifferentTeamNameFormats_WhenCompared_ThenTheyAreConsideredSameTeam()
    {
        Assert.True(TeamNameNormalizer.AreSame("Palmeiras-SP", "Palmeiras"));
        Assert.True(TeamNameNormalizer.AreSame("Flamengo-RJ", "Flamengo"));
        Assert.False(TeamNameNormalizer.AreSame("Palmeiras", "Flamengo"));
    }
}
