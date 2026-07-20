using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Data Loading
///   All six Kaggle CSV files must be loadable and queryable.
/// </summary>
public class DataLoadingTests
{
    /*
     * Scenario: All six CSV files are loaded
     *   Given the data directory contains the six Kaggle CSVs
     *   When the service loads
     *   Then matches and players are available in expected volumes
     */
    [Fact]
    public void All_six_csv_files_are_loaded()
    {
        // Given / When
        var service = TestData.Service;

        // Then - player data: 18,207 rows in fifa_data.csv
        Assert.True(service.Players.Count > 17_000,
            $"Expected >17k players, got {service.Players.Count}");

        // Then - match data: after cross-file dedupe we must still have well
        // over 20k unique matches from the ~28k raw rows
        Assert.True(service.Matches.Count > 20_000,
            $"Expected >20k deduped matches, got {service.Matches.Count}");
    }

    /*
     * Scenario: Every expected competition is present
     *   Given the match data is loaded
     *   When competitions are listed
     *   Then Brasileirão, Copa do Brasil and Libertadores are all present
     */
    [Fact]
    public void Every_expected_competition_is_present()
    {
        // Given
        var service = TestData.Service;

        // When
        var competitions = service.GetCompetitions();

        // Then
        Assert.Contains(competitions, c => c.Contains("Brasileirão"));
        Assert.Contains(competitions, c => c.Contains("Copa do Brasil"));
        Assert.Contains(competitions, c => c.Contains("Libertadores"));
    }

    /*
     * Scenario: Cross-file duplicates are removed
     *   Given several source files contain the same real-world match
     *   When the data is loaded
     *   Then the same (date, home, away) match is stored only once
     */
    [Fact]
    public void Cross_file_duplicates_are_removed()
    {
        // Given
        var service = TestData.Service;

        // When
        var duplicates = service.Matches
            .Where(m => m.Date is not null)
            .GroupBy(m => (m.Date!.Value.Date, m.HomeTeamKey, m.AwayTeamKey))
            .Where(g => g.Count() > 1)
            .ToList();

        // Then
        Assert.Empty(duplicates);
    }

    /*
     * Scenario: Multiple date formats are parsed
     *   Given the datasets use ISO, ISO+time and Brazilian date formats
     *   When dates are parsed
     *   Then all formats yield correct DateTime values
     */
    [Theory]
    [InlineData("2023-09-24", 2023, 9, 24)]
    [InlineData("2012-05-19 18:30:00", 2012, 5, 19)]
    [InlineData("29/03/2003", 2003, 3, 29)]
    public void Multiple_date_formats_are_parsed(string raw, int y, int m, int d)
    {
        // When
        var parsed = DataLoader.ParseDate(raw);

        // Then
        Assert.NotNull(parsed);
        Assert.Equal(new DateTime(y, m, d), parsed!.Value.Date);
    }

    /*
     * Scenario: UTF-8 team names survive loading
     *   Given Brazilian Portuguese names contain accents and cedilla
     *   When the team list is read
     *   Then names such as "São Paulo" and "Grêmio" appear intact
     */
    [Fact]
    public void Utf8_team_names_survive_loading()
    {
        // Given
        var service = TestData.Service;

        // When
        var teams = service.GetTeams();

        // Then
        Assert.Contains(teams, t => t.Contains("São Paulo"));
        Assert.Contains(teams, t => t.Contains("Grêmio"));
    }
}
