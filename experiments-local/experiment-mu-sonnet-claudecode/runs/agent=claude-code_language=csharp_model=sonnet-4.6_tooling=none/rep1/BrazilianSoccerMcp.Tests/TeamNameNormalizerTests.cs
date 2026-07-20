using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

public class TeamNameNormalizerTests
{
    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("São Paulo-SP", "São Paulo")]
    [InlineData("Sport-PE", "Sport")]
    [InlineData("Portuguesa-SP", "Portuguesa")]
    [InlineData("América - MG", "América")]
    [InlineData("Ceará - CE", "Ceará")]
    [InlineData("Flamengo", "Flamengo")]
    [InlineData("Palmeiras", "Palmeiras")]
    public void Normalize_StripsStateSuffix(string input, string expected)
    {
        Assert.Equal(expected, TeamNameNormalizer.Normalize(input));
    }

    [Fact]
    public void Normalize_StripsParentheticalAndStateSuffix()
    {
        var input = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ";
        var result = TeamNameNormalizer.Normalize(input);
        Assert.Contains("Boavista", result);
        Assert.DoesNotContain("-RJ", result);
        Assert.DoesNotContain("antigo", result);
    }

    [Theory]
    [InlineData("Flamengo-RJ", "Flamengo", true)]
    [InlineData("Palmeiras-SP", "Palmeiras", true)]
    [InlineData("Flamengo", "Flamengo", true)]
    [InlineData("FLAMENGO", "flamengo", true)]
    [InlineData("Corinthians-SP", "Palmeiras", false)]
    public void Matches_ReturnsCorrectResult(string stored, string query, bool expected)
    {
        Assert.Equal(expected, TeamNameNormalizer.Matches(stored, query));
    }
}
