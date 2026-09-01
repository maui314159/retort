"""Feature: Competition Queries (BDD)

Spec scenarios:

    Scenario: Who won the 2019 Brasileirão?
      Given the match data is loaded
      When I request the 2019 Serie A standings
      Then Flamengo is Champion with 90 points (28W, 6D, 4L)

    Scenario: Which teams were relegated in 2020?
      When I request the 2020 relegation zone
      Then Vasco, Goiás, Coritiba and Botafogo are returned
"""

from __future__ import annotations

import pytest

from brsoccer import queries as q
from brsoccer.data import COMPETITIONS

pytestmark = pytest.mark.bdd


class TestStandings:
    """Scenario: Standings by season, calculated from match results."""

    def test_2019_brasileirao_champion_is_flamengo(self, sd):
        # Given the match data is loaded (deduped across files)
        # When I request the 2019 Serie A standings
        table = q.standings(sd, "serie_a", 2019)
        # Then the table has 20 teams
        assert len(table) == 20
        # And Flamengo is Champion with exactly the spec's numbers
        champion = table[0]
        assert champion.display == "Flamengo"
        assert champion.points == 90
        assert (champion.win, champion.draw, champion.loss) == (28, 6, 4)
        assert (champion.goals_for, champion.goals_against) == (86, 37)

    def test_2019_runners_up(self, sd):
        # And Palmeiras and Santos follow on 74 points
        table = q.standings(sd, "serie_a", 2019)
        assert table[1].display == "Palmeiras"
        assert table[1].points == 74
        assert (table[1].win, table[1].draw, table[1].loss) == (21, 11, 6)
        assert table[2].display == "Santos"
        assert table[2].points == 74
        assert (table[2].win, table[2].draw, table[2].loss) == (22, 8, 8)

    def test_standings_are_ordered_by_points(self, sd):
        # When I request any season's table
        table = q.standings(sd, "serie_a", 2016)
        # Then points are non-increasing down the table
        points = [row.points for row in table]
        assert points == sorted(points, reverse=True)
        # And every team played the same number of matches
        played = {row.played for row in table}
        assert played == {38}

    def test_every_season_since_2006_has_380_matches(self, sd):
        # Given complete double round-robin seasons
        # When I count matches per season
        per_season = {}
        for match in sd.matches_for_competition("serie_a"):
            if match.season:
                per_season[match.season] = per_season.get(match.season, 0) + 1
        # Then 2006-2022 all have exactly 380 (data holes only in 2009/2015/2023)
        for season in range(2006, 2023):
            if season in (2009, 2015):
                assert abs(per_season[season] - 380) <= 1
            else:
                assert per_season[season] == 380, f"season {season}"
        assert per_season[2023] == 377  # BRF 2023 is three matches short

    def test_default_season_is_the_latest(self, sd):
        # When I request standings without a season
        table = q.standings(sd, "serie_a")
        # Then the latest covered season is used (2023, with all 20 teams)
        latest = sd.seasons_for("serie_a")[-1]
        assert latest == 2023
        assert len(table) == 20
        points = [row.points for row in table]
        assert points == sorted(points, reverse=True)

    def test_cups_refuse_standings_with_guidance(self, sd):
        # When I request standings for a knockout competition
        with pytest.raises(q.QueryError, match="not a league"):
            q.standings(sd, "libertadores")
        with pytest.raises(q.QueryError, match="not a league"):
            q.standings(sd, "copa_do_brasil")
        # And the error points at stage filters instead
        with pytest.raises(q.QueryError, match="stage"):
            q.standings(sd, "copa")

    def test_unknown_season_is_rejected_with_range(self, sd):
        # When I request a season with no data
        with pytest.raises(q.QueryError, match="Available seasons"):
            q.standings(sd, "serie_a", 1999)


class TestRelegation:
    """Scenario: Which teams were relegated in 2020?"""

    def test_2020_relegated_teams(self, sd):
        # When I request the 2020 relegation zone
        rows = q.relegation(sd, "serie_a", 2020)
        # Then the bottom four are Vasco, Goiás, Coritiba and Botafogo
        relegated = {row.display for row in rows}
        assert relegated == {"Vasco", "Goiás", "Coritiba", "Botafogo-RJ"}
        # And they are ordered worst-first within the zone
        points = [row.points for row in rows]
        assert points == sorted(points, reverse=True)

    def test_2019_relegated_teams(self, sd):
        # When I request the 2019 relegation zone
        rows = q.relegation(sd, "serie_a", 2019)
        # Then CSA, Chapecoense and Avaí join Cruzeiro in the bottom four
        relegated = {row.display for row in rows}
        assert relegated == {"Cruzeiro", "Chapecoense", "CSA", "Avaí"}


class TestCompetitionInfo:
    """Scenario: Competition coverage across all six files."""

    def test_all_five_competitions_are_covered(self, sd):
        # When I request the overview of all competitions
        info = q.competition_info(sd)
        codes = {c["code"] for c in info["competitions"]}
        # Then all five competitions are present
        assert codes == {"serie_a", "serie_b", "serie_c", "copa_do_brasil", "libertadores"}
        # And Serie A spans 2003-2023 (historical + modern + BRF files)
        serie_a = next(c for c in info["competitions"] if c["code"] == "serie_a")
        assert serie_a["first_season"] == 2003
        assert serie_a["last_season"] == 2023
        assert serie_a["matches"] == 8403

    def test_single_competition_info(self, sd):
        # When I request info for the Libertadores
        info = q.competition_info(sd, "libertadores")
        # Then the summary describes seasons and the knockout note
        assert info["display"] == COMPETITIONS["libertadores"]
        assert info["first_season"] == 2013
        assert "stage" in info["note"]

    def test_competition_aliases(self, sd):
        # When I use friendly names instead of codes
        # Then they resolve to the same competitions
        assert q.competition_info(sd, "brasileirao")["code"] == "serie_a"
        assert q.competition_info(sd, "copa")["code"] == "copa_do_brasil"


class TestCrossFileQueries:
    """Scenario: Cross-file queries work (player + match data)."""

    def test_player_club_joins_match_data_team(self, sd):
        # Given a FIFA club that exists in the match data
        players = q.search_players(sd, club="Atlético Mineiro")
        key = q.resolve_team(sd, "Atlético Mineiro")
        # When I look up the same team's match record
        stats = q.team_stats(sd, "Atlético Mineiro")
        # Then both resolve to one canonical team identity
        assert all(p.club_key == key for p in players)
        assert stats["key"] == key
        assert stats["overall"]["matches"] > 500

    def test_team_appears_in_multiple_source_files(self, sd):
        # When I trace Flamengo matches by source file
        sources = {m.source for m in sd.matches_for_team(q.resolve_team(sd, "Flamengo"))}
        # Then several distinct files contribute (dedupe kept one row each)
        assert len(sources) >= 3
