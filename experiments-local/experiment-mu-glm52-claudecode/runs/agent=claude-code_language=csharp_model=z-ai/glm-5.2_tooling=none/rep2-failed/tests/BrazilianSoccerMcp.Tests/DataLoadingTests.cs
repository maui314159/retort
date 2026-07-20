// BrazilianSoccerMcp.Tests / DataLoadingTests.cs
// -----------------------------------------------------------------------------
// Context: BDD scenarios for TASK.md "Success Criteria -> Data Coverage" — all six
// CSV files loadable and queryable, with row counts near the documented totals.
// Feature: Data Loading Coverage
// The documented row counts (TASK.md): 4,180 / 1,337 / 1,255 / 10,296 / 6,886 /
// 18,207. Rows with empty essential cells are skipped, so loaded counts are the
// lower bound on documented totals (Libertadores blanks reduce slightly).
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Data;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

[Collection("SoccerData")]
public class DataLoadingTests
{
    private readonly SoccerDataService _data;
    public DataLoadingTests(SoccerDataFixture fixture) => _data = fixture.Data;

    // Scenario: all six CSV files load with rows at or near the documented totals
    [Fact]
    public void GivenAllSixCsvFilesExist_WhenLoaded_ThenEveryFileHasRowsAtOrNearDocumentedTotals()
    {
        var counts = _data.LoadCounts;
        // Then Brasileirão ~4,180
        Assert.InRange(counts[DataLocator.Files.Brasileirao], 4100, 4200);
        // And Copa do Brasil ~1,337
        Assert.InRange(counts[DataLocator.Files.CopaDoBrasil], 1300, 1400);
        // And Libertadores ~1,255
        Assert.InRange(counts[DataLocator.Files.Libertadores], 1200, 1300);
        // And historical Brasileirão ~6,886
        Assert.InRange(counts[DataLocator.Files.HistoricalBrasileirao], 6800, 6900);
        // And extended BR-Football ~10,296
        Assert.InRange(counts[DataLocator.Files.Extended], 10000, 10400);
        // And FIFA players ~18,207
        Assert.InRange(counts[DataLocator.Files.FifaPlayers], 18000, 18300);
    }

    // Scenario: the flat Matches list spans every competition
    [Fact]
    public void GivenAllMatchFilesLoaded_WhenMatchesAreEnumerated_ThenEveryCompetitionIsRepresented()
    {
        var comps = _data.Matches.Select(m => m.Competition).Distinct().ToHashSet();
        Assert.Contains(BrazilianSoccerMcp.Core.Models.CompetitionKind.BrasileiraoSerieA, comps);
        Assert.Contains(BrazilianSoccerMcp.Core.Models.CompetitionKind.CopaDoBrasil, comps);
        Assert.Contains(BrazilianSoccerMcp.Core.Models.CompetitionKind.CopaLibertadores, comps);
        Assert.Contains(BrazilianSoccerMcp.Core.Models.CompetitionKind.HistoricoBrasileirao, comps);
        Assert.Contains(BrazilianSoccerMcp.Core.Models.CompetitionKind.Extended, comps);
    }

    // Scenario: matches carry normalized team keys + original display names
    [Fact]
    public void GivenAnyMatchRow_WhenLoaded_ThenItCarriesBothOriginalAndCanonicalTeamNames()
    {
        var sample = _data.Matches.First(m => !string.IsNullOrEmpty(m.HomeTeamOriginal));
        Assert.False(string.IsNullOrEmpty(sample.HomeTeam));
        Assert.False(string.IsNullOrEmpty(sample.AwayTeam));
    }

    // Scenario: the loaded data is large enough to answer at least 20 sample questions
    [Fact]
    public void GivenLoadedData_WhenCheckingCoverage_ThenTotalMatchesAndPlayersSupportTwentyPlusQueries()
    {
        Assert.True(_data.Matches.Count > 20000, "matches should exceed 20k across files");
        Assert.True(_data.Players.Count > 18000, "players should exceed 18k");
    }
}
