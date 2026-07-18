// =============================================================================
// BrazilianSoccerMcp.Tests - Competition & Statistics BDD Tests
// -----------------------------------------------------------------------------
// Feature: Competition Queries & Statistical Analysis
//   Verify standings are computed from match results (champion flagged, points
//   consistent), and that aggregate statistics (avg goals, biggest wins,
//   derbies) are calculated correctly.
// =============================================================================

using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

[Trait("Feature", "Competition Queries")]
public class CompetitionQueryTests : TestBase
{
    // Scenario: Standings for a season
    //   Given the match data is loaded
    //   When I request the 2019 Brasileirão standings
    //   Then the champion is Flamengo and points are internally consistent
    [Fact]
    public void Standings_2019Brasileirao_ChampionIsFlamengo()
    {
        var st = Repo.GetStandings("Brasileirão", 2019);
        Assert.NotNull(st);
        Assert.Equal("Brasileirão Série A", st!.Competition);
        Assert.True(st.Rows.Count >= 10);
        var champ = st.Rows.First();
        Assert.True(champ.Champion, "first row should be flagged champion");
        Assert.Equal("Flamengo", champ.Team);
        Assert.Equal(champ.Wins * 3 + champ.Draws, champ.Points);
        Assert.All(st.Rows, r => Assert.Equal(r.Played, r.Wins + r.Draws + r.Losses));
    }

    // Scenario: Relegated teams are the bottom four
    //   Given the match data is loaded
    //   When I request standings for a full season
    //   Then exactly the last four rows are flagged as relegated
    [Fact]
    public void Standings_BottomFourFlaggedAsRelegated()
    {
        var st = Repo.GetStandings("Brasileirão", 2019);
        Assert.NotNull(st);
        var rows = st!.Rows;
        if (rows.Count >= 20)
        {
            for (int i = 0; i < rows.Count - 4; i++)
                Assert.False(rows[i].Relegated, $"row {i} should not be relegated");
            for (int i = rows.Count - 4; i < rows.Count; i++)
                Assert.True(rows[i].Relegated, $"row {i} should be relegated");
        }
    }

    // Scenario: Standings ordering
    //   Given the match data is loaded
    //   When I request standings
    //   Then rows are sorted by points descending
    [Fact]
    public void Standings_SortedByPointsDescending()
    {
        var st = Repo.GetStandings("Brasileirão", 2019);
        Assert.NotNull(st);
        for (int i = 1; i < st!.Rows.Count; i++)
            Assert.True(st.Rows[i - 1].Points >= st.Rows[i].Points, "rows must be sorted by points desc");
    }
}

[Trait("Feature", "Statistical Analysis")]
public class StatisticsTests : TestBase
{
    // Scenario: Average goals per match
    //   Given the match data is loaded
    //   When I request average goals for the Brasileirão
    //   Then the average is a sane positive number (between 1 and 6)
    [Fact]
    public void AverageGoals_Brasileirao_IsSane()
    {
        var g = Repo.AverageGoals(competition: "Brasileirão");
        Assert.True(g.Matches > 0);
        Assert.InRange(g.AvgGoals, 1.0, 6.0);
        Assert.InRange(g.HomeWinPct + g.AwayWinPct + g.DrawPct, 99.0, 101.0);
    }

    // Scenario: Biggest wins are ordered by goal margin
    //   Given the match data is loaded
    //   When I request the biggest wins
    //   Then the first result has the largest goal difference
    [Fact]
    public void BiggestWins_OrderedByGoalMargin()
    {
        var ms = Repo.BiggestWins(limit: 5).ToList();
        Assert.NotEmpty(ms);
        for (int i = 1; i < ms.Count; i++)
            Assert.True(ms[i - 1].GoalDifference >= ms[i].GoalDifference, "must be sorted by margin desc");
        Assert.True(ms[0].GoalDifference >= 4, "biggest win margin should be >= 4");
    }

    // Scenario: Derbies in a season
    //   Given the match data is loaded
    //   When I request derbies for 2019
    //   Then at least one classic derby is returned (Fla-Flu or Majestoso)
    [Fact]
    public void Derbies_2019_ReturnsKnownDerby()
    {
        var derbies = Repo.Derbies(2019).ToList();
        Assert.NotEmpty(derbies);
        var names = derbies.Select(d => d.Name).ToList();
        Assert.True(names.Contains("Fla-Flu") || names.Contains("Clássico Majestoso"),
            $"expected a known derby, got: {string.Join(", ", names)}");
    }

    // Scenario: Home advantage exists
    //   Given the match data is loaded
    //   When I compute average goals for the Brasileirão
    //   Then the home win rate exceeds the away win rate
    [Fact]
    public void AverageGoals_HomeWinRateExceedsAwayWinRate()
    {
        var g = Repo.AverageGoals(competition: "Brasileirão");
        Assert.True(g.HomeWinPct > g.AwayWinPct,
            $"home win rate ({g.HomeWinPct:F1}%) should exceed away ({g.AwayWinPct:F1}%)");
    }
}
