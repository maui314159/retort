using BrazilianSoccerMcpServer.Services;
using FluentAssertions;
using Xunit;

namespace BrazilianSoccerMcpServer.Tests;

public class TeamNameMatcherTests
{
    [Fact]
    public void GivenTeamNameWithStateSuffix_WhenBaseNameIsComputed_ThenSuffixIsRemoved()
    {
        TeamNameMatcher.BaseName("Palmeiras-SP").Should().Be("palmeiras");
        TeamNameMatcher.BaseName("Flamengo-RJ").Should().Be("flamengo");
    }

    [Fact]
    public void GivenTeamNameWithDiacritics_WhenNormalized_ThenAccentsAreRemoved()
    {
        TeamNameMatcher.Normalize("São Paulo").Should().Be("sao paulo");
        TeamNameMatcher.Normalize("Grêmio").Should().Be("gremio");
    }

    [Fact]
    public void GivenSimilarTeamNames_WhenIsMatchIsChecked_ThenTheyMatch()
    {
        TeamNameMatcher.IsMatch("Palmeiras", "Palmeiras-SP").Should().BeTrue();
        TeamNameMatcher.IsMatch("Flamengo-RJ", "Flamengo").Should().BeTrue();
        TeamNameMatcher.IsMatch("Athletico Paranaense", "Athletico-PR").Should().BeTrue();
    }
}
