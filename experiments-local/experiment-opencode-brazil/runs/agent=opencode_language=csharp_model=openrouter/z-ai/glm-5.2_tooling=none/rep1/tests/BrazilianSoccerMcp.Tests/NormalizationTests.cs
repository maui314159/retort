// Context block
// File: NormalizationTests.cs
// Purpose: BDD/GWT tests for the TeamNameNormalizer and DateParser used across the
// Brazilian Soccer MCP server. These cover the data-quality requirements in TASK.md:
// team-name variations (state suffix, full official name, parenthetical notes) must all
// resolve to one canonical form, and the three CSV date formats must parse correctly.
// Tests are grouped by Feature with Given/When/Then comments matching the spec style.
// Language: C# (.NET 10) + xUnit. Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

public class NormalizationTests
{
    private readonly TeamNameNormalizer _n = new();

    // Feature: Team Name Normalization

    // Scenario: Strip trailing state suffix
    //   Given a team name with a "-SP" suffix
    //   When I normalize "Palmeiras-SP"
    //   Then the result should be "Palmeiras"
    [Fact]
    public void Normalize_strips_state_suffix()
    {
        Assert.Equal("Palmeiras", _n.Normalize("Palmeiras-SP"));
        Assert.Equal("Sport", _n.Normalize("Sport-PE"));
        Assert.Equal("Flamengo", _n.Normalize("Flamengo-RJ"));
    }

    // Scenario: Resolve full official names
    //   Given an official club name
    //   When I normalize the long form
    //   Then the short canonical name is returned
    [Fact]
    public void Normalize_resolves_official_names()
    {
        Assert.Equal("Corinthians", _n.Normalize("Sport Club Corinthians Paulista"));
        Assert.Equal("Sao Paulo", _n.Normalize("São Paulo Futebol Clube"));
        Assert.Equal("Vasco", _n.Normalize("Club de Regatas Vasco da Gama"));
    }

    // Scenario: Strip parenthetical notes
    //   Given a team with a "(antigo ...)" note and a state suffix
    //   When I normalize it
    //   Then the canonical short name is returned
    [Fact]
    public void Normalize_strips_parenthetical_notes()
    {
        Assert.Equal("Boavista", _n.Normalize("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"));
    }

    // Scenario: Ambiguous Atletico teams stay distinct
    //   Given "Atletico-MG" and "Athletico-PR"
    //   When I normalize both
    //   Then they remain distinct canonical names
    [Fact]
    public void Normalize_keeps_atletico_variants_distinct()
    {
        Assert.Equal("Atletico-MG", _n.Normalize("Atletico-MG"));
        Assert.Equal("Athletico-PR", _n.Normalize("Athletico-PR"));
        Assert.NotEqual(_n.Normalize("Atletico-MG"), _n.Normalize("Athletico-PR"));
    }

    // Scenario: Matches collapses spelling variants
    //   Given a raw "Palmeiras-SP" and a query "Palmeiras"
    //   When I ask if they match
    //   Then it returns true
    [Fact]
    public void Matches_treats_suffixed_and_bare_as_same()
    {
        Assert.True(_n.Matches("Palmeiras-SP", "Palmeiras"));
        Assert.True(_n.Matches("Sociedade Esportiva Palmeiras", "Palmeiras"));
        Assert.False(_n.Matches("Flamengo", "Fluminense"));
    }

    // Feature: Date Parsing

    // Scenario: Parse ISO with time
    //   Given "2012-05-19 18:30:00"
    //   When I parse it
    //   Then the date is 2012-05-19 18:30
    [Fact]
    public void Parse_handles_iso_with_time()
    {
        var d = new DateParser().Parse("2012-05-19 18:30:00");
        Assert.Equal(2012, d.Year);
        Assert.Equal(5, d.Month);
        Assert.Equal(19, d.Day);
        Assert.Equal(18, d.Hour);
        Assert.Equal(30, d.Minute);
    }

    // Scenario: Parse Brazilian day-first format
    //   Given "29/03/2003"
    //   When I parse it
    //   Then the date is 2003-03-29
    [Fact]
    public void Parse_handles_brazilian_format()
    {
        var d = new DateParser().Parse("29/03/2003");
        Assert.Equal(2003, d.Year);
        Assert.Equal(3, d.Month);
        Assert.Equal(29, d.Day);
    }

    // Scenario: Parse ISO date only
    //   Given "2023-09-24"
    //   When I parse it
    //   Then the date is 2023-09-24
    [Fact]
    public void Parse_handles_iso_date_only()
    {
        var d = new DateParser().Parse("2023-09-24");
        Assert.Equal(2023, d.Year);
        Assert.Equal(9, d.Month);
        Assert.Equal(24, d.Day);
    }
}
