// <copyright file="TeamNameNormalizerTests.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Tests for team name normalization.
// </copyright>
using BrazilianSoccerMcp.Core.Normalization;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Normalization;

public class TeamNameNormalizerTests
{
    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("São Paulo Futebol Clube", "São Paulo")]
    [InlineData("Sport Club Corinthians Paulista", "Corinthians")]
    [InlineData("Grêmio Foot-Ball Porto Alegrense", "Grêmio")]
    [InlineData("América-MG", "América-MG")]
    [InlineData("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "Boavista-RJ")]
    public void Normalize_ReturnsCanonicalName(string raw, string expected)
    {
        TeamNameNormalizer.Normalize(raw).Should().Be(expected);
    }

    [Theory]
    [InlineData("Palmeiras", "Palmeiras-SP")]
    [InlineData("São Paulo", "Sao Paulo")]
    [InlineData("Flamengo", "Flamengo-RJ")]
    public void Matches_ReturnsTrueForVariations(string a, string b)
    {
        TeamNameNormalizer.Matches(a, b).Should().BeTrue();
    }
}
