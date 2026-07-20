using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Unit tests for the query engine over a small synthetic dataset,
/// written as Given/When/Then scenarios.
/// </summary>
public class SoccerDataServiceTests
{
    private static MatchRecord Match(
        string date, string home, string away, int? hg, int? ag,
        string competition = DataLoader.BrasileiraoSerieA, int? season = null,
        string source = "synthetic", string? round = null) =>
        new()
        {
            Date = DateOnly.Parse(date),
            Season = season ?? DateOnly.Parse(date).Year,
            Competition = competition,
            Source = source,
            Round = round,
            HomeTeam = home,
            AwayTeam = away,
            HomeTeamCanonical = TeamNameNormalizer.CanonicalName(home),
            AwayTeamCanonical = TeamNameNormalizer.CanonicalName(away),
            HomeGoals = hg,
            AwayGoals = ag,
        };

    private static PlayerRecord Player(int id, string name, string nationality, string club, int overall, string position) =>
        new() { Id = id, Name = name, Nationality = nationality, Club = club, Overall = overall, Position = position };

    private static SoccerDataService BuildService() =>
        new(
            matches:
            [
                Match("2021-05-30", "Palmeiras-SP", "Flamengo-RJ", 2, 1, season: 2021, round: "Round 1"),
                Match("2021-09-12", "Flamengo-RJ", "Palmeiras-SP", 3, 0, season: 2021, round: "Round 19"),
                Match("2021-11-27", "Palmeiras-SP", "Flamengo-RJ", 1, 1, DataLoader.CopaLibertadores, 2021, round: "Final"),
                Match("2021-06-06", "Corinthians-SP", "Palmeiras-SP", 0, 0, season: 2021, round: "Round 2"),
                Match("2020-08-09", "Palmeiras-SP", "Corinthians-SP", 2, 0, season: 2020, round: "Round 2"),
                Match("2022-04-10", "Flamengo-RJ", "Corinthians-SP", 4, 2, season: 2022, round: "Round 1"),
                Match("2022-10-01", "Santos-SP", "Flamengo-RJ", null, null, season: 2022, round: "Round 33"), // unplayed
                Match("2013-03-13", "Santos-SP", "Barcelona-EQU", 2, 0, DataLoader.CopaLibertadores, 2013, round: "Group Stage"),
            ],
            players:
            [
                Player(1, "Neymar Jr", "Brazil", "Paris Saint-Germain", 92, "LW"),
                Player(2, "Alisson", "Brazil", "Liverpool", 89, "GK"),
                Player(3, "L. Messi", "Argentina", "FC Barcelona", 94, "RF"),
                Player(4, "Everton Ribeiro", "Brazil", "CR Flamengo", 80, "RM"),
                Player(5, "Gabriel Veron", "Brazil", "SE Palmeiras", 74, "RW"),
            ]);

    // ---------- Match queries ----------

    [Fact]
    public void FindMatches_ByTeam_ReturnsHomeAndAwayFixtures()
    {
        // Given the loaded synthetic data
        var service = BuildService();

        // When searching matches involving Palmeiras
        var matches = service.FindMatches(new SoccerDataService.MatchFilter { Team = "palmeiras" });

        // Then both home and away fixtures are returned, newest first
        Assert.Equal(5, matches.Count);
        Assert.All(matches, m => Assert.True(
            m.HomeTeamCanonical == "Palmeiras" || m.AwayTeamCanonical == "Palmeiras"));
        Assert.True(matches[0].Date >= matches[^1].Date);
    }

    [Fact]
    public void FindMatches_ByTeamAndOpponent_ReturnsOnlyTheirMeetings()
    {
        // Given the loaded data
        var service = BuildService();

        // When searching Palmeiras vs Flamengo
        var matches = service.FindMatches(new SoccerDataService.MatchFilter
        { Team = "Palmeiras", Opponent = "Flamengo" });

        // Then only their three meetings are returned
        Assert.Equal(3, matches.Count);
    }

    [Fact]
    public void FindMatches_ByCompetitionAndSeason_FiltersCorrectly()
    {
        // Given the loaded data
        var service = BuildService();

        // When filtering Libertadores 2021
        var matches = service.FindMatches(new SoccerDataService.MatchFilter
        { Competition = "libertadores", Season = 2021 });

        // Then only the Libertadores final remains
        Assert.Single(matches);
        Assert.Equal(DataLoader.CopaLibertadores, matches[0].Competition);
    }

    [Fact]
    public void FindMatches_ByDateRange_FiltersCorrectly()
    {
        // Given the loaded data
        var service = BuildService();

        // When filtering a date window
        var matches = service.FindMatches(new SoccerDataService.MatchFilter
        { From = new DateOnly(2021, 9, 1), To = new DateOnly(2021, 12, 31) });

        // Then only matches inside the window are returned
        Assert.Equal(2, matches.Count);
        Assert.All(matches, m => Assert.InRange(m.Date!.Value, new DateOnly(2021, 9, 1), new DateOnly(2021, 12, 31)));
    }

    [Fact]
    public void FindMatches_ByRound_FinalDoesNotMatchSemifinals()
    {
        // Given the loaded data
        var service = BuildService();

        // When filtering round = "Final"
        var matches = service.FindMatches(new SoccerDataService.MatchFilter { Round = "Final" });

        // Then only the actual final is returned (not "Semifinals")
        Assert.Single(matches);
        Assert.Equal("Final", matches[0].Round);
    }

    // ---------- Team queries ----------

    [Fact]
    public void GetTeamStatistics_ComputesWinDrawLossAndGoals()
    {
        // Given the loaded data
        var service = BuildService();

        // When requesting Palmeiras' 2021 record
        var stats = service.GetTeamStatistics("Palmeiras", season: 2021);

        // Then W/D/L and goals are correct (played matches only)
        Assert.Equal(4, stats.Matches);
        Assert.Equal(1, stats.Wins);
        Assert.Equal(2, stats.Draws);
        Assert.Equal(1, stats.Losses);
        Assert.Equal(3, stats.GoalsFor);
        Assert.Equal(5, stats.GoalsAgainst);
    }

    [Fact]
    public void GetTeamStatistics_HomeVenue_OnlyCountsHomeMatches()
    {
        // Given the loaded data
        var service = BuildService();

        // When requesting Palmeiras' 2021 home record
        var stats = service.GetTeamStatistics("Palmeiras", season: 2021, venue: SoccerDataService.Venue.Home);

        // Then away matches are excluded (2-1 W vs Flamengo, 1-1 D Libertadores final)
        Assert.Equal(2, stats.Matches);
        Assert.Equal(1, stats.Wins);
        Assert.Equal(1, stats.Draws);
        Assert.Equal(0, stats.Losses);
    }

    [Fact]
    public void HeadToHead_SummarizesAllTimeRecord()
    {
        // Given the loaded data
        var service = BuildService();

        // When comparing Palmeiras and Flamengo
        var h2h = service.HeadToHead("SE Palmeiras", "Flamengo-RJ");

        // Then the summary reflects every played meeting
        Assert.Equal(3, h2h.Matches.Count);
        Assert.Equal(1, h2h.Team1Wins);
        Assert.Equal(1, h2h.Team2Wins);
        Assert.Equal(1, h2h.Draws);
        Assert.Equal("Palmeiras", h2h.Team1);
    }

    [Fact]
    public void TeamCompetitions_ListsDistinctCompetitions()
    {
        // Given the loaded data
        var service = BuildService();

        // When listing Santos' competitions
        var competitions = service.TeamCompetitions("Santos");

        // Then both competitions are listed
        Assert.Equal([DataLoader.BrasileiraoSerieA, DataLoader.CopaLibertadores], competitions);
    }

    // ---------- Standings ----------

    [Fact]
    public void GetStandings_ComputesPointsAndOrdering()
    {
        // Given the loaded data
        var service = BuildService();

        // When computing the 2021 Brasileirão table (synthetic source wins the single-source rule? no:
        // source 'synthetic' is used because the preferred files have no data here)
        var standings = service.GetStandings("Brasileirão", 2021);

        // Then Palmeiras (4 pts) leads Flamengo (3 pts) and Corinthians (1 pt)
        Assert.Equal(3, standings.Rows.Count);
        Assert.Equal("Palmeiras", standings.Rows[0].Team);
        Assert.Equal(4, standings.Rows[0].Points);
        Assert.Equal("Flamengo", standings.Rows[1].Team);
        Assert.Equal(3, standings.Rows[1].Points);
        Assert.Equal("Corinthians", standings.Rows[2].Team);
        Assert.Equal(1, standings.Rows[2].Points);
    }

    // ---------- Player queries ----------

    [Fact]
    public void SearchPlayers_ByName_IsCaseInsensitiveSubstring()
    {
        // Given the loaded data
        var service = BuildService();

        // When searching "neymar"
        var players = service.SearchPlayers(new SoccerDataService.PlayerFilter { Name = "neymar" });

        // Then Neymar Jr is found
        Assert.Single(players);
        Assert.Equal("Neymar Jr", players[0].Name);
    }

    [Fact]
    public void SearchPlayers_ByNationalityAndClub_FiltersAndSortsByRating()
    {
        // Given the loaded data
        var service = BuildService();

        // When filtering Brazilian players at clubs containing "Flamengo"
        var players = service.SearchPlayers(new SoccerDataService.PlayerFilter
        { Nationality = "Brazil", Club = "flamengo" });

        // Then only Everton Ribeiro matches
        Assert.Single(players);
        Assert.Equal("Everton Ribeiro", players[0].Name);
    }

    [Fact]
    public void TopPlayers_BrazilianSortedByOverall()
    {
        // Given the loaded data
        var service = BuildService();

        // When asking for the top 3 Brazilians
        var top = service.TopPlayers(nationality: "Brazil", limit: 3);

        // Then they come back in descending rating order
        Assert.Equal(["Neymar Jr", "Alisson", "Everton Ribeiro"], top.Select(p => p.Name).ToArray());
    }

    // ---------- Statistics ----------

    [Fact]
    public void GetMatchStatistics_ComputesAveragesAndWinRates()
    {
        // Given the loaded data
        var service = BuildService();

        // When aggregating all 2021 matches
        var stats = service.GetMatchStatistics(season: 2021);

        // Then averages and rates use played matches only
        Assert.Equal(4, stats.TotalMatches);
        Assert.Equal(4, stats.PlayedMatches);
        Assert.Equal(8.0 / 4, stats.AvgGoalsPerMatch);
        Assert.Equal(50.0, stats.HomeWinRate);
        Assert.Equal(0.0, stats.AwayWinRate);
        Assert.Equal(50.0, stats.DrawRate);
        Assert.Equal("2021-09-12: Flamengo 3-0 Palmeiras (Brasileirão Série A, Round 19)",
            stats.BiggestWins[0].Describe());
    }

    [Fact]
    public void GetMatchStatistics_UnplayedFixtures_AreExcludedFromRates()
    {
        // Given the loaded data
        var service = BuildService();

        // When aggregating 2022 (contains one unplayed fixture)
        var stats = service.GetMatchStatistics(season: 2022);

        // Then the unplayed match counts in totals but not in averages
        Assert.Equal(2, stats.TotalMatches);
        Assert.Equal(1, stats.PlayedMatches);
        Assert.Equal(6.0, stats.AvgGoalsPerMatch);
    }

    // ---------- Resolution errors ----------

    [Fact]
    public void ResolveTeam_UnknownTeam_Throws() =>
        Assert.Throws<TeamResolutionException>(() => BuildService().ResolveTeam("Borussia Dortmund"));

    [Fact]
    public void ResolveTeam_AmbiguousTeam_ThrowsWithCandidates()
    {
        // Given two teams that both contain the query
        var service = new SoccerDataService(
            [
                Match("2021-01-01", "Ponte Preta-SP", "Santos-SP", 1, 0),
                Match("2021-01-02", "Portuguesa-SP", "Santos-SP", 0, 1),
            ], []);

        // When resolving an ambiguous substring, then the error lists candidates
        var ex = Assert.Throws<TeamResolutionException>(() => service.ResolveTeam("po"));
        Assert.Contains("ambiguous", ex.Message);
    }
}
