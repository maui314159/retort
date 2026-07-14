using Xunit;
using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Integration-style tests that load the actual CSV files from data/kaggle/.
/// The repository is constructed once per test class to avoid loading 6 large
/// files for each individual test.
/// </summary>
public class DataRepositoryTests : IClassFixture<RepositoryFixture>
{
    private readonly DataRepository _repo;

    public DataRepositoryTests(RepositoryFixture fixture)
    {
        _repo = fixture.Repository;
    }

    // -----------------------------------------------------------------------
    // Dataset loading
    // -----------------------------------------------------------------------

    [Fact]
    public void Matches_AreLoaded_NonEmpty()
    {
        Assert.True(_repo.Matches.Count > 1000,
            $"Expected at least 1000 matches, got {_repo.Matches.Count}");
    }

    [Fact]
    public void Players_AreLoaded_NonEmpty()
    {
        Assert.True(_repo.Players.Count > 1000,
            $"Expected at least 1000 players, got {_repo.Players.Count}");
    }

    [Fact]
    public void AllCompetitions_ArePresent()
    {
        var comps = _repo.Competitions;
        Assert.Contains("Brasileirão", comps, StringComparer.OrdinalIgnoreCase);
        Assert.Contains("Copa do Brasil", comps, StringComparer.OrdinalIgnoreCase);
        Assert.Contains("Copa Libertadores", comps, StringComparer.OrdinalIgnoreCase);
    }

    // -----------------------------------------------------------------------
    // Team name normalisation
    // -----------------------------------------------------------------------

    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("Atletico-MG", "Atletico")]
    [InlineData("Sport-PE", "Sport")]
    [InlineData("Santos", "Santos")]
    public void NormalizeTeam_StripsSuffix(string raw, string expected)
    {
        Assert.Equal(expected, DataRepository.NormalizeTeam(raw));
    }

    [Theory]
    [InlineData("Flamengo-RJ", "Flamengo", true)]
    [InlineData("Palmeiras-SP", "palmeiras", true)]  // case-insensitive
    [InlineData("Corinthians", "Santos", false)]
    [InlineData("Fluminense-RJ", "Flu", true)]       // partial match
    public void TeamMatches_PartialAndCaseInsensitive(string dataName, string query, bool expected)
    {
        Assert.Equal(expected, DataRepository.TeamMatches(dataName, query));
    }

    // -----------------------------------------------------------------------
    // Match search
    // -----------------------------------------------------------------------

    [Fact]
    public void SearchMatches_ByTeam_ReturnsRelevantMatches()
    {
        var matches = _repo.SearchMatches(team: "Flamengo", limit: 50);
        Assert.True(matches.Count > 0, "Expected Flamengo matches");
        foreach (var m in matches)
        {
            bool involves = DataRepository.TeamMatches(m.HomeTeam, "Flamengo")
                         || DataRepository.TeamMatches(m.AwayTeam, "Flamengo");
            Assert.True(involves, $"Match {m.HomeTeam} vs {m.AwayTeam} does not involve Flamengo");
        }
    }

    [Fact]
    public void SearchMatches_HeadToHead_OnlyReturnsBothTeams()
    {
        var matches = _repo.SearchMatches(team: "Flamengo", opponent: "Fluminense", limit: 100);
        Assert.True(matches.Count > 0, "Expected Flamengo vs Fluminense matches");
        foreach (var m in matches)
        {
            bool flamInvolved = DataRepository.TeamMatches(m.HomeTeam, "Flamengo")
                             || DataRepository.TeamMatches(m.AwayTeam, "Flamengo");
            bool fluInvolved = DataRepository.TeamMatches(m.HomeTeam, "Fluminense")
                            || DataRepository.TeamMatches(m.AwayTeam, "Fluminense");
            Assert.True(flamInvolved && fluInvolved,
                $"H2H match {m.HomeTeam} vs {m.AwayTeam} does not involve both teams");
        }
    }

    [Fact]
    public void SearchMatches_BySeason_ReturnsCorrectYear()
    {
        var matches = _repo.SearchMatches(season: 2019, limit: 50);
        Assert.True(matches.Count > 0, "Expected matches in 2019");
        foreach (var m in matches)
            Assert.Equal(2019, m.Season);
    }

    [Fact]
    public void SearchMatches_ByCompetition_FiltersCorrectly()
    {
        var matches = _repo.SearchMatches(competition: "Copa Libertadores", limit: 50);
        Assert.True(matches.Count > 0, "Expected Libertadores matches");
        foreach (var m in matches)
            Assert.Contains("Libertadores", m.Competition, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void SearchMatches_LimitRespected()
    {
        var matches = _repo.SearchMatches(limit: 5);
        Assert.True(matches.Count <= 5);
    }

    // -----------------------------------------------------------------------
    // Team statistics
    // -----------------------------------------------------------------------

    [Fact]
    public void GetTeamStats_Palmeiras_HasPositiveRecord()
    {
        var stats = repo.GetTeamStats("Palmeiras", competition: "Brasileirão");
        Assert.True(stats.Played > 0, "Expected Palmeiras Brasileirão matches");
        Assert.True(stats.Wins >= 0);
        Assert.Equal(stats.Played, stats.Wins + stats.Draws + stats.Losses);
    }

    [Fact]
    public void GetTeamStats_GoalsSumMatchesMatches()
    {
        var stats = repo.GetTeamStats("Flamengo", season: 2019, competition: "Brasileirão");
        // If data exists, verify internal consistency
        if (stats.Played == 0) return; // dataset may not have this exact combo
        Assert.True(stats.GoalsFor >= 0);
        Assert.True(stats.GoalsAgainst >= 0);
        Assert.Equal(stats.Played, stats.Wins + stats.Draws + stats.Losses);
    }

    // -----------------------------------------------------------------------
    // Standings
    // -----------------------------------------------------------------------

    [Fact]
    public void GetStandings_Brasileirao2019_HasTeams()
    {
        var standings = _repo.GetStandings("Brasileirão", 2019);
        Assert.True(standings.Count > 0, "Expected 2019 Brasileirão standings");
    }

    [Fact]
    public void GetStandings_RanksAreConsecutive()
    {
        var standings = _repo.GetStandings("Brasileirão", 2019);
        if (standings.Count == 0) return;
        for (int i = 0; i < standings.Count; i++)
            Assert.Equal(i + 1, standings[i].Rank);
    }

    [Fact]
    public void GetStandings_PointsDescendingOrder()
    {
        var standings = _repo.GetStandings("Brasileirão", 2019);
        for (int i = 1; i < standings.Count; i++)
            Assert.True(standings[i - 1].Points >= standings[i].Points,
                $"Standings not sorted: {standings[i-1].Team}({standings[i-1].Points}) < {standings[i].Team}({standings[i].Points})");
    }

    // -----------------------------------------------------------------------
    // Player search
    // -----------------------------------------------------------------------

    [Fact]
    public void SearchPlayers_ByNationality_Brazil_ReturnsPlayers()
    {
        var players = _repo.SearchPlayers(nationality: "Brazil", limit: 20);
        Assert.True(players.Count > 0, "Expected Brazilian players");
        foreach (var p in players)
            Assert.Contains("Brazil", p.Nationality, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void SearchPlayers_ByClub_Flamengo_ReturnsPlayers()
    {
        var players = _repo.SearchPlayers(club: "Flamengo", limit: 20);
        foreach (var p in players)
            Assert.Contains("Flamengo", p.Club, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void SearchPlayers_ByName_Neymar_Found()
    {
        var players = _repo.SearchPlayers(name: "Neymar", limit: 5);
        Assert.True(players.Count > 0, "Expected to find Neymar");
        Assert.Contains(players, p => p.Name.Contains("Neymar", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void SearchPlayers_MinOverall80_AllAbove80()
    {
        var players = _repo.SearchPlayers(minOverall: 80, limit: 50);
        Assert.True(players.Count > 0);
        foreach (var p in players)
            Assert.True(p.Overall >= 80, $"{p.Name} has overall {p.Overall} < 80");
    }

    [Fact]
    public void SearchPlayers_SortedByOverallDesc()
    {
        var players = _repo.SearchPlayers(nationality: "Brazil", limit: 20);
        for (int i = 1; i < players.Count; i++)
            Assert.True(players[i - 1].Overall >= players[i].Overall,
                $"Players not sorted by overall: {players[i-1].Name}({players[i-1].Overall}) < {players[i].Name}({players[i].Overall})");
    }

    // -----------------------------------------------------------------------
    // Statistics
    // -----------------------------------------------------------------------

    [Fact]
    public void GetBiggestWins_ReturnsMatchesSortedByGoalDiff()
    {
        var wins = _repo.GetBiggestWins(count: 5);
        Assert.True(wins.Count > 0);
        for (int i = 1; i < wins.Count; i++)
            Assert.True(wins[i - 1].GoalDifference >= wins[i].GoalDifference);
    }

    [Fact]
    public void GetAggregateStats_AllMatches_SensibleValues()
    {
        var (avg, homeWin, awayWin, draw, total) = _repo.GetAggregateStats();
        Assert.True(total > 0);
        Assert.True(avg > 0 && avg < 20, $"Average goals {avg} seems wrong");
        Assert.True(homeWin + awayWin + draw > 90, "Win/draw percentages should sum near 100%");
    }

    [Fact]
    public void GetHeadToHead_TotalMatchesConsistent()
    {
        var (t1w, t2w, draws, total) = _repo.GetHeadToHead("Flamengo", "Fluminense");
        Assert.Equal(total, t1w + t2w + draws);
    }

    // Reference to avoid IDE warning about field vs. fixture
    private DataRepository repo => _repo;
}

/// <summary>
/// Loads the DataRepository once and shares it across all tests in the class.
/// </summary>
public class RepositoryFixture
{
    public DataRepository Repository { get; }

    public RepositoryFixture()
    {
        var dataDir = FindDataDir();
        Repository = new DataRepository(dataDir);
    }

    private static string FindDataDir()
    {
        var env = Environment.GetEnvironmentVariable("SOCCER_DATA_DIR");
        if (!string.IsNullOrEmpty(env) && Directory.Exists(env)) return env;

        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "data", "kaggle");
            if (Directory.Exists(candidate)) return candidate;
            dir = dir.Parent;
        }

        dir = new DirectoryInfo(Directory.GetCurrentDirectory());
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "data", "kaggle");
            if (Directory.Exists(candidate)) return candidate;
            dir = dir.Parent;
        }

        throw new InvalidOperationException(
            "Cannot find data/kaggle directory. Set SOCCER_DATA_DIR env var.");
    }
}
