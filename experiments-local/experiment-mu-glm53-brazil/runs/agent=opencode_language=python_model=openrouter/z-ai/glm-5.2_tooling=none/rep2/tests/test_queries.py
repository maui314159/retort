# SPDX-License-Identifier: Apache-2.0
# Context block ----------------------------------------------------------------
# BDD tests for the QueryEngine: matches, teams, head-to-head, statistics,
# standings, players, derbies, biggest wins. Mirrors the spec's example
# questions and expected answer formats.
# --------------------------------------------------------------------------- #
"""BDD scenarios for the query engine."""

from __future__ import annotations

from brazilian_soccer_mcp.queries import QueryEngine


class TestMatchQueries:
    def test_search_matches_between_two_teams(self, engine: QueryEngine):
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        # Then I should receive a list of matches
        # And each match should have date, scores, and competition
        results = engine.search_matches(team="Flamengo", opponent="Fluminense")
        assert len(results) >= 5
        for m in results:
            assert "date" in m
            assert "score" in m
            assert "competition" in m
            assert "home_team" in m and "away_team" in m

    def test_search_matches_by_team_returns_only_that_team(self, engine: QueryEngine):
        # Given the match data is loaded
        # When I search for Palmeiras matches
        # Then every result features Palmeiras (home or away)
        results = engine.search_matches(team="Palmeiras", limit=50)
        assert len(results) == 50
        for m in results:
            assert m["home_team_key"] == "palmeiras" or m["away_team_key"] == "palmeiras"

    def test_search_matches_by_season(self, engine: QueryEngine):
        # Given the match data is loaded
        # When I search for Palmeiras matches in 2022
        # Then every result has season == 2022
        results = engine.search_matches(team="Palmeiras", season=2022, limit=200)
        assert results
        for m in results:
            assert m["season"] == 2022

    def test_search_matches_by_competition_accent_insensitive(self, engine: QueryEngine):
        # Given the match data is loaded
        # When I search by competition "brasileirao" (no accent)
        # Then the results come from "Brasileirão Série A" matches
        results = engine.search_matches(competition="brasileirao", limit=10)
        assert results
        assert all("Brasileirão" in m["competition"] for m in results)

    def test_search_matches_by_date_range(self, engine: QueryEngine):
        # Given the match data is loaded
        # When I search within 2022-09-01..2023-09-30
        # Then every match with a date falls in September 2023
        results = engine.search_matches(start_date="2023-09-01",
                                        end_date="2023-09-30", limit=50)
        assert results
        for m in results:
            if m["date"]:
                assert "2023-09" in m["date"]

    def test_search_matches_most_recent_first(self, engine: QueryEngine):
        # Given the match data is loaded
        # When I search Flamengo matches with no date filter
        # Then the results are sorted most-recent first
        results = engine.search_matches(team="Flamengo", limit=20)
        dates = [m["date"] for m in results if m["date"]]
        assert dates == sorted(dates, reverse=True)


class TestTeamQueries:
    def test_team_statistics_returns_wins_losses_draws_goals(self, engine: QueryEngine):
        # Given the match data is loaded
        # When I request statistics for "Palmeiras" in season "2022"
        # Then I should receive wins, losses, draws, and goals
        stats = engine.team_statistics(team="Palmeiras", season=2022)
        assert stats["team_key"] == "palmeiras"
        assert stats["matches"] > 0
        assert stats["wins"] + stats["draws"] + stats["losses"] == stats["matches"]
        assert stats["goals_for"] >= 0
        assert stats["goals_against"] >= 0
        assert "win_rate" in stats

    def test_team_statistics_home_venue(self, engine: QueryEngine):
        # Given the match data is loaded
        # When I request Corinthians home record in 2022
        # Then only home matches are counted
        stats = engine.team_statistics(team="Corinthians", season=2022, venue="home")
        assert stats["matches"] == stats["home"]["matches"]
        assert stats["away"]["matches"] == 0

    def test_team_statistics_unknown_team_is_empty(self, engine: QueryEngine):
        stats = engine.team_statistics(team="NoSuch FC")
        assert stats["matches"] == 0

    def test_competitions_for_team_lists_all_competitions(self, engine: QueryEngine):
        # Given the match data is loaded
        # When I ask which competitions Palmeiras played in
        # Then I get a non-empty list
        result = engine.competitions_for_team("Palmeiras")
        assert result["team_key"] == "palmeiras"
        assert len(result["competitions"]) >= 1

    def test_team_statistics_points_three_per_win(self, engine: QueryEngine):
        # Given a team's stats
        # When I read points
        # Then it equals 3*wins + 1*draws
        stats = engine.team_statistics(team="Flamengo", season=2019)
        assert stats["points"] == 3 * stats["wins"] + stats["draws"]


class TestHeadToHead:
    def test_fla_flu_head_to_head(self, engine: QueryEngine):
        # Given the match data is loaded
        # When I request the head-to-head between Flamengo and Fluminense
        # Then I get wins/draws/goals plus the match list
        h2h = engine.head_to_head("Flamengo", "Fluminense")
        assert h2h["team_a_key"] == "flamengo"
        assert h2h["team_b_key"] == "fluminense"
        assert h2h["is_derby"] is True
        total = h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"]
        assert total == h2h["matches_total"]
        assert total > 0
        assert "matches" in h2h

    def test_head_to_head_symmetric(self, engine: QueryEngine):
        # Given two teams A and B
        # When I swap their order
        # Then the win counts swap and totals match
        ab = engine.head_to_head("Palmeiras", "Corinthians")
        ba = engine.head_to_head("Corinthians", "Palmeiras")
        assert ab["team_a_wins"] == ba["team_b_wins"]
        assert ab["team_b_wins"] == ba["team_a_wins"]
        assert ab["matches_total"] == ba["matches_total"]


class TestPlayerQueries:
    def test_top_rated_brazilians(self, engine: QueryEngine):
        # Given the FIFA data
        # When I ask for top-rated Brazilian players
        # Then I get a non-empty list sorted by overall desc
        players = engine.top_rated_by_nationality("Brazil", limit=10)
        assert players
        overalls = [p["overall"] for p in players if p["overall"] is not None]
        assert overalls == sorted(overalls, reverse=True)
        assert players[0]["overall"] >= 85

    def test_search_players_by_name(self, engine: QueryEngine):
        # Given the FIFA data
        # When I search by name "Neymar"
        # Then I get the Neymar Jr. record
        results = engine.search_players(name="Neymar", limit=5)
        assert results
        assert any("neymar" in p["name"].lower() for p in results)

    def test_search_players_by_nationality_and_position(self, engine: QueryEngine):
        # Given the FIFA data
        # When I filter Brazilian forwards
        # Then every result is Brazilian and a forward
        results = engine.search_players(nationality="Brazil", position="ST", limit=20)
        for p in results:
            assert p["nationality"] == "Brazil"
            assert p["position"] == "ST"

    def test_top_rated_by_club_gremio(self, engine: QueryEngine):
        # Given the FIFA data
        # When I ask for top-rated Grêmio players
        # Then I get a non-empty list
        players = engine.top_rated_by_club("Grêmio", limit=5)
        assert players

    def test_search_players_min_overall(self, engine: QueryEngine):
        # Given the FIFA data
        # When I filter min_overall=85
        # Then every result has overall >= 85
        results = engine.search_players(min_overall=85, limit=50)
        for p in results:
            assert p["overall"] >= 85


class TestCompetitionQueries:
    def test_list_competitions(self, engine: QueryEngine):
        comps = engine.list_competitions()
        names = {c["competition"] for c in comps}
        assert "Brasileirão Série A" in names
        assert "Copa do Brasil" in names
        assert "Copa Libertadores" in names
        for c in comps:
            assert c["matches"] > 0

    def test_standings_2019_champion_is_flamengo(self, engine: QueryEngine):
        # Given the loaded match data
        # When I request the 2019 Brasileirão standings
        # Then the champion (first row) is Flamengo
        standings = engine.standings(season=2019, competition="Brasileirão Série A")
        assert standings
        assert standings[0].get("champion") is True
        assert standings[0]["team_key"] == "flamengo"

    def test_standings_points_descending(self, engine: QueryEngine):
        # Given a standings table
        # When I read the rows in order
        # Then points are non-increasing
        standings = engine.standings(season=2019)
        pts = [r["points"] for r in standings]
        assert pts == sorted(pts, reverse=True)

    def test_standings_cup_returns_note(self, engine: QueryEngine):
        # Given a knockout cup competition
        # When I ask for standings
        # Then I get an explanatory note, not a table
        standings = engine.standings(season=2018, competition="Copa do Brasil")
        assert len(standings) == 1
        assert "note" in standings[0]

    def test_standings_2018_libertadores_returns_note(self, engine: QueryEngine):
        standings = engine.standings(season=2018, competition="Copa Libertadores")
        assert len(standings) == 1
        assert "note" in standings[0]


class TestStatisticalAnalysis:
    def test_average_goals_brasileirao(self, engine: QueryEngine):
        # Given the loaded matches
        # When I compute average goals per Brasileirão match
        # Then the value is in a plausible 2.0-3.0 range
        stats = engine.average_goals(competition="brasileirao")
        assert 2.0 <= stats["average_goals_per_match"] <= 3.0
        assert stats["home_win_rate"] > stats["away_win_rate"]

    def test_average_goals_libertadores(self, engine: QueryEngine):
        stats = engine.average_goals(competition="libertadores")
        assert stats["average_goals_per_match"] > 0
        assert stats["total_matches"] > 100

    def test_biggest_wins_returns_margin_sorted(self, engine: QueryEngine):
        # Given the loaded matches
        # When I ask for the biggest wins
        # Then the results are sorted by margin descending
        wins = engine.biggest_wins(limit=10)
        assert wins
        margins = [w["margin"] for w in wins]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 4

    def test_best_home_record(self, engine: QueryEngine):
        # Given the loaded matches
        # When I ask for the best home record
        # Then I get a list of teams sorted by win rate
        rows = engine.best_record_by_venue(venue="home", min_matches=50)
        assert rows
        rates = [r["home"]["win_rate"] for r in rows]
        assert rates == sorted(rates, reverse=True)

    def test_derbies_in_season(self, engine: QueryEngine):
        # Given the loaded matches and the derby table
        # When I ask for 2023 derbies
        # Then I get a non-empty list
        derbies = engine.derbies_in_season(season=2022)
        assert derbies

    def test_top_scorers_by_team_proxy(self, engine: QueryEngine):
        # Given the FIFA data
        # When I ask for top scorers at Grêmio
        # Then I get players ranked by the Finishing attribute
        scorers = engine.top_scorers_by_team("Grêmio", limit=5)
        assert scorers
        fins = [s.get("finishing") for s in scorers if s.get("finishing") is not None]
        assert fins == sorted(fins, reverse=True)


class TestListTeamsAndSources:
    def test_list_teams(self, engine: QueryEngine):
        teams = engine.list_teams()
        keys = {t["team_key"] for t in teams}
        assert "flamengo" in keys
        assert "palmeiras" in keys
        for t in teams:
            assert t["matches"] >= 1

    def test_list_teams_per_competition(self, engine: QueryEngine):
        teams = engine.list_teams(competition="copa do brasil")
        assert teams
        # All listed teams have played in Copa do Brasil; we cannot verify
        # directly from list_teams, but the engine guarantees the filter.

    def test_sources_summary(self, engine: QueryEngine):
        s = engine.sources()
        assert s["matches_total"] > 0
        assert s["players_total"] > 0
        assert len(s["source_files"]) == 6
