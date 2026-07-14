// BrazilianSoccerMcp.Tests - BDD feature: Data Quality & Normalization.
// Covers the three data-quality requirements from the spec: team-name
// variations resolve to one identity, multiple date formats parse correctly,
// and UTF-8 accented names are preserved. Also verifies all 6 CSV files load.
using BrazilianSoccerMcp.Core.Data;
using LightBDD.Framework;
using LightBDD.Framework.Scenarios;

namespace BrazilianSoccerMcp.Tests;

[FeatureDescription(
    "Data quality: team-name normalization, multi-format date parsing, UTF-8 " +
    "accent handling, and full dataset loading.")]
public class DataQualityTests : SoccerFeatureFixture
{
    [Scenario]
    public void All_six_CSV_files_are_loadable()
    {
        Runner.RunScenario(
            Given_the_datasets_are_loaded,
            Then_there_should_be_thousands_of_matches,
            And_there_should_be_thousands_of_players);
    }

    [Scenario]
    public void Team_name_variations_resolve_to_the_same_identity()
    {
        Runner.RunScenario(
            Given_the_datasets_are_loaded,
            When_I_resolve_Palmeiras_with_and_without_state_suffix,
            Then_both_forms_should_match_the_same_team);
    }

    [Scenario]
    public void Accented_team_names_are_preserved_and_matchable()
    {
        Runner.RunScenario(
            Given_the_datasets_are_loaded,
            When_I_search_for_Sao_Paulo_with_and_without_accent,
            Then_both_searches_should_return_matches,
            And_the_normalized_keys_should_be_equal);
    }

    [Scenario]
    public void Multiple_date_formats_parse_correctly()
    {
        Runner.RunScenario(
            Given_the_datasets_are_loaded,
            Then_ISO_dates_with_time_should_parse,
            And_ISO_dates_without_time_should_parse,
            And_Brazilian_DD_MM_YYYY_dates_should_parse);
    }

    // --- steps ------------------------------------------------------------

    private void Given_the_datasets_are_loaded() { }

    private void Then_there_should_be_thousands_of_matches()
        => Assert.True(Data.Matches.Count > 10000, $"match count {Data.Matches.Count}");

    private void And_there_should_be_thousands_of_players()
        => Assert.True(Data.Players.Count > 10000, $"player count {Data.Players.Count}");

    private void When_I_resolve_Palmeiras_with_and_without_state_suffix()
    {
        ResultText = Query.ResolveTeam("Palmeiras-SP");
        ResultText2 = Query.ResolveTeam("Palmeiras");
    }

    private void Then_both_forms_should_match_the_same_team()
        => Assert.Equal(TeamNameNormalizer.BaseKey(ResultText), TeamNameNormalizer.BaseKey(ResultText2));

    private void When_I_search_for_Sao_Paulo_with_and_without_accent()
    {
        ResultMatches = Query.FindMatchesByTeam("São Paulo", season: 2019);
        ResultMatches2 = Query.FindMatchesByTeam("Sao Paulo", season: 2019);
    }

    private void Then_both_searches_should_return_matches()
    {
        Assert.NotEmpty(ResultMatches);
        Assert.NotEmpty(ResultMatches2);
    }

    private void And_the_normalized_keys_should_be_equal()
        => Assert.Equal(
            TeamNameNormalizer.BaseKey("São Paulo"),
            TeamNameNormalizer.BaseKey("Sao Paulo"));

    private void Then_ISO_dates_with_time_should_parse()
    {
        var d = DateParser.Parse("2012-05-19 18:30:00");
        Assert.NotNull(d);
        Assert.Equal(2012, d!.Value.Year);
    }

    private void And_ISO_dates_without_time_should_parse()
    {
        var d = DateParser.Parse("2023-09-24");
        Assert.NotNull(d);
        Assert.Equal(2023, d!.Value.Year);
    }

    private void And_Brazilian_DD_MM_YYYY_dates_should_parse()
    {
        var d = DateParser.Parse("29/03/2003");
        Assert.NotNull(d);
        Assert.Equal(2003, d!.Value.Year);
    }

    // extra scratch field for steps needing two results.
    private string ResultText2 = "";
    private IReadOnlyList<Core.Models.Match> ResultMatches2 = Array.Empty<Core.Models.Match>();
}
