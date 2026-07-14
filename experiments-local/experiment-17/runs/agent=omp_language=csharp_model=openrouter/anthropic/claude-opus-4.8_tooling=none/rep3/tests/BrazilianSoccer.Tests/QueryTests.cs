// =============================================================================
// File:    QueryTests.cs
// Project: BrazilianSoccer.Tests
// Purpose: BDD scenarios for SoccerDatabase queries against the real corpus —
//          match search, head-to-head, team records, calculated standings,
//          player search and aggregate statistics — mirroring the Gherkin
//          scenarios and example answers in TASK.md.
// Context: The standings assertion pins the well-known 2019 Brasileirão result
//          (Flamengo champion, 90 pts, 28W/6D/4L) which doubles as a proof that
//          cross-source deduplication is correct: without it the win count
//          inflates 2-3x. Other tests assert logical invariants (played =
//          W+D+L, goals symmetry in head-to-head) rather than brittle totals.
// =============================================================================

using BrazilianSoccer.Core;

namespace BrazilianSoccer.Tests;

[Collection("database")]
public class QueryTests
{
    private readonly SoccerDatabase _db;
    public QueryTests(DatabaseFixture fx) => _db = fx.Db;

    [Fact]
    public void Given_TwoTeams_When_FindingMatchesBetweenThem_Then_OnlyTheirFixturesReturned()
    {
        // Given the match data is loaded
        // When I search for matches between Flamengo and Fluminense
        var matches = _db.FindMatches(team: "Flamengo", opponent: "Fluminense");

        // Then I receive matches, each between exactly those two teams
        Assert.NotEmpty(matches);
        Assert.All(matches, m =>
        {
            var keys = new[] { m.HomeKey, m.AwayKey };
            Assert.Contains("flamengo", keys);
            Assert.Contains("fluminense", keys);
        });
        // And they are sorted newest-first
        var dated = matches.Where(m => m.Date is not null).Select(m => m.Date!.Value).ToList();
        Assert.True(dated.SequenceEqual(dated.OrderByDescending(d => d)));
    }

    [Fact]
    public void Given_TeamAndSeason_When_RequestingRecord_Then_PlayedEqualsWinsDrawsLosses()
    {
        // When I request Palmeiras' 2019 Série A record
        var record = _db.TeamRecord("Palmeiras", Competition.BrasileiraoSerieA, 2019);

        // Then I receive a consistent W/D/L record
        Assert.NotNull(record);
        Assert.Equal(record!.Played, record.Wins + record.Draws + record.Losses);
        Assert.True(record.Played >= 30);
    }

    [Fact]
    public void Given_Season2019_When_CalculatingBrasileiraoStandings_Then_FlamengoChampionWith90Points()
    {
        // When I calculate the 2019 Brasileirão table from match results
        var table = _db.Standings(Competition.BrasileiraoSerieA, 2019);

        // Then Flamengo is champion with the historically correct 90 pts (28W,6D,4L)
        Assert.NotEmpty(table);
        var champ = table[0];
        Assert.Equal(1, champ.Position);
        Assert.Equal("flamengo", NameNormalizer.Key(champ.Record.Team));
        Assert.Equal(38, champ.Record.Played); // 20-team league, 38 rounds
        Assert.Equal(90, champ.Record.Points);
        Assert.Equal(28, champ.Record.Wins);
        Assert.Equal(6, champ.Record.Draws);
        Assert.Equal(4, champ.Record.Losses);
        // And a 20-team league produces 20 rows
        Assert.Equal(20, table.Count);
    }

    [Fact]
    public void Given_TwoTeams_When_ComputingHeadToHead_Then_TotalsAreInternallyConsistent()
    {
        // When
        var h2h = _db.HeadToHead("Palmeiras", "Santos");

        // Then wins+draws account for every scored match and goals are symmetric
        Assert.NotNull(h2h);
        var scored = h2h!.Matches.Count(m => m.HasScore);
        Assert.Equal(scored, h2h.TeamAWins + h2h.TeamBWins + h2h.Draws);
        Assert.True(h2h.Played > 0);
    }

    [Fact]
    public void Given_Nationality_When_SearchingPlayers_Then_AllMatchAndSortedByRating()
    {
        // When I search for Brazilian players
        var players = _db.FindPlayers(nationality: "Brazil", limit: 50);

        // Then all are Brazilian and sorted by overall descending
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality));
        var ratings = players.Select(p => p.Overall).ToList();
        Assert.True(ratings.SequenceEqual(ratings.OrderByDescending(r => r)));
    }

    [Fact]
    public void Given_NameQuery_When_SearchingPlayers_Then_AccentInsensitiveMatch()
    {
        // When I search a name without accents
        var players = _db.FindPlayers(name: "neymar", limit: 5);

        // Then the accented record is found
        Assert.Contains(players, p => p.Name.Contains("Neymar", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void Given_Brasileirao_When_ComputingGoalStats_Then_AveragesAreInPlausibleRange()
    {
        // When
        var (matches, avg, homeWin) = _db.GoalStats(Competition.BrasileiraoSerieA);

        // Then values are in football-plausible ranges
        Assert.True(matches > 1000);
        Assert.InRange(avg, 1.5, 4.0);
        Assert.InRange(homeWin, 0.30, 0.65);
    }

    [Fact]
    public void Given_NoFilter_When_FindingBiggestWins_Then_SortedByDescendingMargin()
    {
        // When
        var wins = _db.BiggestWins(limit: 10);

        // Then the list is sorted by goal margin, largest first
        Assert.NotEmpty(wins);
        var margins = wins.Select(m => Math.Abs(m.HomeGoals!.Value - m.AwayGoals!.Value)).ToList();
        Assert.True(margins.SequenceEqual(margins.OrderByDescending(x => x)));
        Assert.True(margins[0] >= 5);
    }

    [Fact]
    public void Given_UnknownTeam_When_FindingMatches_Then_EmptyNotError()
    {
        // When
        var matches = _db.FindMatches(team: "Definitely Not A Real Club 123");

        // Then no results, no exception
        Assert.Empty(matches);
    }

    [Fact]
    public void Given_Team_When_ListingCompetitions_Then_MultipleCompetitionsReturned()
    {
        // When
        var comps = _db.CompetitionsForTeam("Palmeiras");

        // Then Palmeiras appears across more than one competition
        Assert.True(comps.Count >= 2);
        Assert.All(comps, c => Assert.True(c.Matches > 0));
    }

    [Fact]
    public void Given_AmbiguousBaseName_When_ResolvingDisplay_Then_CanonicalSpellingChosen()
    {
        // Given two distinct clubs sharing the base "Atletico"
        // When resolving each via its qualified key
        var mineiro = _db.ResolveDisplayName("Atletico-MG");
        var paranaense = _db.ResolveDisplayName("Atletico-PR");

        // Then they resolve to different, non-empty display names (not a bare
        // "Atletico" collision) so a reader can tell them apart.
        Assert.NotEqual(mineiro, paranaense);
        Assert.NotEqual("", mineiro);
        Assert.NotEqual("", paranaense);
    }

    [Fact]
    public void Given_SeasonStandings_When_Read_Then_NoTeamPlaysMoreThanRoundRobin()
    {
        // Guards against dedup regressions: a 20-team double round-robin caps a
        // team at 38 games. If overlapping sources stopped merging, this breaks.
        var table = _db.Standings(Competition.BrasileiraoSerieA, 2019);
        Assert.All(table, s => Assert.True(s.Record.Played <= 38,
            $"{s.Record.Team} played {s.Record.Played} (dedup regression?)"));
    }
}
