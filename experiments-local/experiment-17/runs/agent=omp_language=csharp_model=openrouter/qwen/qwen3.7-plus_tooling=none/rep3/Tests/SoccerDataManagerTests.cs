using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Xunit;

public class SoccerDataManagerTests
{
    private readonly SoccerDataManager _dataManager;

    public SoccerDataManagerTests()
    {
        // The data path is relative to the test project, so we go up one directory
        var dataPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", "data", "kaggle");
        _dataManager = new SoccerDataManager(dataPath);
    }

    [Fact]
    public async Task LoadDataAsync_ShouldLoadMatches()
    {
        await _dataManager.LoadDataAsync();
        Assert.NotEmpty(_dataManager.Matches);
        Assert.True(_dataManager.Matches.Count > 10000); // We have multiple CSVs with thousands of matches
    }

    [Fact]
    public async Task LoadDataAsync_ShouldLoadPlayers()
    {
        await _dataManager.LoadDataAsync();
        Assert.NotEmpty(_dataManager.Players);
        Assert.True(_dataManager.Players.Count > 10000);
    }

    [Fact]
    public async Task SearchMatches_ShouldFindMatchesByTeam()
    {
        await _dataManager.LoadDataAsync();
        var matches = _dataManager.SearchMatches("Flamengo", null, null, null, null);
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Contains("Flamengo", m.HomeTeam + " " + m.AwayTeam, StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public async Task GetTeamStats_ShouldCalculateCorrectly()
    {
        await _dataManager.LoadDataAsync();
        var stats = _dataManager.GetTeamStats("Palmeiras", "2023");
        Assert.NotNull(stats);
        Assert.Equal("Palmeiras", stats.Team);
        Assert.True(stats.Matches > 0);
        Assert.True(stats.Wins + stats.Draws + stats.Losses == stats.Matches);
    }

    [Fact]
    public async Task GetHeadToHead_ShouldReturnMatches()
    {
        await _dataManager.LoadDataAsync();
        var h2h = _dataManager.GetHeadToHead("Flamengo", "Fluminense");
        Assert.NotNull(h2h);
        Assert.True(h2h.Matches.Count > 0);
        Assert.True(h2h.Team1Wins + h2h.Team2Wins + h2h.Draws == h2h.Matches.Count);
    }

    [Fact]
    public async Task SearchPlayers_ShouldFindPlayersByNationality()
    {
        await _dataManager.LoadDataAsync();
        var players = _dataManager.SearchPlayers(null, "Brazil", null, null, 80);
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Contains("Brazil", p.Nationality, StringComparison.OrdinalIgnoreCase));
        Assert.All(players, p => Assert.True(p.Overall >= 80));
    }

    [Fact]
    public async Task GetCompetitionStandings_ShouldCalculatePoints()
    {
        await _dataManager.LoadDataAsync();
        var standings = _dataManager.GetCompetitionStandings("Brasileirão", "2019");
        Assert.NotEmpty(standings);
        // Flamengo won in 2019
        var flamengo = standings.FirstOrDefault(s => s.Team.Contains("Flamengo", StringComparison.OrdinalIgnoreCase));
        Assert.NotNull(flamengo);
        Assert.True(flamengo.Points > 70); // Flamengo had 90 points in 2019
    }

    [Fact]
    public async Task GetStatisticalAnalysis_ShouldReturnValidData()
    {
        await _dataManager.LoadDataAsync();
        var avgGoals = _dataManager.GetStatisticalAnalysis("average_goals");
        Assert.NotNull(avgGoals);
        Assert.Contains("Average goals per match", avgGoals);

        var biggestWins = _dataManager.GetStatisticalAnalysis("biggest_wins");
        Assert.NotNull(biggestWins);
        Assert.Contains("Biggest victories", biggestWins);

        var homeWinRate = _dataManager.GetStatisticalAnalysis("home_win_rate");
        Assert.NotNull(homeWinRate);
        Assert.Contains("Home win rate", homeWinRate);
    }

    [Fact]
    public void NormalizeTeamName_ShouldRemoveStateSuffix()
    {
        Assert.Equal("Palmeiras", SoccerDataManager.NormalizeTeamName("Palmeiras-SP"));
        Assert.Equal("Flamengo", SoccerDataManager.NormalizeTeamName("Flamengo-RJ"));
        Assert.Equal("Atletico Mineiro", SoccerDataManager.NormalizeTeamName("Atletico-MG"));
    }
}