using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

/// <summary>Loads the real Kaggle CSVs once for all integration tests.</summary>
public sealed class RealDataFixture : IDisposable
{
    public DataLoader Loader { get; }
    public SoccerDataService Service { get; }

    public RealDataFixture()
    {
        var dir = DataLoader.ResolveDataDirectory(AppContext.BaseDirectory);
        Loader = DataLoader.LoadAll(dir);
        Service = new SoccerDataService(Loader);
    }

    public void Dispose() { }
}

/// <summary>
/// BDD scenarios over the real datasets, mapped to the sample questions in the
/// specification (TASK.md). Method names follow Given/When/Then.
/// </summary>
public class RealDataIntegrationTests : IClassFixture<RealDataFixture>
{
    private readonly RealDataFixture _fx;

    public RealDataIntegrationTests(RealDataFixture fx) => _fx = fx;

    private SoccerDataService Service => _fx.Service;

    // ---------- Data coverage ----------

    [Fact]
    public void GivenCsvFiles_WhenLoaded_ThenAllSixDatasetsAreQueryable()
    {
        // Given the data directory, when loaded, then every file produced rows
        var files = _fx.Loader.Datasets.Select(d => d.File).ToList();
        foreach (var required in DataLoader.RequiredFiles)
            Assert.Contains(required, files);

        // And the row counts match the documented dataset sizes
        Assert.Equal(4180, _fx.Loader.Datasets.Single(d => d.File == "Brasileirao_Matches.csv").RowCount);
        Assert.Equal(1337, _fx.Loader.Datasets.Single(d => d.File == "Brazilian_Cup_Matches.csv").RowCount);
        Assert.Equal(1255, _fx.Loader.Datasets.Single(d => d.File == "Libertadores_Matches.csv").RowCount);
        Assert.Equal(10296, _fx.Loader.Datasets.Single(d => d.File == "BR-Football-Dataset.csv").RowCount);
        Assert.Equal(6886, _fx.Loader.Datasets.Single(d => d.File == "novo_campeonato_brasileiro.csv").RowCount);
        Assert.Equal(18207, _fx.Loader.Datasets.Single(d => d.File == "fifa_data.csv").RowCount);
    }

    [Fact]
    public void GivenCsvFiles_WhenLoaded_ThenCrossFileDuplicatesAreRemoved()
    {
        // Given the overlapping files, when loaded and deduplicated,
        // then fewer unique fixtures remain than raw rows
        Assert.True(_fx.Loader.Matches.Count < 4180 + 1337 + 1255 + 10296 + 6886);
        Assert.True(_fx.Loader.Matches.Count > 15000);
    }

    // ---------- 1. Match queries ----------

    [Fact]
    public void GivenMatchData_WhenSearchingFlamengoVsFluminense_ThenReturnsMatchesWithScoresAndCompetition()
    {
        // "Show me all Flamengo vs Fluminense matches"
        var matches = Service.FindMatches(new SoccerDataService.MatchFilter
        { Team = "Flamengo", Opponent = "Fluminense", Limit = 100 });

        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.True(m.Played);
            Assert.False(string.IsNullOrEmpty(m.Competition));
            Assert.NotNull(m.Date);
        });
        Assert.Contains(matches, m => m.Competition == DataLoader.BrasileiraoSerieA);
    }

    [Fact]
    public void GivenMatchData_WhenSearchingPalmeiras2023_ThenReturnsSeasonMatches()
    {
        // "What matches did Palmeiras play in 2023?"
        var matches = Service.FindMatches(new SoccerDataService.MatchFilter
        { Team = "Palmeiras", Season = 2023, Limit = 200 });

        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(2023, m.Season));
    }

    [Fact]
    public void GivenMatchData_WhenSearchingCopaDoBrasilFinals_ThenReturnsTwoLeggedFinals()
    {
        // "Find all Copa do Brasil finals"
        var matches = Service.FindMatches(new SoccerDataService.MatchFilter
        { Competition = "Copa do Brasil", Round = "Final", Limit = 100 });

        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.Equal(DataLoader.CopaDoBrasil, m.Competition);
            Assert.Equal("Final", m.Round);
        });
        // The 2018 two-legged final: Cruzeiro vs Corinthians
        Assert.Contains(matches, m => m.Season == 2018 &&
            m.HomeTeamCanonical == "Cruzeiro" && m.AwayTeamCanonical == "Corinthians");
    }

    [Fact]
    public void GivenMatchData_WhenSearchingByDateRange_ThenRespectsTheWindow()
    {
        // "Flamengo matches in September 2021"
        var matches = Service.FindMatches(new SoccerDataService.MatchFilter
        { Team = "Flamengo", From = new DateOnly(2021, 9, 1), To = new DateOnly(2021, 9, 30), Limit = 100 });

        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.InRange(m.Date!.Value, new DateOnly(2021, 9, 1), new DateOnly(2021, 9, 30)));
    }

    [Fact]
    public void GivenMatchData_WhenAskedLastFlamengoCorinthians_ThenReturnsMostRecentMeeting()
    {
        // "When did Flamengo last play Corinthians?"
        var matches = Service.FindMatches(new SoccerDataService.MatchFilter
        { Team = "Flamengo", Opponent = "Corinthians", Limit = 1 });

        Assert.Single(matches);
        Assert.True(matches[0].Date >= new DateOnly(2022, 1, 1));
        Assert.True(matches[0].Played);
    }

    // ---------- 2. Team queries ----------

    [Fact]
    public void GivenMatchData_WhenRequestingCorinthiansHomeRecord2022_ThenReturnsNineteenHomeMatches()
    {
        // "What is Corinthians' home record in 2022?"
        var stats = Service.GetTeamStatistics("Corinthians", season: 2022,
            competition: "Brasileirão", venue: SoccerDataService.Venue.Home);

        Assert.Equal(19, stats.Matches);
        Assert.Equal(19, stats.Wins + stats.Draws + stats.Losses);
        Assert.True(stats.Wins >= 10); // strong home side that year
        Assert.True(stats.WinRate > 50.0);
    }

    [Fact]
    public void GivenMatchData_WhenComparingPalmeirasAndSantos_ThenReturnsHeadToHeadSummary()
    {
        // "Compare Palmeiras and Santos head-to-head"
        var h2h = Service.HeadToHead("Palmeiras", "Santos", matchLimit: 500);

        Assert.NotEmpty(h2h.Matches);
        // The W/D/L summary must account for every listed meeting
        Assert.Equal(h2h.Matches.Count, h2h.Team1Wins + h2h.Team2Wins + h2h.Draws);
        Assert.True(h2h.Matches.Count >= 20); // decades of meetings across the files
    }

    [Fact]
    public void GivenMatchData_WhenRequestingTeamCompetitions_ThenListsAllCompetitions()
    {
        // "What competitions has Palmeiras played in?"
        var competitions = Service.TeamCompetitions("Palmeiras");

        Assert.Contains(DataLoader.BrasileiraoSerieA, competitions);
        Assert.Contains(DataLoader.CopaDoBrasil, competitions);
        Assert.Contains(DataLoader.CopaLibertadores, competitions);
    }

    // ---------- 3. Player queries ----------

    [Fact]
    public void GivenFifaData_WhenSearchingBrazilianPlayers_ThenReturnsHundreds()
    {
        // "Find all Brazilian players in the dataset"
        var players = Service.SearchPlayers(new SoccerDataService.PlayerFilter
        { Nationality = "Brazil", Limit = 200 });

        Assert.Equal(200, players.Count); // capped by the page size...
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality));
    }

    [Fact]
    public void GivenFifaData_WhenSearchingNeymar_ThenReturnsThePlayer()
    {
        // "Who is Neymar?" (spec: 'Who is Gabriel Barbosa?' - same lookup pattern)
        var players = Service.SearchPlayers(new SoccerDataService.PlayerFilter { Name = "Neymar" });

        Assert.NotEmpty(players);
        Assert.Contains(players, p => p.Name.Contains("Neymar", StringComparison.OrdinalIgnoreCase));
        Assert.All(players, p => Assert.True(p.Overall > 0));
    }

    [Fact]
    public void GivenFifaData_WhenRequestingTopBrazilians_ThenNeymarLeads()
    {
        // "Who are the top Brazilian players?"
        var top = Service.TopPlayers(nationality: "Brazil", limit: 5);

        Assert.Equal(5, top.Count);
        Assert.Equal("Neymar Jr", top[0].Name);
        Assert.True(top[0].Overall >= 90);
        Assert.True(top[^1].Overall >= top[0].Overall - 10);
    }

    [Fact]
    public void GivenFifaData_WhenFilteringGremioPlayers_ThenReturnsSquad()
    {
        // "Which players play for Grêmio?" (spec uses Flamengo; FIFA data lacks Flamengo)
        var players = Service.SearchPlayers(new SoccerDataService.PlayerFilter { Club = "Grêmio", Limit = 50 });

        Assert.Equal(20, players.Count);
        Assert.All(players, p => Assert.Equal("Grêmio", p.Club));
    }

    [Fact]
    public void GivenFifaData_WhenFilteringSantosForwards_ThenReturnsStrikers()
    {
        // "Show me all forwards from São Paulo FC" (pattern; FIFA data uses Santos here)
        var players = Service.SearchPlayers(new SoccerDataService.PlayerFilter
        { Club = "Santos", Position = "ST", Limit = 50 });

        // Club search is a substring match (per spec), so "Santos Laguna" may also appear
        Assert.NotEmpty(players);
        Assert.All(players, p =>
        {
            Assert.Contains("Santos", p.Club, StringComparison.Ordinal);
            Assert.Equal("ST", p.Position);
        });
        Assert.True(players.Count(p => p.Club == "Santos") >= 3);
    }

    // ---------- 4. Competition queries ----------

    [Fact]
    public void GivenMatchData_WhenRequesting2019Standings_ThenFlamengoAreChampions()
    {
        // "Who won the 2019 Brasileirão?"
        var standings = Service.GetStandings("Brasileirão", 2019);

        Assert.Equal(20, standings.Rows.Count);
        var champion = standings.Rows[0];
        Assert.Equal("Flamengo", champion.Team);
        Assert.Equal(90, champion.Points);
        Assert.Equal(28, champion.Wins);
        Assert.Equal("Santos", standings.Rows[1].Team);
        Assert.Equal("Palmeiras", standings.Rows[2].Team);
    }

    [Fact]
    public void GivenMatchData_WhenRequesting2019Relegation_ThenBottomFourMatchHistory()
    {
        // "Which teams were relegated in 2019?"
        var standings = Service.GetStandings("Brasileirão", 2019);
        var bottomFour = standings.Rows.TakeLast(4).Select(r => r.Team).ToList();

        Assert.Equal(["Cruzeiro", "CSA", "Chapecoense", "Avaí"], bottomFour);
    }

    [Fact]
    public void GivenMatchData_WhenRequesting2003Standings_ThenCruzeiroAreChampions()
    {
        // Historical coverage from novo_campeonato_brasileiro (2003-2019)
        var standings = Service.GetStandings("Brasileirão", 2003);

        Assert.Equal(24, standings.Rows.Count);
        Assert.Equal("Cruzeiro", standings.Rows[0].Team);
        Assert.Equal(100, standings.Rows[0].Points); // Cruzeiro's record 100-point season
    }

    [Fact]
    public void GivenMatchData_WhenRequesting2018LibertadoresKnockouts_ThenStagesArePresent()
    {
        // "Show the 2018 Copa Libertadores bracket"
        var knockout = Service.FindMatches(new SoccerDataService.MatchFilter
        { Competition = "Libertadores", Season = 2018, Round = "Final", Limit = 10 });

        Assert.NotEmpty(knockout);
        Assert.All(knockout, m => Assert.Equal(DataLoader.CopaLibertadores, m.Competition));
    }

    // ---------- 5. Statistical analysis ----------

    [Fact]
    public void GivenMatchData_WhenRequesting2021Averages_ThenGoalsPerMatchIsRealistic()
    {
        // "What's the average goals per match in the Brasileirão?"
        var stats = Service.GetMatchStatistics(competition: "Brasileirão", season: 2021);

        Assert.Equal(380, stats.PlayedMatches); // complete double round-robin: 20 teams
        Assert.InRange(stats.AvgGoalsPerMatch, 2.0, 3.0);
        Assert.InRange(stats.HomeWinRate, 35.0, 55.0);
    }

    [Fact]
    public void GivenMatchData_WhenComparing2018And2019_ThenBothSeasonsHaveFullSchedules()
    {
        // "Compare the 2018 and 2019 seasons"
        var s2018 = Service.GetMatchStatistics(competition: "Brasileirão", season: 2018);
        var s2019 = Service.GetMatchStatistics(competition: "Brasileirão", season: 2019);

        Assert.Equal(380, s2018.PlayedMatches);
        Assert.Equal(380, s2019.PlayedMatches);
        Assert.NotEqual(s2018.AvgGoalsPerMatch, s2019.AvgGoalsPerMatch);
    }

    [Fact]
    public void GivenMatchData_WhenRequestingBiggestWins_ThenMarginsAreDescending()
    {
        // "Show me the biggest wins in the dataset"
        var wins = Service.BiggestWins(limit: 10);

        Assert.Equal(10, wins.Count);
        for (var i = 1; i < wins.Count; i++)
            Assert.True(wins[i - 1].GoalMargin >= wins[i].GoalMargin);
        Assert.True(wins[0].GoalMargin >= 8); // e.g. Santos 8-0 Bolivar (2012 Libertadores)
    }

    [Fact]
    public void GivenMatchData_WhenRequestingDerbiesIn2023_ThenFindsRivalryMatches()
    {
        // "Show me all derbies in 2023"
        var derbies = Service.FindDerbies(season: 2023, limit: 100);

        Assert.NotEmpty(derbies);
        Assert.All(derbies, d => Assert.Equal(2023, d.Match.Season));
        Assert.Contains(derbies, d => d.DerbyName == "Fla-Flu");
    }

    // ---------- Data quality requirements ----------

    [Theory]
    [InlineData("Palmeiras-SP")]
    [InlineData("SE Palmeiras")]
    [InlineData("palmeiras")]
    [InlineData("PALMEIRAS")]
    public void GivenTeamNameVariations_WhenResolving_ThenAllMatchTheSameTeam(string spelling)
    {
        // "Implementation should normalize team names for consistent matching"
        Assert.Equal("Palmeiras", Service.ResolveTeam(spelling));
    }

    [Fact]
    public void GivenAccentedNames_WhenResolvingWithoutAccents_ThenStillMatches()
    {
        // "Implementation should handle UTF-8 encoding" (São Paulo, Grêmio, Avaí)
        Assert.Equal("São Paulo", Service.ResolveTeam("Sao Paulo"));
        Assert.Equal("Grêmio", Service.ResolveTeam("Gremio"));
        Assert.Equal("Avaí", Service.ResolveTeam("Avai"));
    }

    [Fact]
    public void GivenHistoricalData_WhenQueryingOldSeasons_ThenBrazilianDateFormatWasParsed()
    {
        // novo_campeonato_brasileiro uses DD/MM/YYYY dates
        var matches = Service.FindMatches(new SoccerDataService.MatchFilter
        { Team = "Vasco", Season = 2003, Limit = 5 });

        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            Assert.NotNull(m.Date);
            Assert.Equal(2003, m.Date!.Value.Year);
        });
    }

    // ---------- Cross-file queries ----------

    [Fact]
    public void GivenAllData_WhenCombiningPlayerAndMatchData_ThenBrazilianClubsAppearInBoth()
    {
        // Cross-file: FIFA clubs that also appear in match data must resolve consistently
        var gremioPlayers = Service.SearchPlayers(new SoccerDataService.PlayerFilter { Club = "Grêmio", Limit = 50 });
        var gremioMatches = Service.FindMatches(new SoccerDataService.MatchFilter { Team = "Grêmio", Limit = 5 });

        Assert.NotEmpty(gremioPlayers);
        Assert.NotEmpty(gremioMatches);
        Assert.All(gremioPlayers, p => Assert.Contains("Grêmio", p.Club));
        Assert.All(gremioMatches, m => Assert.True(
            m.HomeTeamCanonical == "Grêmio" || m.AwayTeamCanonical == "Grêmio"));
    }
}
