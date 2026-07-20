using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

public class TeamNameNormalizerTests
{
    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("Sport-PE", "Sport Recife")]
    [InlineData("Atletico-MG", "Atlético Mineiro")]
    [InlineData("Corinthians-SP", "Corinthians")]
    [InlineData("Santos-SP", "Santos")]
    [InlineData("Sao Paulo-SP", "São Paulo")]
    [InlineData("Vasco-RJ", "Vasco da Gama")]
    public void Normalize_StripsStateSuffix_AndMapsToCanonical(string input, string expected)
    {
        var result = TeamNameNormalizer.Normalize(input);
        Assert.Equal(expected, result);
    }

    [Theory]
    [InlineData("América - MG", "América Mineiro")]
    [InlineData("America - MG", "América Mineiro")]
    public void Normalize_HandlesSpacedStateSuffix(string input, string expected)
    {
        var result = TeamNameNormalizer.Normalize(input);
        Assert.Equal(expected, result);
    }

    [Fact]
    public void Normalize_StripsBracketedContent()
    {
        var input = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ";
        var result = TeamNameNormalizer.Normalize(input);
        Assert.DoesNotContain("antigo", result);
    }

    [Fact]
    public void Normalize_HandlesNull()
    {
        var result = TeamNameNormalizer.Normalize(null);
        Assert.Equal("", result);
    }

    [Fact]
    public void Normalize_HandlesEmpty()
    {
        var result = TeamNameNormalizer.Normalize("");
        Assert.Equal("", result);
    }

    [Theory]
    [InlineData("Flamengo", "Flamengo-RJ", true)]
    [InlineData("Palmeiras", "Palmeiras-SP", true)]
    [InlineData("Flamengo", "Fluminense", false)]
    [InlineData("Corinthians", "Santos", false)]
    public void Matches_TeamNames_ReturnsExpected(string search, string teamInData, bool expected)
    {
        var result = TeamNameNormalizer.Matches(teamInData, search);
        Assert.Equal(expected, result);
    }

    [Fact]
    public void Matches_PartialName_ReturnsTrue()
    {
        var result = TeamNameNormalizer.Matches("Flamengo-RJ", "Flamengo");
        Assert.True(result);
    }

    [Fact]
    public void Matches_CaseInsensitive_ReturnsTrue()
    {
        var result = TeamNameNormalizer.Matches("Flamengo-RJ", "flamengo");
        Assert.True(result);
    }
}
