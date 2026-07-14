using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Tests DataRepository query logic using in-memory data (no CSV loading).
/// </summary>
public class DataRepositoryTests
{
    private static DataRepository BuildRepo() =>
        new DataRepository(SampleMatches(), SamplePlayers());

    private static List<MatchRecord> SampleMatches() =>
    [
        Make("2023-09-03", "Flamengo-RJ", "Fluminense-RJ", 2, 1, "Brasileirao", 2023, "22"),
        Make("2023-05-28", "Fluminense-RJ", "Flamengo-RJ",  1, 0, "Brasileirao", 2023, "8"),
        Make("2022-10-01", "Flamengo-RJ", "Corinthians-SP", 3, 1, "Brasileirao", 2022, "30"),
        Make("2022-08-15", "Palmeiras-SP", "Flamengo-RJ",   1, 2, "Brasileirao", 2022, "24"),
        Make("2019-11-17", "Flamengo-RJ", "Grêmio",         5, 0, "Brasileirao", 2019, "37"),
        Make("2023-06-01", "Flamengo-RJ", "Independiente",  2, 0, "Copa Libertadores", 2023, "group stage"),
    ];

    private static MatchRecord Make(
        string date, string home, string away,
        int hg, int ag, string comp, int season, string round) =>
        new()
        {
            Date        = DateTime.Parse(date),
            HomeTeam    = home,
            AwayTeam    = away,
            HomeGoals   = hg,
            AwayGoals   = ag,
            Competition = comp,
            Season             = season,
            Round              = round,
            HomeTeamKey        = TeamNameNormalizer.Normalize(home),
            AwayTeamKey        = TeamNameNormalizer.Normalize(away),
            HomeTeamSearchKey  = TeamNameNormalizer.NormalizeForSearch(home),
            AwayTeamSearchKey  = TeamNameNormalizer.NormalizeForSearch(away),
        };

    private static List<FifaPlayer> SamplePlayers() =>
    [
        new() { SofifaId=1, Name="Gabriel Barbosa", Age=26, Nationality="Brazil", Overall=84,
                Potential=84, Club="Flamengo", Position="ST",
                NameKey="gabriel barbosa", NationalityKey="brazil", ClubKey="flamengo" },
        new() { SofifaId=2, Name="Neymar Jr",       Age=27, Nationality="Brazil", Overall=92,
                Potential=92, Club="Paris Saint-Germain", Position="LW",
                NameKey="neymar jr", NationalityKey="brazil", ClubKey="paris saint-germain" },
        new() { SofifaId=3, Name="Alisson",         Age=26, Nationality="Brazil", Overall=89,
                Potential=90, Club="Liverpool", Position="GK",
                NameKey="alisson", NationalityKey="brazil", ClubKey="liverpool" },
        new() { SofifaId=4, Name="L. Messi",        Age=31, Nationality="Argentina", Overall=94,
                Potential=94, Club="FC Barcelona", Position="RF",
                NameKey="l. messi", NationalityKey="argentina", ClubKey="fc barcelona" },
    ];

    // ─── FindMatches ──────────────────────────────────────────────────────────

    [Fact]
    public void FindMatches_ByTeam_ReturnsAllSides()
    {
        var repo    = BuildRepo();
        var matches = repo.FindMatches(team: "Flamengo").ToList();
        Assert.Equal(6, matches.Count);  // Flamengo appears in all 6 sample rows
    }

    [Fact]
    public void FindMatches_BySeason_FiltersCorrectly()
    {
        var repo    = BuildRepo();
        var matches = repo.FindMatches(season: 2023).ToList();
        Assert.All(matches, m => Assert.Equal(2023, m.Season));
        Assert.Equal(3, matches.Count);
    }

    [Fact]
    public void FindMatches_ByCompetition_Libertadores()
    {
        var repo    = BuildRepo();
        var matches = repo.FindMatches(competition: "Libertadores").ToList();
        Assert.Single(matches);
        Assert.Equal("Copa Libertadores", matches[0].Competition);
    }

    [Fact]
    public void FindMatches_HeadToHead_FindsBothDirections()
    {
        var repo    = BuildRepo();
        var h2h     = repo.FindMatches("Flamengo", opponent: "Fluminense").ToList();
        Assert.Equal(2, h2h.Count);
    }

    // ─── GetTeamStats ─────────────────────────────────────────────────────────

    [Fact]
    public void GetTeamStats_Flamengo_CorrectRecord()
    {
        var repo  = BuildRepo();
        var stats = repo.GetTeamStats("Flamengo");

        Assert.Equal(6, stats.Matches);
        Assert.Equal(5, stats.Wins);   // W: 2023(2-1), 2022(3-1), 2022(1-2 as away→W), 2019(5-0), 2023-lib(2-0)
        // Let's recalculate: home=Flamengo → 2-1 win, away=Fluminense 1-0 win (Flamengo lost)
        // Flamengo home: 2023-09-03 (2-1 W), 2022-10-01 (3-1 W), 2019-11-17 (5-0 W), 2023-06-01 (2-0 W) = 4W
        // Flamengo away: 2023-05-28 (0-1 L at Fluminense), 2022-08-15 (2-1 W at Palmeiras) = 1W 1L
        // Total: 5W 0D 1L
        Assert.Equal(1, stats.Losses);
        Assert.Equal(0, stats.Draws);
    }

    [Fact]
    public void GetTeamStats_SeasonFilter()
    {
        var repo  = BuildRepo();
        var stats = repo.GetTeamStats("Flamengo", season: 2023);
        Assert.Equal(3, stats.Matches);
    }

    // ─── GetStandings ─────────────────────────────────────────────────────────

    [Fact]
    public void GetStandings_2023_Brasileirao_ContainsTeams()
    {
        var repo  = BuildRepo();
        var table = repo.GetStandings(2023, "Brasileirao");
        Assert.NotEmpty(table);
        // Flamengo won more points than Fluminense in our sample
        var flamengo  = table.First(r => r.Team.Contains("Flamengo"));
        var fluminense = table.First(r => r.Team.Contains("Fluminense"));
        Assert.True(flamengo.Rank < fluminense.Rank,
            $"Flamengo rank {flamengo.Rank} should be better than Fluminense rank {fluminense.Rank}");
    }

    [Fact]
    public void GetStandings_RanksStartAtOne()
    {
        var repo  = BuildRepo();
        var table = repo.GetStandings(2023, "Brasileirao");
        Assert.Equal(1, table[0].Rank);
    }

    // ─── FindPlayers ─────────────────────────────────────────────────────────

    [Fact]
    public void FindPlayers_ByNationality_Brazil()
    {
        var repo    = BuildRepo();
        var players = repo.FindPlayers(nationality: "Brazil").ToList();
        Assert.Equal(3, players.Count);
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality));
    }

    [Fact]
    public void FindPlayers_ByName_PartialMatch()
    {
        var repo    = BuildRepo();
        var players = repo.FindPlayers(name: "Gabriel").ToList();
        Assert.Single(players);
        Assert.Contains("Gabriel", players[0].Name);
    }

    [Fact]
    public void FindPlayers_OrderedByRating()
    {
        var repo    = BuildRepo();
        var players = repo.FindPlayers().ToList();
        for (int i = 1; i < players.Count; i++)
            Assert.True(players[i - 1].Overall >= players[i].Overall);
    }

    [Fact]
    public void FindPlayers_MinRating_FiltersLow()
    {
        var repo    = BuildRepo();
        var players = repo.FindPlayers(minRating: 90).ToList();
        Assert.All(players, p => Assert.True(p.Overall >= 90));
    }

    [Fact]
    public void FindPlayers_ByClub_Flamengo()
    {
        var repo    = BuildRepo();
        var players = repo.FindPlayers(club: "Flamengo").ToList();
        Assert.Single(players);
        Assert.Equal("Gabriel Barbosa", players[0].Name);
    }

    // ─── aggregated stats ─────────────────────────────────────────────────────

    [Fact]
    public void AverageGoalsPerMatch_IsPositive()
    {
        var repo = BuildRepo();
        var avg  = repo.AverageGoalsPerMatch();
        Assert.True(avg > 0);
    }

    [Fact]
    public void HomeWinRate_IsInRange()
    {
        var repo = BuildRepo();
        var rate = repo.HomeWinRate();
        Assert.InRange(rate, 0, 100);
    }

    [Fact]
    public void BiggestWins_ReturnedInDescendingDiff()
    {
        var repo = BuildRepo();
        var wins = repo.BiggestWins(limit: 10).ToList();
        for (int i = 1; i < wins.Count; i++)
            Assert.True(wins[i - 1].GoalDifference >= wins[i].GoalDifference);
    }
}
