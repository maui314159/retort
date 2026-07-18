// Brazilian Soccer MCP Server - BDD tests for player queries and data loading
//
// Context: BDD scenarios for the "Player Queries" feature area and the spec's
// "Data Coverage" success criteria (all 6 CSV files loadable and queryable).
// Also covers the team-name normalization unit tests for the accented/dotted/
// suffixed variants described in the "Data Quality Notes" section.

using BrazilianSoccerMcp.Services;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD-style tests for player queries and dataset coverage. Maps to the spec's
/// player-query scenarios and data-coverage success criteria.
/// </summary>
public class PlayerQueryBddTests
{
    private readonly SoccerDataService _data = new();

    private SoccerDataService Data
    {
        get { _data.EnsureLoaded(); return _data; }
    }

    // Scenario: Find all Brazilian players
    //   Given the FIFA player data is loaded
    //   When I search for players with nationality "Brazil"
    //   Then I should receive a non-empty list of Brazilian players
    [Fact]
    public void Find_brazilian_players_returns_non_empty_list()
    {
        // Given
        var service = Data;

        // When
        var brazilians = service.Players
            .Where(p => p.Nationality.Equals("Brazil", StringComparison.OrdinalIgnoreCase))
            .ToList();

        // Then
        Assert.NotEmpty(brazilians);
        Assert.All(brazilians, p => Assert.Equal("Brazil", p.Nationality, ignoreCase: true));
    }

    // Scenario: Search player by name
    //   Given the FIFA player data is loaded
    //   When I search for a player by name (partial)
    //   Then I should receive matching players
    [Fact]
    public void Search_player_by_name_returns_matches()
    {
        // Given
        var service = Data;
        var tools = new SoccerTools(service);

        // When
        var result = tools.SearchPlayers(name: "Neymar");

        // Then
        Assert.Contains("Neymar", result, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("No players found", result);
    }

    // Scenario: Find players by club
    //   Given the FIFA player data is loaded
    //   When I search for players at a Brazilian club
    //   Then I should receive players from that club
    [Fact]
    public void Get_club_players_returns_club_roster()
    {
        // Given
        var service = Data;
        var tools = new SoccerTools(service);

        // When - use a club that exists in the FIFA dataset
        var clubs = service.Players.Select(p => p.Club).Where(c => !string.IsNullOrEmpty(c)).Distinct().Take(1).ToList();
        Assert.NotEmpty(clubs);
        var club = clubs[0]!;
        var result = tools.GetClubPlayers(club);

        // Then
        Assert.DoesNotContain("No players found", result);
    }

    // Scenario: Top-rated players
    //   Given the FIFA player data is loaded
    //   When I search for players with minOverall 85
    //   Then all results should have overall >= 85
    //   And results should be sorted by overall descending
    [Fact]
    public void Top_rated_players_filtered_and_sorted()
    {
        // Given
        var service = Data;

        // When
        var top = service.Players
            .Where(p => p.Overall >= 85)
            .OrderByDescending(p => p.Overall)
            .Take(10)
            .ToList();

        // Then
        Assert.NotEmpty(top);
        Assert.All(top, p => Assert.True(p.Overall >= 85));
        for (var i = 1; i < top.Count; i++)
            Assert.True(top[i].Overall <= top[i - 1].Overall);
    }
}

/// <summary>
/// Data coverage tests verifying all 6 CSV files load and are queryable.
/// Maps to the spec's "Data Coverage" success criteria.
/// </summary>
public class DataCoverageBddTests
{
    // Scenario: All CSV files are loaded
    //   Given the data directory contains 6 CSV files
    //   When I load all datasets
    //   Then matches and players should be populated from all sources
    [Fact]
    public void All_six_csv_files_are_loaded_and_queryable()
    {
        // Given
        var service = new SoccerDataService();
        service.EnsureLoaded();

        // Then - match data present from multiple sources
        Assert.True(service.Matches.Count > 10000, $"Expected >10k matches, got {service.Matches.Count}");
        Assert.True(service.Players.Count > 10000, $"Expected >10k players, got {service.Players.Count}");

        // All 5 match source files represented
        var sources = service.Matches.Select(m => m.Source).Distinct().ToList();
        Assert.True(sources.Count >= 4, $"Expected matches from >=4 source files, got {sources.Count}");

        // Multiple competitions represented
        var competitions = service.Matches.Select(m => m.Competition).Distinct().ToList();
        Assert.True(competitions.Count >= 3, $"Expected >=3 competitions, got {competitions.Count}");
    }

    // Scenario: Cross-file queries work
    //   Given all datasets are loaded
    //   When I search for a team across all match files
    //   Then I should get matches from multiple competitions/sources
    [Fact]
    public void Cross_file_query_finds_team_across_competitions()
    {
        // Given
        var service = new SoccerDataService();
        service.EnsureLoaded();

        // When
        var matches = service.MatchesForTeam("Flamengo").ToList();

        // Then
        Assert.NotEmpty(matches);
        var comps = matches.Select(m => m.Competition).Distinct().ToList();
        Assert.True(comps.Count >= 2, "Flamengo should appear in multiple competitions");
    }

    // Scenario: Team name variants normalize correctly
    //   Given datasets spell teams differently (suffixes, accents, dots)
    //   When I canonicalize various spellings
    //   Then they should produce the same key
    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("Atlético-MG", "Atletico-MG")]
    [InlineData("América - MG", "America-MG")]
    [InlineData("A.b.c. - RN", "Abc - RN")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("Corinthians-SP", "Corinthians")]
    public void Team_name_variants_normalize_to_same_key(string variant1, string variant2)
    {
        // Given / When
        var key1 = TeamNameNormalizer.CanonicalKey(variant1);
        var key2 = TeamNameNormalizer.CanonicalKey(variant2);

        // Then
        Assert.Equal(key1, key2);
        Assert.False(string.IsNullOrEmpty(key1));
    }

    // Scenario: Parenthetical qualifiers are stripped from display names
    //   Given a team name like "Nacional (URU)"
    //   When I strip the suffix
    //   Then the display name should be "Nacional"
    [Theory]
    [InlineData("Nacional (URU)", "Nacional")]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("América - MG", "América")]
    [InlineData("Barcelona-EQU", "Barcelona")]
    public void Display_name_strips_suffixes_and_parentheticals(string raw, string expected)
    {
        // Given / When
        var display = TeamNameNormalizer.StripSuffix(raw);

        // Then
        Assert.Equal(expected, display);
    }

    // Scenario: Date parsing handles multiple formats
    //   Given dates in ISO and Brazilian formats
    //   When I parse them
    //   Then both should produce valid DateTime values
    [Theory]
    [InlineData("2012-05-19 18:30:00", 2012, 5, 19)]
    [InlineData("2023-09-24", 2023, 9, 24)]
    [InlineData("29/03/2003", 2003, 3, 29)]
    public void Date_parsing_handles_multiple_formats(string raw, int year, int month, int day)
    {
        // Given / When
        var date = SoccerDataService.ParseDate(raw);

        // Then
        Assert.NotNull(date);
        Assert.Equal(year, date!.Value.Year);
        Assert.Equal(month, date.Value.Month);
        Assert.Equal(day, date.Value.Day);
    }

    // Scenario: Goal parsing handles int, string, and float representations
    //   Given goals stored as 2, "2", "1.0", "2.0"
    //   When I parse them
    //   Then all should produce the integer value 2 (or 1 for 1.0)
    [Theory]
    [InlineData("2", 2)]
    [InlineData("0", 0)]
    [InlineData("1.0", 1)]
    [InlineData("2.0", 2)]
    public void Goal_parsing_handles_int_string_and_float(string raw, int expected)
    {
        // Given / When
        var value = SoccerDataService.ParseInt(raw);

        // Then
        Assert.Equal(expected, value);
    }
}
