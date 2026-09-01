"""BDD scenarios: match queries (spec section 1 - Match Queries).

Gherkin:

Feature: Match Queries
  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
"""


from brasil_mcp.store import COPA_DO_BRASIL, SERIE_A


class TestFindMatchesBetweenTwoTeams:
    """Scenario: Find matches between two teams."""

    def test_when_i_search_for_matches_between_flamengo_and_fluminense(self, loaded_store, ask):
        result = ask("search_matches", team="Flamengo", opponent="Fluminense", limit=100)

        assert result["total"] >= 40
        assert len(result["matches"]) >= 40

    def test_then_each_match_has_date_scores_and_competition(self, loaded_store, ask):
        result = ask("search_matches", team="Flamengo", opponent="Fluminense", limit=100)

        for match in result["matches"]:
            assert match["date"], "each match must carry a date"
            assert match["home_goals"] is not None
            assert match["away_goals"] is not None
            assert match["competition"] in {
                "Brasileirão Série A",
                "Copa do Brasil",
                "Copa Libertadores",
            }

    def test_matches_are_newest_first(self, loaded_store, ask):
        result = ask("search_matches", team="Flamengo", opponent="Fluminense", limit=100)
        dates = [m["date"] for m in result["matches"] if m["date"]]
        assert dates == sorted(dates, reverse=True)

    def test_head_to_head_summary_matches_spec_format(self, loaded_store, ask):
        result = ask("head_to_head", team_a="Flamengo", team_b="Fluminense")
        expected = "Head-to-head in dataset: Flamengo 18 wins, Fluminense 14 wins, 12 draws"
        assert expected in result["summary"]
        decided = result["team_a"]["wins"] + result["team_b"]["wins"] + result["team_a"]["draws"]
        assert decided == result["total"]


class TestMatchesBySeason:
    """Scenario: What matches did Flamengo play in each season?"""

    def test_palmeiras_2023_serie_a_matches(self, loaded_store, ask):
        result = ask("search_matches", team="Palmeiras", season=2023, competition="Série A")
        assert result["total"] == 37
        assert all(m["season"] == 2023 for m in result["matches"])
        assert all(m["competition"] == SERIE_A for m in result["matches"])

    def test_every_season_has_38_league_matches(self, loaded_store, ask):
        for season in range(2012, 2023):
            result = ask("search_matches", team="Flamengo", season=season, competition="brasileirão")
            assert result["total"] == 38, f"Flamengo should play 38 Série A matches in {season}"


class TestMatchesByCompetition:
    """Scenario: Find all Copa do Brasil finals."""

    def test_copa_do_brasil_finals_2012(self, loaded_store, ask):
        result = ask("search_matches", competition="Copa do Brasil", season=2012, stage="final")
        assert result["total"] == 2
        pairings = {frozenset((m["home_team"], m["away_team"])) for m in result["matches"]}
        assert pairings == {frozenset(("Palmeiras", "Coritiba"))}
        assert "Palmeiras" in result["summary"]

    def test_libertadores_final_2019(self, loaded_store, ask):
        result = ask("search_matches", competition="Libertadores", season=2019, stage="final")
        assert result["total"] == 1
        final = result["matches"][0]
        assert final["home_team"] == "Flamengo"
        assert final["away_team"] == "River Plate"
        assert (final["home_goals"], final["away_goals"]) == (2, 1)

    def test_competition_filter_is_fuzzy(self, loaded_store, ask):
        for query in ("Brasileirão", "brasileirao", "Série A", "serie a"):
            result = ask("search_matches", team="Flamengo", competition=query, season=2019)
            assert result["total"] == 38
        result = ask("search_matches", team="Flamengo", competition="copa do brasil", season=2019)
        assert all(m["competition"] == COPA_DO_BRASIL for m in result["matches"])


class TestMatchesByDateRange:
    """Scenario: Find matches by date range."""

    def test_date_range_filter(self, loaded_store, ask):
        result = ask(
            "search_matches",
            team="Flamengo",
            date_from="2023-06-01",
            date_to="2023-08-31",
            limit=100,
        )
        assert result["total"] > 0
        for match in result["matches"]:
            assert "2023-06-01" <= match["date"] <= "2023-08-31"

    def test_brazilian_date_format_accepted_in_filters(self, loaded_store):
        matches, total = loaded_store.find_matches(
            team="Flamengo", date_from="2023-06-01", date_to="2023-08-31", limit=None
        )
        assert total > 0


class TestVenueFilters:
    """Scenario: home and away matches of a team."""

    def test_home_venue_filter(self, loaded_store):
        flamengo = loaded_store.resolve_team("Flamengo")
        matches, total = loaded_store.find_matches(
            team="Flamengo", venue="home", season=2019, competition="Série A", limit=None
        )
        assert total == 19
        assert all(m.home == flamengo for m in matches)

    def test_away_venue_filter(self, loaded_store):
        flamengo = loaded_store.resolve_team("Flamengo")
        matches, total = loaded_store.find_matches(
            team="Flamengo", venue="away", season=2019, competition="Série A", limit=None
        )
        assert total == 19
        assert all(m.away == flamengo for m in matches)

    def test_venue_filter_without_competition_spans_all_trophies(self, loaded_store):
        _, home_total = loaded_store.find_matches(
            team="Flamengo", venue="home", season=2019, limit=None
        )
        assert home_total > 19, "2019 also had Copa do Brasil and Libertadores home games"


class TestUnknownTeam:
    """Scenario: unknown team names produce helpful errors."""

    def test_unknown_team_error_with_suggestions(self, ask):
        result = ask("search_matches", team="Flamenguinho")
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_typo_gets_suggestions(self, ask):
        result = ask("find_team", name="Palmeirass")
        assert result.get("suggestions")


class TestMatchQueryPerformance:
    """Spec: simple lookups respond in < 2 seconds."""

    def test_simple_lookup_under_two_seconds(self, loaded_store, ask):
        import time

        start = time.perf_counter()
        ask("search_matches", team="Flamengo", opponent="Corinthians", limit=10)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"simple lookup took {elapsed:.2f}s"
