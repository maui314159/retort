// =============================================================================
// Context: Brazilian Soccer MCP Server — BDD (Given/When/Then) tests.
//
// Exercises the QueryEngine over the real datasets via a shared fixture so the
// CSVs are loaded once for the whole test class. Tests follow the spec's
// Gherkin-style scenarios (match search, team stats, head-to-head, player
// search, standings, aggregate stats) and assert behavioral invariants rather
// than brittle exact counts where the data could legitimately vary. They cover
// the messy-data edge cases the loader must survive: name normalization across
// state suffixes, "NA" goals excluded from aggregation, multi-format dates.
// =============================================================================
using BrazilianSoccer.Core;
using Xunit;

namespace BrazilianSoccer.Tests;

/// <summary>Loads all six CSVs once and shares the engine across the test class.</summary>
public sealed class SoccerDataFixture
{
    public QueryEngine Engine { get; }
    public SoccerData Data { get; }

    public SoccerDataFixture()
    {
        var root = SoccerData.FindDataRoot(AppContext.BaseDirectory);
        Data = SoccerData.Load(root);
        Engine = new QueryEngine(Data);
    }
}

public sealed class QueryEngineTests : IClassFixture<SoccerDataFixture>
{
    private readonly QueryEngine _engine;
    private readonly SoccerData _data;

    public QueryEngineTests(SoccerDataFixture fx)
    {
        _engine = fx.Engine;
        _data = fx.Data;
    }

    // ---- Feature: Data loading -------------------------------------------

    [Fact]
    public void Given_all_csvs_When_loaded_Then_matches_and_players_are_populated()
    {
        // Given the six datasets, When loaded and deduplicated, Then both stores are
        // substantial. The ~24k raw match rows collapse to ~16.7k after overlapping
        // (competition, season) buckets are reduced to a single source.
        Assert.True(_data.Matches.Count > 15_000, $"expected >15k matches, got {_data.Matches.Count}");
        Assert.True(_data.Players.Count > 18_000, $"expected >18k players, got {_data.Players.Count}");
    }

    [Fact]
    public void Given_all_csvs_When_loaded_Then_every_competition_is_represented()
    {
        // Given loaded data, When grouping by competition, Then each main competition has matches.
        var byComp = _data.Matches.GroupBy(m => m.Competition).ToDictionary(g => g.Key, g => g.Count());
        Assert.True(byComp.GetValueOrDefault(Competition.BrasileiraoSerieA) > 0);
        Assert.True(byComp.GetValueOrDefault(Competition.CopaDoBrasil) > 0);
        Assert.True(byComp.GetValueOrDefault(Competition.Libertadores) > 0);
    }

    // ---- Feature: Match Queries ------------------------------------------

    [Fact]
    public void Given_match_data_When_searching_two_teams_Then_only_their_fixtures_return()
    {
        // Given match data, When I search matches between Flamengo and Fluminense,
        // Then every result involves both teams and carries date + competition.
        var matches = _engine.FindMatches(team: "Flamengo", opponent: "Fluminense");
        Assert.NotEmpty(matches);
        foreach (var m in matches)
        {
            bool flaHome = TeamName.Matches(m.HomeTeamKey, TeamName.Key("Flamengo"));
            bool fluHome = TeamName.Matches(m.HomeTeamKey, TeamName.Key("Fluminense"));
            bool flaAway = TeamName.Matches(m.AwayTeamKey, TeamName.Key("Flamengo"));
            bool fluAway = TeamName.Matches(m.AwayTeamKey, TeamName.Key("Fluminense"));
            Assert.True((flaHome && fluAway) || (fluHome && flaAway));
        }
    }

    [Fact]
    public void Given_match_data_When_filtering_by_season_Then_all_results_are_that_season()
    {
        // Given matches, When I ask for Palmeiras matches in 2019, Then all are 2019.
        var matches = _engine.FindMatches(team: "Palmeiras", season: 2019);
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(2019, m.Season));
    }

    [Fact]
    public void Given_match_data_When_results_returned_Then_ordered_by_date_descending()
    {
        // Given matches, When returned, Then newest-first ordering holds.
        var matches = _engine.FindMatches(team: "Corinthians", limit: 50);
        var dates = matches.Where(m => m.Date.HasValue).Select(m => m.Date!.Value).ToList();
        for (int i = 1; i < dates.Count; i++)
            Assert.True(dates[i] <= dates[i - 1], "matches not sorted by date descending");
    }

    [Fact]
    public void Given_a_competition_filter_When_searching_Then_only_that_competition_returns()
    {
        // Given the competition filter, When I search Libertadores matches, Then all are Libertadores.
        var matches = _engine.FindMatches(competition: CompetitionFilter.Libertadores, limit: 100);
        Assert.NotEmpty(matches);
        Assert.All(matches, m => Assert.Equal(Competition.Libertadores, m.Competition));
    }

    // ---- Feature: Team name normalization --------------------------------

    [Fact]
    public void Given_state_suffixed_names_When_normalized_Then_variants_collapse()
    {
        // Given naming variants, When keyed, Then suffixes/accents/case are removed.
        Assert.Equal("palmeiras", TeamName.Key("Palmeiras-SP"));
        Assert.Equal("palmeiras", TeamName.Key("Palmeiras"));
        Assert.Equal("sao paulo", TeamName.Key("São Paulo-SP"));
        Assert.Equal("gremio", TeamName.Key("Grêmio - RS"));
        Assert.Equal("nacional", TeamName.Key("Nacional (URU)"));
    }

    [Fact]
    public void Given_state_suffixed_name_When_searching_unsuffixed_Then_matches_found()
    {
        // Given "Palmeiras-SP" rows, When I search "Palmeiras", Then I get matches.
        var matches = _engine.FindMatches(team: "Palmeiras", competition: CompetitionFilter.BrasileiraoSerieA);
        Assert.NotEmpty(matches);
    }

    // ---- Feature: Team Queries -------------------------------------------

    [Fact]
    public void Given_match_data_When_requesting_team_record_Then_totals_are_consistent()
    {
        // Given matches, When I request Flamengo's record, Then W+D+L equals matches and goals are non-negative.
        var rec = _engine.TeamRecordFor("Flamengo");
        Assert.True(rec.Matches > 0);
        Assert.Equal(rec.Matches, rec.Wins + rec.Draws + rec.Losses);
        Assert.True(rec.GoalsFor >= 0 && rec.GoalsAgainst >= 0);
        Assert.InRange(rec.WinRate, 0d, 1d);
    }

    [Fact]
    public void Given_venue_filter_When_summing_home_and_away_Then_equals_combined()
    {
        // Given a season, When I split a team's record by venue, Then home + away == both.
        var both = _engine.TeamRecordFor("Corinthians", season: 2019, competition: CompetitionFilter.BrasileiraoSerieA, venue: HomeAway.Both);
        var home = _engine.TeamRecordFor("Corinthians", season: 2019, competition: CompetitionFilter.BrasileiraoSerieA, venue: HomeAway.Home);
        var away = _engine.TeamRecordFor("Corinthians", season: 2019, competition: CompetitionFilter.BrasileiraoSerieA, venue: HomeAway.Away);
        Assert.Equal(both.Matches, home.Matches + away.Matches);
        Assert.Equal(both.Wins, home.Wins + away.Wins);
        Assert.Equal(both.GoalsFor, home.GoalsFor + away.GoalsFor);
    }

    // ---- Feature: Head-to-head -------------------------------------------

    [Fact]
    public void Given_two_teams_When_head_to_head_Then_wins_and_draws_sum_to_matches()
    {
        // Given two rivals, When I compute head-to-head, Then the tallies are internally consistent.
        var h = _engine.HeadToHeadFor("Flamengo", "Fluminense");
        Assert.True(h.Matches > 0);
        Assert.Equal(h.Matches, h.TeamAWins + h.TeamBWins + h.Draws);
    }

    [Fact]
    public void Given_head_to_head_When_teams_swapped_Then_results_mirror()
    {
        // Given a swap of arguments, When recomputed, Then A/B wins swap and matches/draws stay.
        var ab = _engine.HeadToHeadFor("Palmeiras", "Santos");
        var ba = _engine.HeadToHeadFor("Santos", "Palmeiras");
        Assert.Equal(ab.Matches, ba.Matches);
        Assert.Equal(ab.Draws, ba.Draws);
        Assert.Equal(ab.TeamAWins, ba.TeamBWins);
        Assert.Equal(ab.TeamBWins, ba.TeamAWins);
    }

    // ---- Feature: Player Queries -----------------------------------------

    [Fact]
    public void Given_player_data_When_searching_by_name_Then_match_returns()
    {
        // Given FIFA data, When I search "Messi", Then a player is found.
        var players = _engine.FindPlayers(name: "Messi");
        Assert.NotEmpty(players);
        Assert.Contains(players, p => p.Name.Contains("Messi", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void Given_player_data_When_filtering_brazilians_Then_all_are_brazilian_and_sorted()
    {
        // Given FIFA data, When I filter Brazil, Then all are Brazilian and sorted by Overall desc.
        var players = _engine.FindPlayers(nationality: "Brazil", limit: 50);
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Equal("Brazil", p.Nationality));
        for (int i = 1; i < players.Count; i++)
            Assert.True((players[i].Overall ?? 0) <= (players[i - 1].Overall ?? 0));
    }

    [Fact]
    public void Given_player_data_When_filtering_by_position_Then_only_that_position_returns()
    {
        // Given FIFA data, When I filter GK Brazilians, Then every result is a GK.
        var players = _engine.FindPlayers(nationality: "Brazil", position: "GK", limit: 20);
        Assert.NotEmpty(players);
        Assert.All(players, p => Assert.Equal("GK", p.Position));
    }

    // ---- Feature: Competition Queries ------------------------------------

    [Fact]
    public void Given_a_season_When_computing_standings_Then_table_is_well_formed()
    {
        // Given 2019 Serie A matches, When I compute standings,
        // Then positions are 1..N, points match 3W+D, and the leader is reasonable.
        var rows = _engine.Standings(2019, CompetitionFilter.BrasileiraoSerieA);
        Assert.NotEmpty(rows);
        for (int i = 0; i < rows.Count; i++)
        {
            Assert.Equal(i + 1, rows[i].Position);
            var r = rows[i].Record;
            Assert.Equal(r.Wins * 3 + r.Draws, r.Points);
            Assert.Equal(r.Matches, r.Wins + r.Draws + r.Losses);
        }
        // Sorted by points descending.
        for (int i = 1; i < rows.Count; i++)
            Assert.True(rows[i].Record.Points <= rows[i - 1].Record.Points);
    }

    [Fact]
    public void Given_2019_serie_a_When_computing_standings_Then_flamengo_is_champion()
    {
        // Given the known 2019 season, When I compute the table, Then Flamengo tops it (historical fact).
        var rows = _engine.Standings(2019, CompetitionFilter.BrasileiraoSerieA);
        Assert.NotEmpty(rows);
        Assert.Contains("Flamengo", rows[0].Record.Team, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Given_overlapping_sources_When_deduplicated_Then_2019_serie_a_has_exactly_20_teams_and_380_matches()
    {
        // Given 2019 Série A appears in three source files, When deduplicated,
        // Then the table has the real 20 teams and the season's 380 matches (no inflation).
        var rows = _engine.Standings(2019, CompetitionFilter.BrasileiraoSerieA);
        Assert.Equal(20, rows.Count);
        var totalTeamMatches = rows.Sum(r => r.Record.Matches);
        Assert.Equal(380 * 2, totalTeamMatches); // each match counted once per side
        Assert.All(rows, r => Assert.Equal(38, r.Record.Matches));
    }

    [Fact]
    public void Given_2019_serie_a_When_computing_standings_Then_flamengo_record_matches_history()
    {
        // Given the known 2019 champion, When standings computed, Then Flamengo's
        // exact record (90 pts, 28W-6D-4L) from the spec example is reproduced.
        var rows = _engine.Standings(2019, CompetitionFilter.BrasileiraoSerieA);
        var flamengo = rows[0].Record;
        Assert.Contains("Flamengo", flamengo.Team, StringComparison.OrdinalIgnoreCase);
        Assert.Equal(90, flamengo.Points);
        Assert.Equal(28, flamengo.Wins);
        Assert.Equal(6, flamengo.Draws);
        Assert.Equal(4, flamengo.Losses);
    }

    [Fact]
    public void Given_two_distinct_atletico_clubs_When_aggregated_Then_they_are_not_merged()
    {
        // Given Atlético-MG and Athletico-PR share a loose name key, When standings
        // group by identity key, Then both appear as separate rows in 2019 Série A.
        var rows = _engine.Standings(2019, CompetitionFilter.BrasileiraoSerieA);
        var atleticos = rows
            .Where(r => TeamName.Key(r.Record.Team) == "atletico")
            .ToList();
        Assert.Equal(2, atleticos.Count);
        // No team plays more than 38 matches; a merge would show ~76.
        Assert.All(rows, r => Assert.True(r.Record.Matches <= 38));
    }

    // ---- Feature: Statistical Analysis -----------------------------------

    [Fact]
    public void Given_matches_When_computing_stats_Then_rates_sum_and_average_is_plausible()
    {
        // Given Serie A matches, When I aggregate, Then win/draw rates sum to 1 and GPM is in a sane range.
        var s = _engine.Stats(competition: CompetitionFilter.BrasileiraoSerieA);
        Assert.True(s.Matches > 0);
        Assert.Equal(s.Matches, s.HomeWins + s.AwayWins + s.Draws);
        Assert.InRange(s.HomeWinRate + s.AwayWinRate + s.DrawRate, 0.999, 1.001);
        Assert.InRange(s.GoalsPerMatch, 1.5, 4.0);
    }

    [Fact]
    public void Given_matches_When_listing_biggest_wins_Then_sorted_by_margin()
    {
        // Given results, When I list biggest wins, Then margins are non-increasing and all have results.
        var wins = _engine.BiggestWins(limit: 10);
        Assert.NotEmpty(wins);
        Assert.All(wins, m => Assert.True(m.HasResult));
        for (int i = 1; i < wins.Count; i++)
        {
            int prev = Math.Abs(wins[i - 1].HomeGoal!.Value - wins[i - 1].AwayGoal!.Value);
            int cur = Math.Abs(wins[i].HomeGoal!.Value - wins[i].AwayGoal!.Value);
            Assert.True(cur <= prev);
        }
    }

    [Fact]
    public void Given_NA_goals_in_source_When_aggregating_Then_those_rows_are_excluded()
    {
        // Given Brasileirao rows with "NA" goals, When aggregating, Then result-less matches are skipped.
        // Invariant: stats match count never exceeds the count of matches with results.
        var withResults = _data.Matches.Count(m => m.Competition == Competition.BrasileiraoSerieA && m.HasResult);
        var s = _engine.Stats(competition: CompetitionFilter.BrasileiraoSerieA);
        Assert.Equal(withResults, s.Matches);
        Assert.True(_data.Matches.Any(m => !m.HasResult), "expected at least one result-less (NA) match in data");
    }

    // ---- Feature: Multi-format date parsing ------------------------------

    [Fact]
    public void Given_brazilian_format_dates_When_parsed_Then_dates_resolve()
    {
        // Given novo_campeonato rows (DD/MM/YYYY), When loaded, Then those matches have parsed dates.
        var novo = _data.Matches.Where(m => m.Source == "novo_campeonato_brasileiro.csv").ToList();
        Assert.NotEmpty(novo);
        Assert.True(novo.Count(m => m.Date.HasValue) > novo.Count / 2,
            "majority of Brazilian-format dates should parse");
    }

    [Theory]
    [InlineData("2023-09-24", 2023, 9, 24)]
    [InlineData("29/03/2003", 2003, 3, 29)]
    [InlineData("2012-05-19 18:30:00", 2012, 5, 19)]
    public void Given_various_date_formats_When_parsed_Then_correct_components(string raw, int y, int mo, int d)
    {
        var date = Parsing.Date(raw);
        Assert.NotNull(date);
        Assert.Equal(new DateOnly(y, mo, d), date!.Value);
    }
}
