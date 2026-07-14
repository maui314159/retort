using BrazilianSoccerMCP.Data;
using BrazilianSoccerMCP.Models;
using BrazilianSoccerMCP.Tools;

namespace BrazilianSoccerMCP.Tests;

public class DataLoadingTests
{
    [Fact]
    public void Load_Brasileirao_Matches_Should_Succeed()
    {
        var loader = new DataLoader();
        var matches = loader.LoadBrasileiraoMatches();
        Assert.NotEmpty(matches);
        Assert.True(matches.Count >= 4000, $"Expected 4000+, got {matches.Count}");
        Assert.All(matches, m =>
        {
            Assert.False(string.IsNullOrEmpty(m.HomeTeam));
            Assert.False(string.IsNullOrEmpty(m.AwayTeam));
            Assert.True(m.Season >= 2012);
        });
    }

    [Fact]
    public void Load_Copa_Brasil_Matches_Should_Succeed()
    {
        var loader = new DataLoader();
        var matches = loader.LoadCopaBrasilMatches();
        Assert.NotEmpty(matches);
        Assert.True(matches.Count >= 1000, $"Expected 1000+, got {matches.Count}");
    }

    [Fact]
    public void Load_Libertadores_Matches_Should_Succeed()
    {
        var loader = new DataLoader();
        var matches = loader.LoadLibertadoresMatches();
        Assert.NotEmpty(matches);
        Assert.True(matches.Count >= 1000, $"Expected 1000+, got {matches.Count}");
    }

    [Fact]
    public void Load_Extended_Matches_Should_Succeed()
    {
        var loader = new DataLoader();
        var matches = loader.LoadExtendedMatches();
        Assert.NotEmpty(matches);
        Assert.True(matches.Count >= 10000, $"Expected 10000+, got {matches.Count}");
    }

    [Fact]
    public void Load_Historical_Matches_Should_Succeed()
    {
        var loader = new DataLoader();
        var matches = loader.LoadHistoricalMatches();
        Assert.NotEmpty(matches);
        Assert.True(matches.Count >= 6000, $"Expected 6000+, got {matches.Count}");
    }

    [Fact]
    public void Load_Fifa_Players_Should_Succeed()
    {
        var loader = new DataLoader();
        var players = loader.LoadFifaPlayers();
        Assert.NotEmpty(players);
        Assert.True(players.Count >= 18000, $"Expected 18000+, got {players.Count}");
    }

    [Fact]
    public void Load_All_Unified_Matches_Should_Combine_Datasets()
    {
        var loader = new DataLoader();
        var matches = loader.LoadAllUnifiedMatches();
        Assert.NotEmpty(matches);
        // Should combine Brasileirao + Copa Brasil + Libertadores + Extended + Historical
        Assert.True(matches.Count > 15000, $"Expected >15000, got {matches.Count}");
    }
}

public class TeamNormalizerTests
{
    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("Flamengo-RJ", "flamengo")]
    [InlineData("Sao Paulo-SP", "São Paulo")]
    [InlineData("Corinthians-SP", "Corinthians")]
    [InlineData("Gremio-RS", "Grêmio")]
    [InlineData("Vasco da Gama-RJ", "Vasco da Gama")]
    public void Normalize_State_Suffix_Teams_Match(string withSuffix, string withoutSuffix)
    {
        Assert.True(TeamNormalizer.Matches(withSuffix, withoutSuffix),
            $"Expected '{withSuffix}' to match '{withoutSuffix}'");
    }

    [Theory]
    [InlineData("São Paulo", "Sao Paulo")]
    [InlineData("Grêmio", "Gremio")]
    [InlineData("Atlético-MG", "Atletico-MG")]
    [InlineData("Avaí", "Avai")]
    public void Accent_Insensitive_Matching(string accented, string unaccented)
    {
        Assert.True(TeamNormalizer.Matches(accented, unaccented),
            $"Expected '{accented}' to match '{unaccented}'");
    }

    [Fact]
    public void Different_Teams_Should_Not_Match()
    {
        Assert.False(TeamNormalizer.Matches("Palmeiras", "Flamengo"));
        Assert.False(TeamNormalizer.Matches("Corinthians", "Santos"));
    }

    [Fact]
    public void Dot_Abbreviated_Names_Should_Normalize()
    {
        var normalized = TeamNormalizer.Normalize("A.b.c. - RN");
        Assert.DoesNotContain(".", normalized);
        Assert.Contains("abc", normalized, StringComparison.OrdinalIgnoreCase);
    }
}

public class SoccerToolsTests
{
    private readonly SoccerTools _tools = new();

    [Fact]
    public void Search_Matches_By_Team_Should_Return_Results()
    {
        var result = _tools.search_matches(team: "Flamengo");
        Assert.NotNull(result);
        Assert.Contains("Flamengo", result, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Head_To_Head_Should_Return_Stats()
    {
        var result = _tools.head_to_head("Flamengo", "Fluminense");
        Assert.NotNull(result);
        Assert.Contains("Flamengo", result, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("Fluminense", result, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Team_Statistics_Should_Return_Stats()
    {
        var result = _tools.team_statistics("Palmeiras");
        Assert.NotNull(result);
        Assert.Contains("Palmeiras", result, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("Matches", result);
    }

    [Fact]
    public void Team_Statistics_With_Season_Should_Filter()
    {
        var result = _tools.team_statistics("Flamengo", season: 2019);
        Assert.NotNull(result);
        Assert.Contains("2019", result);
        Assert.Contains("Flamengo", result, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Search_Players_By_Nationality_Should_Return_Brazilians()
    {
        var result = _tools.search_players(nationality: "Brazil");
        Assert.NotNull(result);
        Assert.Contains("Brazil", result, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Search_Players_By_Name_Should_Find()
    {
        var result = _tools.search_players(name: "Neymar");
        Assert.NotNull(result);
        Assert.Contains("Neymar", result, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Team_Players_Should_List_Club_Players()
    {
        var result = _tools.team_players("Flamengo");
        Assert.NotNull(result);
        // Should find players at Flamengo
        Assert.True(result.Length > 10, "Expected player listing for Flamengo");
    }

    [Fact]
    public void Competition_Standings_Should_Calculate()
    {
        var result = _tools.competition_standings("Brasileirão", 2019);
        Assert.NotNull(result);
        Assert.Contains("2019", result);
    }

    [Fact]
    public void Competition_Winners_Should_Return_Winners()
    {
        var result = _tools.competition_winners("Brasileirão");
        Assert.NotNull(result);
        Assert.True(result.Length > 0, "Expected winner listing");
    }

    [Fact]
    public void Biggest_Wins_Should_Return_Results()
    {
        var result = _tools.biggest_wins();
        Assert.NotNull(result);
        Assert.True(result.Length > 10, "Expected biggest wins listing");
    }

    [Fact]
    public void Goals_Per_Match_Average_Should_Return_Stats()
    {
        var result = _tools.goals_per_match_average();
        Assert.NotNull(result);
        Assert.Contains("goals per match", result, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Team_Season_Comparison_Should_Compare()
    {
        var result = _tools.team_season_comparison("Flamengo", 2019, 2020);
        Assert.NotNull(result);
        Assert.Contains("2019", result);
        Assert.Contains("2020", result);
    }

    [Fact]
    public void Search_Matches_No_Results_Should_Say_No_Matches()
    {
        var result = _tools.search_matches(team: "TimeInexistenteXYZ");
        Assert.Contains("No matches found", result, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Search_Players_No_Results_Should_Say_No_Players()
    {
        var result = _tools.search_players(name: "JogadorInexistenteXYZ");
        Assert.Contains("No players found", result, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Team_Home_Record_Should_Return_Stats()
    {
        var result = _tools.team_home_record("Corinthians", season: 2022);
        Assert.NotNull(result);
        Assert.Contains("home", result, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Team_Away_Record_Should_Return_Stats()
    {
        var result = _tools.team_away_record("Corinthians", season: 2022);
        Assert.NotNull(result);
        Assert.Contains("away", result, StringComparison.OrdinalIgnoreCase);
    }
}
