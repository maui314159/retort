"""
BDD scenarios: competition queries (TASK.md "Required Capabilities" #4).

Feature: Competition Queries
  Scenario: Standings by season
    Given the match data is loaded
    When I request the 2019 Brasileirão standings
    Then Flamengo should be champion with 90 points
    And the table should reconcile W+D+L with matches played
"""

from __future__ import annotations




class TestStandings:
    """Scenario: standings calculated from match results."""

    def test_2019_brasileirao_champion_flamengo(self, service):
        # Given the match data is loaded
        # When I calculate the 2019 Brasileirão table
        standings = service.standings("brasileirao", 2019)
        # Then Flamengo is champion with the TASK.md example's numbers
        champion = standings.champion
        assert champion.display == "Flamengo"
        assert champion.points == 90
        assert (champion.wins, champion.draws, champion.losses) == (28, 6, 4)
        assert (champion.goals_for, champion.goals_against) == (86, 37)

    def test_2019_table_shape(self, service):
        standings = service.standings("brasileirao", 2019)
        # Then 20 teams each played 38 matches (380 games, complete season)
        assert len(standings.table) == 20
        assert all(r.matches == 38 for r in standings.table)
        total_matches = sum(r.matches for r in standings.table) // 2
        assert total_matches == 380

    def test_points_reconcile(self, service):
        standings = service.standings("brasileirao", 2019)
        for row in standings.table:
            assert row.points == row.wins * 3 + row.draws
            assert row.matches == row.wins + row.draws + row.losses

    def test_goal_balance(self, service):
        # Given goals scored and conceded across the whole table
        standings = service.standings("serie a", 2019)
        # Then total GF equals total GA (every goal is counted twice)
        gf = sum(r.goals_for for r in standings.table)
        ga = sum(r.goals_against for r in standings.table)
        assert gf == ga

    def test_brazilian_tiebreak_prefers_wins(self, service):
        # Given Santos and Palmeiras both finished 2019 on 74 points
        standings = service.standings("brasileirao", 2019)
        table = standings.table
        santos = next(r for r in table if r.display == "Santos")
        palmeiras = next(r for r in table if r.display == "Palmeiras")
        assert santos.points == palmeiras.points == 74
        # Then Santos ranks higher via more wins (Brazilian tie-break)
        assert table.index(santos) < table.index(palmeiras)
        assert santos.wins > palmeiras.wins

    def test_incomplete_season_is_flagged(self, service):
        # Given 2022's data stops before the season end (81 unplayed)
        from brazilian_soccer_mcp.formatting import format_standings

        text = format_standings(service.standings("brasileirao", 2022))
        # Then the rendering says the table is partial
        assert "based on 299 played matches" in text


class TestChampion:
    """Scenario: 'Who won the 2019 Brasileirão?'."""

    def test_league_champion(self, service):
        answer = service.champion("brasileirao", 2019)
        assert "Flamengo - 90 pts (28W, 6D, 4L)" in answer
        assert "Runner-up: Santos" in answer

    def test_libertadores_champion_from_final(self, service):
        # Given the 2019 Libertadores final: Flamengo 2-1 River Plate
        answer = service.champion("libertadores", 2019)
        assert "Champion: Flamengo" in answer
        assert "2-1 River Plate" in answer

    def test_two_legged_final_aggregate(self, service):
        # Given the 2018 Libertadores final ended 2-2 / 3-1
        answer = service.champion("libertadores", 2018)
        # Then River Plate win on aggregate 5-3
        assert "Champion: River Plate" in answer
        assert "5-3" in answer

    def test_penalty_shootout_case_is_honest(self, service):
        # Given the 2022 Copa do Brasil final ended level on aggregate
        answer = service.champion("Copa do Brasil", 2022)
        # Then the answer says the dataset cannot decide it
        assert "tied 1-1" in answer
        assert "penalties" in answer

    def test_copa_do_brasil_2023_champion(self, service):
        answer = service.champion("Copa do Brasil", 2023)
        assert "Champion: São Paulo" in answer

    def test_copa_do_brasil_2021_from_fallback_dates(self, service):
        # Given the 2021 cup rounds are truncated in the dedicated file
        # When the final is recovered from the last played dates
        answer = service.champion("Copa do Brasil", 2021)
        # Then Atlético Mineiro's 6-1 aggregate final is found
        assert "Champion: Atlético Mineiro" in answer
        assert "6-1" in answer


class TestRelegated:
    """Scenario: 'Which teams were relegated in 2020?'."""

    def test_relegation_zone_2020(self, service):
        relegated = service.relegated("brasileirao", 2020)
        names = [r.display for r in relegated]
        # listed worst-first: Botafogo finished bottom
        assert names == ["Botafogo", "Coritiba", "Goiás", "Vasco da Gama"]

    def test_relegation_zone_2019(self, service):
        relegated = service.relegated("brasileirao", 2019)
        names = {r.display for r in relegated}
        assert names == {"Avaí", "CSA", "Chapecoense", "Cruzeiro"}

    def test_relegated_are_the_bottom(self, service):
        standings = service.standings("brasileirao", 2019)
        bottom = {r.display for r in standings.table[-4:]}
        relegated = {r.display for r in service.relegated("brasileirao", 2019)}
        assert bottom == relegated


class TestCompetitionDiscovery:
    """Scenario: which competitions and seasons exist."""

    def test_list_competitions(self, service):
        assert set(service.competitions()) == {
            "Brasileirão Série A",
            "Brasileirão Série B",
            "Brasileirão Série C",
            "Copa do Brasil",
            "Copa Libertadores",
        }

    def test_season_coverage(self, service):
        # Given TASK.md's data tables
        assert service.seasons("brasileirao") == list(range(2003, 2024))
        assert service.seasons("libertadores") == list(range(2013, 2023))
        assert service.seasons("Copa do Brasil") == list(range(2012, 2024))

    def test_competition_aliases(self, service):
        # Given users say competitions in many ways
        for alias, expected in [
            ("brasileirao", "Brasileirão Série A"),
            ("Serie A", "Brasileirão Série A"),
            ("serie b", "Brasileirão Série B"),
            ("SÉRIE C", "Brasileirão Série C"),
            ("brazilian cup", "Copa do Brasil"),
            ("libertadores", "Copa Libertadores"),
            ("Campeonato Brasileiro", "Brasileirão Série A"),
        ]:
            assert service.resolve_competition(alias) == expected

    def test_resolution_is_idempotent(self, service):
        # Given an already-canonical name
        for canonical in service.competitions():
            # When resolved again
            # Then it round-trips unchanged (no Série B -> Série A mangling)
            assert service.resolve_competition(canonical) == canonical
