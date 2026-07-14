using BrazilianSoccerCore.Data;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD tests for team-name normalization — the core of cross-dataset matching.
/// </summary>
public class TeamNormalizerTests
{
    // Scenario: state suffix stripped
    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("América - MG", "América")]
    [InlineData("Athletico-PR", "Athletico")]
    public void Normalize_strips_state_suffix(string raw, string expected)
    {
        Assert.Equal(expected, TeamNormalizer.Normalize(raw));
    }

    // Scenario: parenthetical annotations removed
    [Fact]
    public void Normalize_strips_parenthetical_annotations()
    {
        var raw = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ";
        Assert.Equal("Boavista Sport Club", TeamNormalizer.Normalize(raw));
    }

    // Scenario: accents preserved in display, stripped in key
    [Fact]
    public void Key_is_accent_insensitive()
    {
        Assert.True(TeamNormalizer.SameTeam("São Paulo", "Sao Paulo"));
        Assert.True(TeamNormalizer.SameTeam("Grêmio", "Gremio"));
    }

    // Scenario: same team across naming variations
    [Fact]
    public void SameTeam_matches_across_variations()
    {
        Assert.True(TeamNormalizer.SameTeam("Palmeiras-SP", "Palmeiras"));
        Assert.True(TeamNormalizer.SameTeam("Flamengo-RJ", "Flamengo"));
        Assert.False(TeamNormalizer.SameTeam("Flamengo", "Fluminense"));
    }
}