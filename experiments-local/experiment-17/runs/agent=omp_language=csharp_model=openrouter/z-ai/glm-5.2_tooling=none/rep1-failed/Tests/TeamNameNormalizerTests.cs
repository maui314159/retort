// ============================================================================
// File: Tests/TeamNameNormalizerTests.cs
// ----------------------------------------------------------------------------
// Context: Pure unit tests for the team-name normalization that makes
// cross-dataset matching work. These are the data-quality guarantees called out
// in the spec (Team Name Variations, Date Formats, Character Encoding).
//
// BDD Feature: Team Name Normalization
// ============================================================================

using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

public class TeamNameNormalizerTests
{
    // Scenario: state suffix with hyphen is stripped
    //   Given a team name "Palmeiras-SP"
    //   When normalized
    //   Then the bare key is "palmeiras" and the suffix is "SP"
    [Fact]
    public void Parse_strips_hyphen_state_suffix()
    {
        var key = TeamNameNormalizer.Parse("Palmeiras-SP");
        Assert.Equal("palmeiras", key.Bare);
        Assert.Equal("SP", key.Suffix);
    }

    // Scenario: state suffix with " - " separator
    //   Given "América - MG"
    //   When normalized
    //   Then the bare key is "america" and the suffix is null (split kept left half)
    [Fact]
    public void Parse_splits_on_space_dash_space()
    {
        var key = TeamNameNormalizer.Parse("América - MG");
        Assert.Equal("america", key.Bare);
    }

    // Scenario: parenthetical notes are dropped
    //   Given "Nacional (URU)"
    //   When normalized
    //   Then the bare key is "nacional"
    [Fact]
    public void Parse_drops_parenthetical_notes()
    {
        var key = TeamNameNormalizer.Parse("Nacional (URU)");
        Assert.Equal("nacional", key.Bare);
    }

    // Scenario: accents are folded to ASCII so "São Paulo" matches "Sao Paulo"
    [Fact]
    public void Parse_folds_accents()
    {
        Assert.Equal("sao-paulo", TeamNameNormalizer.Parse("São Paulo").Bare);
        Assert.Equal("gremio", TeamNameNormalizer.Parse("Grêmio").Bare);
        Assert.Equal("avai", TeamNameNormalizer.Parse("Avaí").Bare);
    }

    // Scenario: multi-word names use hyphen-joined bare keys
    [Fact]
    public void Parse_hyphen_joins_multi_word_names()
    {
        Assert.Equal("ponte-preta", TeamNameNormalizer.Parse("Ponte Preta-SP").Bare);
    }

    // Scenario: bare query "Flamengo" matches stored "Flamengo-RJ"
    [Fact]
    public void Matches_bare_query_matches_suffixed_stored()
    {
        var query = TeamNameNormalizer.Parse("Flamengo");
        var stored = TeamNameNormalizer.Parse("Flamengo-RJ");
        Assert.True(TeamNameNormalizer.Matches(query, stored));
    }

    // Scenario: same bare name but different suffix does NOT match (disambiguation)
    [Fact]
    public void Matches_different_suffixes_do_not_match()
    {
        var mg = TeamNameNormalizer.Parse("América-MG");
        var rn = TeamNameNormalizer.Parse("América-RN");
        Assert.False(TeamNameNormalizer.Matches(mg, rn));
    }

    // Scenario: same suffix matches
    [Fact]
    public void Matches_same_suffix_matches()
    {
        var a = TeamNameNormalizer.Parse("América-MG");
        var b = TeamNameNormalizer.Parse("América-MG");
        Assert.True(TeamNameNormalizer.Matches(a, b));
    }

    // Scenario: ASCII "Sao Paulo" matches accented "São Paulo-SP" (cross-dataset)
    [Fact]
    public void Matches_ascii_matches_accented_with_suffix()
    {
        var ascii = TeamNameNormalizer.Parse("Sao Paulo");
        var accented = TeamNameNormalizer.Parse("São Paulo-SP");
        Assert.True(TeamNameNormalizer.Matches(ascii, accented));
    }
}
