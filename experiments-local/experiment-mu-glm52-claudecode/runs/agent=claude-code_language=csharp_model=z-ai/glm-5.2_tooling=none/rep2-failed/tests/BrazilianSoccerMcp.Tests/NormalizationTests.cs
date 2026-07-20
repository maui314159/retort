// BrazilianSoccerMcp.Tests / NormalizationTests.cs
// -----------------------------------------------------------------------------
// Context: BDD scenarios for TASK.md "Data Quality Notes" — team name variations
// and date formats. These are the foundation: if normalization is wrong, every
// cross-file query silently returns wrong counts.
// Feature: Team Name Normalization & Date Parsing
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Normalization;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

public class NormalizationTests
{
    // Scenario: strip a trailing state suffix while KEEPING it for disambiguation
    [Theory]
    [InlineData("Palmeiras-SP", "palmeiras-sp")]
    [InlineData("Flamengo-RJ", "flamengo-rj")]
    [InlineData("América - MG", "america-mg")]       // spaced dash collapses
    [InlineData("PALMEIRAS", "palmeiras")]
    [InlineData("São Paulo-SP", "sao paulo-sp")]     // accent folded, suffix kept
    [InlineData("Avaí-SC", "avai-sc")]
    [InlineData("Grêmio-RS", "gremio-rs")]
    public void Normalize_ProducesCanonicalKey(string raw, string expected)
    {
        // Given a raw team name from any of the CSVs
        // When normalized
        var actual = TeamNormalizer.Normalize(raw);
        // Then the canonical key is stable and lowercase
        Assert.Equal(expected, actual);
    }

    // Scenario: parenthesized former-name fragments are stripped
    [Fact]
    public void Normalize_StripsParenthesizedFragments()
    {
        // Given a club name with a parenthetical former name
        var raw = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ";
        // When normalized
        var key = TeamNormalizer.Normalize(raw);
        // Then the canonical key has no parentheses and the suffix survives
        Assert.Contains("boavista", key);
        Assert.DoesNotContain("(", key);
        Assert.EndsWith("-rj", key);
    }

    // Scenario: distinct same-base clubs do NOT collide (the Atlético bug)
    [Theory]
    [InlineData("Atlético-MG", "atletico-mg")]
    [InlineData("Atletico-GO", "atletico-go")]
    [InlineData("Atletico-PR", "atletico-pr")]
    public void Normalize_KeepsSuffixesThatDisambiguateSameBaseClubs(string raw, string expected)
    {
        // Given three distinct clubs sharing the "Atlético" base name
        var mg = TeamNormalizer.Normalize("Atlético-MG");
        var go = TeamNormalizer.Normalize("Atletico-GO");
        var pr = TeamNormalizer.Normalize("Atletico-PR");
        // When normalized, each keeps its disambiguating suffix
        Assert.Equal(expected, TeamNormalizer.Normalize(raw));
        // Then they remain distinct keys (no collision to "atletico")
        Assert.NotEqual(mg, go);
        Assert.NotEqual(mg, pr);
        Assert.NotEqual(go, pr);
    }

    // Scenario: a suffix-less query matches a suffixed stored key
    [Theory]
    [InlineData("palmeiras-sp", "palmeiras", true)]
    [InlineData("flamengo-rj", "flamengo", true)]
    [InlineData("atletico-mg", "atletico", true)]   // suffix-less query matches suffixed key
    [InlineData("atletico-mg", "atletico-go", false)] // distinct suffixes never match
    [InlineData("palmeiras-sp", "corinthians-sp", false)]
    [InlineData("palmeiras-sp", "palmeiras-sp", true)] // exact match
    public void SameTeam_IsSuffixTolerantButNeverMergesDistinctClubs(string stored, string query, bool expected)
    {
        // Given a stored canonical key and a query key
        // When compared
        var same = TeamNormalizer.SameTeam(stored, query);
        // Then suffix-tolerant matching holds without merging distinct clubs
        Assert.Equal(expected, same);
    }

    // Scenario: a suffix-less "atletico" query is correctly ambiguous
    [Fact]
    public void SameTeam_AmbiguousBaseMatchesAllSuffixedVariants()
    {
        // Given an ambiguous suffix-less query "atletico"
        // When compared against each suffixed Atlético
        // Then it matches all of them (the caller asked ambiguously)
        Assert.True(TeamNormalizer.SameTeam("atletico-mg", "atletico"));
        Assert.True(TeamNormalizer.SameTeam("atletico-go", "atletico"));
        Assert.True(TeamNormalizer.SameTeam("atletico-pr", "atletico"));
    }

    // Scenario: date parsing handles every format found in the CSVs
    [Theory]
    [InlineData("2012-05-19 18:30:00", 2012, 5, 19)]   // ISO with time
    [InlineData("2023-09-24", 2023, 9, 24)]             // ISO date
    [InlineData("29/03/2003", 2003, 3, 29)]              // Brazilian DD/MM/YYYY
    [InlineData("2023-09-24", 2023, 9, 24)]
    public void DateParser_HandlesEveryCsvFormat(string raw, int y, int m, int d)
    {
        // Given a date string in any of the documented formats
        // When parsed
        var dt = DateParser.Parse(raw);
        // Then the correct calendar date is recovered
        Assert.NotNull(dt);
        Assert.Equal(y, dt!.Value.Year);
        Assert.Equal(m, dt.Value.Month);
        Assert.Equal(d, dt.Value.Day);
    }

    [Fact]
    public void DateParser_ReturnsNullForBlankOrGarbage()
    {
        // Given a blank or unparseable date cell
        // When parsed
        // Then null is returned (never throws)
        Assert.Null(DateParser.Parse(""));
        Assert.Null(DateParser.Parse("   "));
        Assert.Null(DateParser.Parse("not-a-date"));
    }
}
