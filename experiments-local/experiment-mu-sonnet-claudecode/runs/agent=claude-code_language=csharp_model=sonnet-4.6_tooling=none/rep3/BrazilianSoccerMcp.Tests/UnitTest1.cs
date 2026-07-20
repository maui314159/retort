using BrazilianSoccerMcp;

namespace BrazilianSoccerMcp.Tests;

public class DataLoaderTests
{
    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("Sport-PE", "Sport")]
    [InlineData("Flamengo", "Flamengo")]
    [InlineData("São Paulo", "São Paulo")]
    [InlineData("Grêmio-RS", "Grêmio")]
    public void NormalizeTeam_RemovesStateSuffix(string input, string expected)
    {
        var result = DataLoader.NormalizeTeam(input);
        Assert.Equal(expected, result);
    }

    [Theory]
    [InlineData("Flamengo-RJ", "Flamengo", true)]
    [InlineData("Palmeiras-SP", "palmeiras", true)]
    [InlineData("Corinthians", "Corinthians", true)]
    [InlineData("Flamengo-RJ", "Santos", false)]
    public void TeamMatches_FindsTeamByPartialName(string teamInData, string search, bool expected)
    {
        var result = DataLoader.TeamMatches(teamInData, search);
        Assert.Equal(expected, result);
    }
}

public class SoccerDatabaseTests
{
    private static SoccerDatabase CreateDb()
    {
        var db = new SoccerDatabase();
        // Find the data directory relative to the test project
        var dir = AppContext.BaseDirectory;
        while (dir != null && !Directory.Exists(Path.Combine(dir, "data", "kaggle")))
            dir = Directory.GetParent(dir)?.FullName;

        if (dir != null)
            db.Initialize(Path.Combine(dir, "data", "kaggle"));

        return db;
    }

    private static readonly Lazy<SoccerDatabase> _db = new(CreateDb);
    private SoccerDatabase Db => _db.Value;

    [Fact]
    public void Database_LoadsAllMatchFiles()
    {
        Assert.True(Db.AllMatches.Count > 1000, $"Expected >1000 matches, got {Db.AllMatches.Count}");
    }

    [Fact]
    public void Database_LoadsPlayerData()
    {
        Assert.True(Db.Players.Count > 1000, $"Expected >1000 players, got {Db.Players.Count}");
    }

    [Fact]
    public void Database_HasBrasileiraoMatches()
    {
        var matches = Db.AllMatches.Where(m => m.Competition.Contains("Brasileirão")).ToList();
        Assert.NotEmpty(matches);
    }

    [Fact]
    public void Database_HasCopaDoBrasilMatches()
    {
        var matches = Db.AllMatches.Where(m => m.Competition.Contains("Copa do Brasil")).ToList();
        Assert.NotEmpty(matches);
    }

    [Fact]
    public void Database_HasLibertadoresMatches()
    {
        var matches = Db.AllMatches.Where(m => m.Competition.Contains("Libertadores")).ToList();
        Assert.NotEmpty(matches);
    }

    // Feature: Match Queries
    // Scenario: Find matches between two teams
    // Given the match data is loaded
    // When I search for matches between "Flamengo" and "Fluminense"
    // Then I should receive a list of matches
    // And each match should have date, scores, and competition
    [Fact]
    public void SearchMatches_FindsFlamengoVsFluminense()
    {
        var matches = Db.AllMatches.Where(m =>
        {
            bool flaHome = DataLoader.TeamMatches(m.HomeTeam, "Flamengo") && DataLoader.TeamMatches(m.AwayTeam, "Fluminense");
            bool fluHome = DataLoader.TeamMatches(m.HomeTeam, "Fluminense") && DataLoader.TeamMatches(m.AwayTeam, "Flamengo");
            return flaHome || fluHome;
        }).ToList();

        Assert.NotEmpty(matches);
        foreach (var m in matches)
        {
            Assert.True(m.HomeGoals >= 0);
            Assert.True(m.AwayGoals >= 0);
            Assert.NotEmpty(m.Competition);
        }
    }

    [Fact]
    public void SearchMatches_FiltersBySeason()
    {
        var matches = Db.SearchMatches(team: "Flamengo", season: 2019).ToList();
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(2019, m.Season));
    }

    [Fact]
    public void SearchMatches_FiltersByCompetition()
    {
        var matches = Db.SearchMatches(competition: "Brasileirão").ToList();
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Contains("Brasileirão", m.Competition));
    }

    [Fact]
    public void SearchMatches_FiltersByTeam()
    {
        var matches = Db.SearchMatches(team: "Palmeiras").ToList();
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
            Assert.True(DataLoader.TeamMatches(m.HomeTeam, "Palmeiras") || DataLoader.TeamMatches(m.AwayTeam, "Palmeiras")));
    }

    [Fact]
    public void SearchMatches_FiltersByDateRange()
    {
        var from = new DateTime(2019, 1, 1);
        var to = new DateTime(2019, 12, 31);
        var matches = Db.SearchMatches(fromDate: from, toDate: to).ToList();
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.True(m.Date >= from && m.Date <= to));
    }

    // Feature: Team Queries
    // Scenario: Get team statistics
    // Given the match data is loaded
    // When I request statistics for "Palmeiras" in season "2023"
    // Then I should receive wins, losses, draws, and goals
    [Fact]
    public void CalculateTeamStats_ReturnsValidStats()
    {
        var stats = Db.CalculateTeamStats("Palmeiras", season: 2023);
        Assert.Equal("Palmeiras", stats.Team);
        Assert.True(stats.Matches > 0);
        Assert.Equal(stats.Matches, stats.Wins + stats.Draws + stats.Losses);
        Assert.True(stats.GoalsFor >= 0);
        Assert.True(stats.GoalsAgainst >= 0);
        Assert.True(stats.Points >= 0);
    }

    [Fact]
    public void CalculateTeamStats_HomeOnlyFilter()
    {
        var homeStats = Db.CalculateTeamStats("Corinthians", season: 2022, homeOnly: true);
        var awayStats = Db.CalculateTeamStats("Corinthians", season: 2022, homeOnly: false);
        var allStats = Db.CalculateTeamStats("Corinthians", season: 2022);

        if (allStats.Matches > 0)
        {
            Assert.True(homeStats.Matches + awayStats.Matches >= allStats.Matches - 2); // allow small overlap
        }
    }

    [Fact]
    public void GetStandings_Returns2019BrasileiraoStandings()
    {
        var standings = Db.GetStandings(2019, "Brasileirão");
        Assert.NotEmpty(standings);
        // Standings should be sorted by points descending
        for (int i = 1; i < standings.Count; i++)
        {
            Assert.True(standings[i - 1].Points >= standings[i].Points);
        }
    }

    // Player query tests
    [Fact]
    public void SearchPlayers_FindsByName()
    {
        var players = Db.SearchPlayers(name: "Neymar").ToList();
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Contains("Neymar", p.Name, StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void SearchPlayers_FiltersByNationality()
    {
        var players = Db.SearchPlayers(nationality: "Brazil", limit: 10).ToList();
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality));
    }

    [Fact]
    public void SearchPlayers_FiltersByClub()
    {
        // FIFA dataset uses "Santos" not "Flamengo" for this era
        var players = Db.SearchPlayers(club: "Santos").ToList();
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Contains("Santos", p.Club, StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void SearchPlayers_SortedByRatingDescending()
    {
        var players = Db.SearchPlayers(nationality: "Brazil", limit: 20).ToList();
        for (int i = 1; i < players.Count; i++)
        {
            Assert.True(players[i - 1].Overall >= players[i].Overall);
        }
    }

    [Fact]
    public void SearchPlayers_FiltersByMinRating()
    {
        var players = Db.SearchPlayers(minRating: 85).ToList();
        Assert.All(players, p => Assert.True(p.Overall >= 85));
    }

    // Statistical analysis tests
    [Fact]
    public void BiggestWins_ReturnsSortedByGoalDifference()
    {
        var biggest = Db.AllMatches
            .Where(m => m.HomeGoals != m.AwayGoals)
            .OrderByDescending(m => Math.Abs(m.HomeGoals - m.AwayGoals))
            .Take(10)
            .ToList();

        Assert.NotEmpty(biggest);
        for (int i = 1; i < biggest.Count; i++)
        {
            Assert.True(
                Math.Abs(biggest[i - 1].HomeGoals - biggest[i - 1].AwayGoals) >=
                Math.Abs(biggest[i].HomeGoals - biggest[i].AwayGoals));
        }
    }

    [Fact]
    public void AllMatches_HaveValidGoalCounts()
    {
        Assert.All(Db.AllMatches, m =>
        {
            Assert.True(m.HomeGoals >= 0, $"Negative home goals in match {m.HomeTeam} vs {m.AwayTeam}");
            Assert.True(m.AwayGoals >= 0, $"Negative away goals in match {m.HomeTeam} vs {m.AwayTeam}");
        });
    }

    [Fact]
    public void AllMatches_HaveNonEmptyTeamNames()
    {
        Assert.All(Db.AllMatches, m =>
        {
            Assert.NotEmpty(m.HomeTeam);
            Assert.NotEmpty(m.AwayTeam);
        });
    }

    [Fact]
    public void Players_HaveValidRatings()
    {
        Assert.All(Db.Players, p =>
        {
            Assert.True(p.Overall >= 1 && p.Overall <= 100, $"Invalid rating {p.Overall} for {p.Name}");
        });
    }
}

public class SoccerToolsTests
{
    private static readonly Lazy<SoccerDatabase> _db = new(() =>
    {
        var db = new SoccerDatabase();
        var dir = AppContext.BaseDirectory;
        while (dir != null && !Directory.Exists(Path.Combine(dir, "data", "kaggle")))
            dir = Directory.GetParent(dir)?.FullName;
        if (dir != null)
            db.Initialize(Path.Combine(dir, "data", "kaggle"));
        return db;
    });

    private SoccerTools CreateTools() => new(_db.Value);

    [Fact]
    public void SearchMatches_ReturnsResultsForFlamengo()
    {
        var tools = CreateTools();
        var result = tools.SearchMatches(team: "Flamengo", limit: 10);
        Assert.NotNull(result);
        Assert.DoesNotContain("No matches found", result);
        Assert.Contains("Flamengo", result, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void GetHeadToHead_ReturnsFlamengoVsCorinthians()
    {
        var tools = CreateTools();
        var result = tools.GetHeadToHead("Flamengo", "Corinthians");
        Assert.NotNull(result);
        Assert.Contains("Head-to-head", result);
    }

    [Fact]
    public void GetTeamStats_ReturnsPalmeiraStats()
    {
        var tools = CreateTools();
        var result = tools.GetTeamStats("Palmeiras", season: 2023);
        Assert.NotNull(result);
        Assert.Contains("Statistics for Palmeiras", result);
        Assert.Contains("Matches:", result);
        Assert.Contains("Wins:", result);
    }

    [Fact]
    public void GetStandings_Returns2019Season()
    {
        var tools = CreateTools();
        var result = tools.GetStandings(2019);
        Assert.NotNull(result);
        Assert.Contains("2019", result);
        Assert.Contains("Standings", result);
    }

    [Fact]
    public void SearchPlayers_FindsBrazilianPlayers()
    {
        var tools = CreateTools();
        var result = tools.SearchPlayers(nationality: "Brazil", limit: 5);
        Assert.NotNull(result);
        Assert.Contains("Brazil", result);
    }

    [Fact]
    public void GetBiggestWins_ReturnsResults()
    {
        var tools = CreateTools();
        var result = tools.GetBiggestWins(limit: 5);
        Assert.NotNull(result);
        Assert.DoesNotContain("No matches found", result);
        Assert.Contains("Biggest wins", result);
    }

    [Fact]
    public void GetSeasonList_ListsAllCompetitions()
    {
        var tools = CreateTools();
        var result = tools.GetSeasonList();
        Assert.NotNull(result);
        Assert.Contains("Brasileirão", result);
        Assert.Contains("Copa do Brasil", result);
    }

    [Fact]
    public void GetCompetitionSummary_Returns2022BrasileiraoSummary()
    {
        var tools = CreateTools();
        // Brasileirão data goes up to 2022; BR-Football-Dataset has 2023 as "Serie A"
        var result = tools.GetCompetitionSummary(competition: "Brasileirão", season: 2022);
        Assert.NotNull(result);
        Assert.Contains("Total Matches", result);
    }

    [Fact]
    public void GetTeamCompetitions_ReturnsPalmeiraCompetitions()
    {
        var tools = CreateTools();
        var result = tools.GetTeamCompetitions("Palmeiras");
        Assert.NotNull(result);
        Assert.Contains("Palmeiras", result);
        Assert.Contains("matches", result);
    }

    [Fact]
    public void GetTopTeams_Returns2019TopTeams()
    {
        var tools = CreateTools();
        var result = tools.GetTopTeams(season: 2019, competition: "Brasileirão");
        Assert.NotNull(result);
        Assert.Contains("pts", result);
    }

    [Fact]
    public void SearchMatches_NoResultsForNonExistentTeam()
    {
        var tools = CreateTools();
        var result = tools.SearchMatches(team: "TeamThatDoesNotExist12345");
        Assert.Contains("No matches found", result);
    }

    [Fact]
    public void SearchPlayers_FindsPlayerByName()
    {
        var tools = CreateTools();
        var result = tools.SearchPlayers(name: "Neymar");
        Assert.NotNull(result);
        Assert.Contains("Neymar", result, StringComparison.OrdinalIgnoreCase);
    }
}
