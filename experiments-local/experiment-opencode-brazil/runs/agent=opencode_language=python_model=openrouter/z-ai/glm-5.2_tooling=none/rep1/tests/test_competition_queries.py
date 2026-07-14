from brazilian_soccer_mcp import QueryEngine


def test_2019_brasileirao_champion(engine):
    """Feature: Competition Queries
    Scenario: who won the 2019 Brasileirao
      Given the match data is loaded
      When I request the 2019 Brasileirao champion
      Then the champion should be Flamengo with 90 points
    """
    champ = engine.competition_champion("Brasileirao", 2019)
    assert champ is not None
    assert champ.team_id == "flamengo"
    assert champ.points == 90
    assert champ.wins == 28 and champ.draws == 6 and champ.losses == 4


def test_standings_full_table(engine):
    """Scenario: 2019 Brasileirao final standings
      When I request the full standings
      Then there should be 20 teams and points are non-increasing
    """
    table = engine.competition_standings("Brasileirao", 2019)
    assert len(table) == 20
    points = [r.points for r in table]
    assert points == sorted(points, reverse=True)
    assert table[0].position == 1
    assert all(r.matches == 38 for r in table)


def test_relegated_teams(engine):
    """Scenario: which teams were relegated in 2019
      When I request the bottom 4 of 2019 Brasileirao
      Then the last team is position 20
    """
    relegated = engine.relegated_teams("Brasileirao", 2019, n=4)
    assert len(relegated) == 4
    ids = {r.team_id for r in relegated}
    assert "avai" in ids
    assert relegated[-1].position == 20


def test_copa_do_brasil_has_matches(engine):
    """Scenario: Copa do Brasil matches exist
      When I search Copa do Brasil matches for a season
      Then I get results
    """
    matches = engine.search_matches(competition="Copa do Brasil", season=2019, limit=10)
    assert len(matches) > 0
    assert all(m.competition == "Copa do Brasil" for m in matches)


def test_champion_for_multiple_seasons(engine):
    """Scenario: champion across multiple seasons
      When I request champions for several seasons
      Then each returns a valid team with 38 matches (full season)
    """
    for season in [2018, 2019, 2020]:
        champ = engine.competition_champion("Brasileirao", season)
        assert champ is not None
        assert champ.matches >= 38
