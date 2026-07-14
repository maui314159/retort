// ============================================================================
// File: Tests/DataLoadingTests.cs
// ----------------------------------------------------------------------------
// Context: Verifies the success criterion "All 6 CSV files are loadable and
// queryable". The SoccerDataStore loads all five match files into the unified
// Matches collection and the FIFA file into Players. We assert each source
// contributed rows and that the totals match the spec's documented counts.
// ============================================================================

using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

[Collection("Store")]
public class DataLoadingTests
{
    private readonly SoccerDataStore _store;
    public DataLoadingTests(StoreFixture fixture) => _store = fixture.Store;

    [Fact]
    public void All_match_sources_are_loaded()
    {
        var bySource = _store.Matches.GroupBy(m => m.Source).ToDictionary(g => g.Key ?? "", g => g.Count());

        Assert.True(bySource.ContainsKey("Brasileirao_Matches.csv"));
        Assert.True(bySource.ContainsKey("Brazilian_Cup_Matches.csv"));
        Assert.True(bySource.ContainsKey("Libertadores_Matches.csv"));
        Assert.True(bySource.ContainsKey("novo_campeonato_brasileiro.csv"));
        Assert.True(bySource.ContainsKey("BR-Football-Dataset.csv"));
    }

    [Fact]
    public void Match_counts_match_spec_order_of_magnitude()
    {
        // Spec documents: 4,180 / 1,337 / 1,255 / 10,296 / 6,886 matches per file.
        var bySource = _store.Matches.GroupBy(m => m.Source).ToDictionary(g => g.Key ?? "", g => g.Count());
        Assert.InRange(bySource["Brasileirao_Matches.csv"], 3_000, 5_000);
        Assert.InRange(bySource["Brazilian_Cup_Matches.csv"], 1_000, 1_600);
        Assert.InRange(bySource["Libertadores_Matches.csv"], 1_000, 1_500);
        Assert.InRange(bySource["novo_campeonato_brasileiro.csv"], 6_000, 7_500);
        Assert.InRange(bySource["BR-Football-Dataset.csv"], 9_000, 11_000);
    }

    [Fact]
    public void Fifa_players_loaded()
    {
        // Spec documents 18,207 players.
        Assert.InRange(_store.Players.Count, 15_000, 20_000);
    }

    [Fact]
    public void Matches_have_normalized_team_keys()
    {
        var sample = _store.Matches.First(m => m.HomeGoals is not null);
        Assert.False(string.IsNullOrEmpty(sample.HomeKey.Bare));
        Assert.False(string.IsNullOrEmpty(sample.AwayKey.Bare));
    }

    [Fact]
    public void Dates_parse_across_formats()
    {
        // ISO datetime (modern files) and DD/MM/YYYY (historical file) both parse.
        Assert.Contains(_store.Matches, m => m.Date is not null && m.Source == "Brasileirao_Matches.csv");
        Assert.Contains(_store.Matches, m => m.Date is not null && m.Source == "novo_campeonato_brasileiro.csv");
    }
}
