// =============================================================================
// File:    NameNormalizerTests.cs
// Project: BrazilianSoccer.Tests
// Purpose: BDD (Given/When/Then) tests for NameNormalizer — the load-bearing
//          component that decides whether two rows refer to the same club.
// Context: These guard the two correctness hazards documented in
//          NameNormalizer: (1) distinct same-named clubs MUST stay separate by
//          state (Atlético-MG vs Athletico-PR vs Atlético-GO, Botafogo-RJ vs
//          Botafogo-SP), and (2) spelling variants of one club MUST merge
//          (Vasco / Vasco da Gama, Athletico Paranaense / Atlético-PR, verbose
//          legal names). Regressions here silently inflate standings.
// =============================================================================

using BrazilianSoccer.Core;

namespace BrazilianSoccer.Tests;

public class NameNormalizerTests
{
    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("Flamengo-RJ", "Clube de Regatas do Flamengo")]
    [InlineData("Vasco", "Vasco da Gama")]
    [InlineData("Vasco da Gama-RJ", "Vasco da Gama")]
    [InlineData("Sport Club Corinthians Paulista", "Corinthians-SP")]
    [InlineData("Athletico Paranaense", "Atletico-PR")]
    [InlineData("Athletico", "Atletico-PR")]
    [InlineData("Sao Paulo FC", "São Paulo-SP")]
    [InlineData("EC Bahia", "Bahia")]
    [InlineData("Red Bull Bragantino", "Bragantino")]
    [InlineData("Sport Recife", "Sport-PE")]
    public void Given_TwoSpellingsOfSameClub_When_Keyed_Then_KeysAreEqual(string a, string b)
    {
        // When
        var keyA = NameNormalizer.Key(a);
        var keyB = NameNormalizer.Key(b);

        // Then
        Assert.Equal(keyA, keyB);
        Assert.NotEqual("", keyA);
    }

    [Theory]
    [InlineData("Atletico-MG", "Atletico-PR")]
    [InlineData("Atletico-MG", "Atletico-GO")]
    [InlineData("Atletico Mineiro", "Athletico Paranaense")]
    [InlineData("Botafogo-RJ", "Botafogo-SP")]
    [InlineData("America-MG", "America-RN")]
    public void Given_DistinctClubsSharingABaseName_When_Keyed_Then_KeysDiffer(string a, string b)
    {
        // When
        var keyA = NameNormalizer.Key(a);
        var keyB = NameNormalizer.Key(b);

        // Then
        Assert.NotEqual(keyA, keyB);
    }

    [Fact]
    public void Given_ForeignClubWithCountryTag_When_Keyed_Then_CountryQualified()
    {
        // Given a Libertadores-style foreign club
        // When
        var key = NameNormalizer.Key("Nacional (URU)");

        // Then it keeps the country so it cannot merge with a Brazilian "Nacional"
        Assert.Contains("uru", key);
        Assert.NotEqual(NameNormalizer.Key("Nacional"), key);
    }

    [Fact]
    public void Given_NameWithStateSuffix_When_Displayed_Then_SuffixRemovedAccentsKept()
    {
        // When
        var display = NameNormalizer.Display("São Paulo-SP");

        // Then
        Assert.Equal("São Paulo", display);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void Given_BlankInput_When_Keyed_Then_Empty(string? input)
    {
        Assert.Equal("", NameNormalizer.Key(input));
    }
}
