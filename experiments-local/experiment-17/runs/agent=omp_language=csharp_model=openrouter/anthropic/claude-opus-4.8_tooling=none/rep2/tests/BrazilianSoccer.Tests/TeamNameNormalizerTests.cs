// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    TeamNameNormalizerTests.cs
// Project: BrazilianSoccer.Tests
// Purpose: BDD (Given/When/Then) unit tests for TeamNameNormalizer, the
//          component that reconciles the many spellings of club names across
//          datasets (state suffixes, country codes, accents, legal names).
// =============================================================================

using BrazilianSoccer.Core.Data;
using Xunit;

namespace BrazilianSoccer.Tests;

public sealed class TeamNameNormalizerTests
{
    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("América - MG", "América")]
    [InlineData("Nacional (URU)", "Nacional")]
    [InlineData("Barcelona-EQU", "Barcelona")]
    public void Given_NameWithLocationSuffix_When_Displayed_Then_SuffixIsStripped(string input, string expected)
    {
        // When
        var display = TeamNameNormalizer.Display(input);
        // Then
        Assert.Equal(expected, display);
    }

    [Theory]
    [InlineData("Flamengo-RJ", "flamengo")]
    [InlineData("FLAMENGO", "flamengo")]
    [InlineData("São Paulo", "sao paulo")]
    [InlineData("Grêmio", "gremio")]
    [InlineData("Sport Club Corinthians Paulista", "corinthians")]
    [InlineData("Atlético-MG", "atletico mineiro")]
    public void Given_VariantSpelling_When_Canonicalised_Then_KeyIsAccentAndSuffixInsensitive(
        string input, string expectedKey)
    {
        // When
        var key = TeamNameNormalizer.Canonical(input);
        // Then
        Assert.Equal(expectedKey, key);
    }

    [Fact]
    public void Given_SameClubDifferentSpellings_When_Matched_Then_TheyAreEqual()
    {
        // Given two spellings of the same club
        var a = "Flamengo-RJ";
        var b = "FLAMENGO";
        // When / Then
        Assert.True(TeamNameNormalizer.Matches(a, b));
    }

    [Fact]
    public void Given_DifferentClubs_When_Matched_Then_TheyAreNotEqual()
    {
        // Given / When / Then
        Assert.False(TeamNameNormalizer.Matches("Flamengo", "Fluminense"));
    }

    [Fact]
    public void Given_EmptyName_When_Matched_Then_NeverEqual()
    {
        Assert.False(TeamNameNormalizer.Matches("", ""));
    }
}
