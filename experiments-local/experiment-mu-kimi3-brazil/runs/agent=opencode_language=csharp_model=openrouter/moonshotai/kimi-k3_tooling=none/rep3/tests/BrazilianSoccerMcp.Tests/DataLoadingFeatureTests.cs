using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: Dataset loading
/// All six CSV files load, contribute to the unified graph, and cross-source
/// duplication is removed by the per-season source-priority rule.
/// </summary>
public class DataLoadingFeatureTests
{
    [Fact]
    public void Given_TheKaggleDirectory_When_DataIsLoaded_Then_AllSixFilesContributeMatchesOrPlayers()
    {
        // Given / When
        var graph = TestData.Graph;

        // Then: every match file kept at least one season's worth of rows
        Assert.Equal(5, graph.SourceContributions.Count);
        Assert.All(graph.SourceContributions, kv => Assert.True(kv.Value > 0, $"{kv.Key} contributed no matches"));
        // And the player file is loaded
        Assert.Equal(18_207, graph.Players.Count);
    }

    [Fact]
    public void Given_OverlappingSources_When_DataIsLoaded_Then_2019SerieAHasExactlyOneMatchPerFixture()
    {
        // Given (2019 appears in Brasileirao_Matches, novo_campeonato AND BR-Football)
        var graph = TestData.Graph;

        // When
        var season2019 = graph.Matches
            .Where(m => m.Competition == DataLoader.SerieA && m.Season == 2019)
            .ToList();

        // Then: one authoritative source -> 20 teams x 38 rounds / 2 = 380 matches
        Assert.Equal(380, season2019.Count);
        Assert.Equal(20, season2019.Select(m => m.HomeKey).Distinct().Count());
    }

    [Fact]
    public void Given_RawFiles_When_DataIsLoaded_Then_DedupActuallyRemovedRows()
    {
        // Given / When
        var graph = TestData.Graph;

        // Then
        Assert.True(graph.TotalMatchRowsRead > graph.Matches.Count,
            "expected cross-source dedup to drop overlapping seasons");
    }

    [Fact]
    public void Given_MatchesWithNaScores_When_DataIsLoaded_Then_TheyAreKeptButMarkedUnplayed()
    {
        // Given (Brasileirao_Matches.csv has 82 NA rows, e.g. postponed 2022 games)
        var graph = TestData.Graph;

        // When
        var unplayed = graph.Matches.Where(m => !m.Played).ToList();

        // Then
        Assert.NotEmpty(unplayed);
        Assert.All(unplayed, m => Assert.Equal("not played", m.Scoreline()));
    }

    [Fact]
    public void Given_AllMatches_When_Inspecting_Then_EveryMatchHasCanonicalTeamsAndCompetition()
    {
        // Given / When
        var graph = TestData.Graph;

        // Then
        Assert.All(graph.Matches, m =>
        {
            Assert.False(string.IsNullOrWhiteSpace(m.HomeKey));
            Assert.False(string.IsNullOrWhiteSpace(m.AwayKey));
            Assert.False(string.IsNullOrWhiteSpace(m.Competition));
        });
    }

    [Fact]
    public void Given_ThePlayerFile_When_DataIsLoaded_Then_BrazilianPlayersArePresent()
    {
        // Given / When
        var graph = TestData.Graph;

        // Then
        var brazilians = graph.Players.Count(p => p.Nationality == "Brazil");
        Assert.Equal(827, brazilians);
    }
}
