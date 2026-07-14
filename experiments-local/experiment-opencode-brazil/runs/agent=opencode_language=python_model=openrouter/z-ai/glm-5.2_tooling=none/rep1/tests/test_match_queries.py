from brazilian_soccer_mcp import QueryEngine


def test_all_six_files_loaded(engine):
    """Feature: Data Coverage
    Scenario: all provided CSV files are loadable and queryable
      Given the data loader has run
      When I inspect the data coverage
      Then there should be matches, players, and stats loaded
    """
    cov = engine.data_coverage()
    assert cov["matches_unique"] > 0
    assert cov["matches_raw"] >= cov["matches_unique"]
    assert cov["players"] > 18000
    assert cov["matches_with_stats"] > 0
    for comp in ["Brasileirao", "Copa do Brasil", "Libertadores"]:
        assert comp in cov["competitions"]


def test_load_performance(engine):
    """Scenario: simple lookups respond quickly
      Given the engine is loaded
      When I run a simple lookup
      Then it should respond within 2 seconds
    """
    import time
    t = time.time()
    engine.search_matches(team="Flamengo", season=2023, limit=5)
    assert time.time() - t < 2.0


def test_search_matches_between_two_teams(engine):
    """Feature: Match Queries
    Scenario: find matches between two teams
      Given the match data is loaded
      When I search for matches between "Flamengo" and "Fluminense"
      Then I should receive a list of matches
      And each match should have date, scores, and competition
    """
    matches = engine.search_matches(team="Flamengo", vs_team="Fluminense")
    assert len(matches) > 0
    for m in matches:
        d = m.to_dict()
        assert d["home_goal"] is not None and d["away_goal"] is not None
        assert d["competition"] is not None
        assert {d["home_id"], d["away_id"]} == {"flamengo", "fluminense"}


def test_search_matches_by_team_and_season(engine):
    """Scenario: matches for a team in a season
      When I search Palmeiras matches in 2023
      Then I get only 2023 matches involving Palmeiras
    """
    matches = engine.search_matches(team="Palmeiras", season=2023)
    assert len(matches) > 0
    assert all(m.season == 2023 for m in matches)
    assert all("palmeiras" in (m.home_id, m.away_id) for m in matches)


def test_search_matches_by_competition(engine):
    """Scenario: filter by competition
      When I search Libertadores matches
      Then every match has competition Libertadores
    """
    matches = engine.search_matches(competition="Libertadores", season=2019, limit=50)
    assert len(matches) > 0
    assert all(m.competition == "Libertadores" for m in matches)


def test_search_matches_date_range(engine):
    """Scenario: filter by date range
      When I search Brasileirao matches in a date range
      Then every match date falls inside the range
    """
    matches = engine.search_matches(
        competition="Brasileirao", date_from="2019-09-01", date_to="2019-09-30"
    )
    assert len(matches) > 0
    for m in matches:
        assert m.date is not None
        assert "2019-09-01" <= m.date.isoformat() <= "2019-09-30"
