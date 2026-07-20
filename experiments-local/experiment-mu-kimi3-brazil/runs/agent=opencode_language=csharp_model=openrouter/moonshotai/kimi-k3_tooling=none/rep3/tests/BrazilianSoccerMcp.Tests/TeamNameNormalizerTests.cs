using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

/// <summary>Feature: team-name normalization across the different file conventions.</summary>
public class TeamNameNormalizerTests
{
    [Theory]
    [InlineData("Palmeiras-SP", "palmeiras")]
    [InlineData("Flamengo-RJ", "flamengo")]
    [InlineData("São Paulo", "sao paulo")]
    [InlineData("Sao Paulo", "sao paulo")]
    [InlineData("Grêmio", "gremio")]
    [InlineData("Avaí-SC", "avai")]
    [InlineData("Vasco da Gama-RJ", "vasco da gama")]
    [InlineData("Sport Club Corinthians Paulista", "corinthians")]
    [InlineData("Atlético Mineiro", "atletico mg")]
    [InlineData("Atletico-MG", "atletico mg")]
    [InlineData("Athletico-PR", "athletico pr")]
    [InlineData("Athletico Paranaense", "athletico pr")]
    [InlineData("América - MG", "america mg")]
    [InlineData("América FC (Minas Gerais)", "america mg")]
    [InlineData("Sport-PE", "sport recife")]
    [InlineData("Sport Club do Recife", "sport recife")]
    [InlineData("Botafogo-RJ", "botafogo")]
    [InlineData("Ceará Sporting Club", "ceara")]
    [InlineData("Red Bull Bragantino-SP", "red bull bragantino")]
    public void Given_TeamNameVariant_When_Canonized_Then_MatchesExpectedKey(string raw, string expected)
    {
        // Given / When / Then
        Assert.Equal(expected, TeamNameNormalizer.CanonKey(raw));
    }

    [Theory]
    [InlineData("Atletico-GO", "atletico go")]   // state kept: ambiguous base
    [InlineData("Botafogo PB", "botafogo pb")]   // distinct club from Botafogo-RJ
    [InlineData("América-RN", "america rn")]
    public void Given_AmbiguousBaseName_When_Canonized_Then_StateSuffixIsKept(string raw, string expected)
    {
        // Given / When / Then
        Assert.Equal(expected, TeamNameNormalizer.CanonKey(raw));
    }

    [Fact]
    public void Given_AccentedAndUnaccentedSpellings_When_Canonized_Then_TheyUnify()
    {
        // Given
        var accented = TeamNameNormalizer.CanonKey("Grêmio-RS");
        var plain = TeamNameNormalizer.CanonKey("Gremio");

        // When / Then
        Assert.Equal(plain, accented);
    }

    [Fact]
    public void Given_NullOrEmpty_When_Canonized_Then_EmptyKey()
    {
        // Given / When / Then
        Assert.Equal(string.Empty, TeamNameNormalizer.CanonKey(null));
        Assert.Equal(string.Empty, TeamNameNormalizer.CanonKey("   "));
    }
}
