// =============================================================================
// Brazilian Soccer MCP Server
// File: TeamNameNormalizerTests.cs
// Purpose: Unit tests for TeamNameNormalizer, the cross-dataset glue.
// Context: Cross-file matches only work if the normalizer resolves
//          "Flamengo", "Flamengo-RJ", and "Flamengo - RJ" to the same key.
// =============================================================================

using BrazilianSoccerMcp.Core;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests;

public class TeamNameNormalizerTests
{
    [Theory]
    [InlineData("Flamengo", "Flamengo-RJ")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("Flamengo - RJ", "Flamengo")]
    [InlineData("Flamengo (RJ)", "Flamengo")]
    public void Given_team_name_variations_When_normalizing_Then_keys_match(string a, string b)
    {
        TeamNameNormalizer.AreSame(a, b).Should().BeTrue();
    }

    [Theory]
    [InlineData("Sao Paulo", "São Paulo")]
    [InlineData("Sao Paulo-SP", "São Paulo - SP")]
    public void Given_accent_variations_When_normalizing_Then_keys_match(string a, string b)
    {
        TeamNameNormalizer.AreSame(a, b).Should().BeTrue();
    }

    [Theory]
    [InlineData("Flamengo", "Corinthians")]
    public void Given_different_teams_When_normalizing_Then_keys_differ(string a, string b)
    {
        TeamNameNormalizer.AreSame(a, b).Should().BeFalse();
    }

    [Theory]
    [InlineData("  ", "")]
    [InlineData("", "Flamengo")]
    public void Given_blank_or_empty_input_When_normalizing_Then_key_is_empty(string a, string b)
    {
        TeamNameNormalizer.Key(a).Should().BeEmpty();
        TeamNameNormalizer.AreSame(a, b).Should().BeFalse();
    }

    [Fact]
    public void Given_known_team_When_getting_display_name_Then_returns_canonical_form()
    {
        TeamNameNormalizer.DisplayName("flamengo").Should().Be("Flamengo - RJ");
        TeamNameNormalizer.DisplayName("Flamengo").Should().Be("Flamengo - RJ");
    }

    [Fact]
    public void Given_unknown_team_with_garbage_suffix_When_getting_display_name_Then_returns_original_trimmed()
    {
        // "Flamengo-XX" -- "XX" is not a valid state code, so the suffix
        // is NOT stripped. The key resolves to "flamengoxx", which has
        // no alias match, so DisplayName returns the original.
        TeamNameNormalizer.DisplayName("Flamengo-XX").Should().Be("Flamengo-XX");
        // An entirely unknown team returns its stripped original.
        TeamNameNormalizer.DisplayName("My Custom Team").Should().Be("My Custom Team");
    }
}
