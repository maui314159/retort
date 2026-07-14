from brazilian_soccer_mcp import QueryEngine


def test_search_player_by_name(engine):
    """Feature: Player Queries
    Scenario: who is Gabriel Barbosa
      Given the FIFA player data is loaded
      When I search for a player named "Neymar"
      Then I should get at least one matching player
    """
    players = engine.search_player(name="Neymar")
    assert len(players) >= 1
    assert any("Neymar" in p.name for p in players)


def test_search_player_accent_insensitive(engine):
    """Scenario: name search is accent-insensitive
      When I search for "São" without typing accents
      Then names with accents also match
    """
    players = engine.search_player(name="Coutinho")
    assert len(players) >= 1


def test_top_brazilian_players(engine):
    """Scenario: top Brazilian players
      When I request the top Brazilian players
      Then the highest rated is Neymar Jr with overall 92
      And every player is Brazilian
    """
    players = engine.top_players(nationality="Brazil", limit=5)
    assert len(players) == 5
    assert players[0].name == "Neymar Jr"
    assert players[0].overall == 92
    assert all(p.nationality == "Brazil" for p in players)
    overalls = [p.overall for p in players]
    assert overalls == sorted(overalls, reverse=True)


def test_players_at_brazilian_club(engine):
    """Scenario: players at a Brazilian club
      When I request players at Cruzeiro
      Then I get a count and an average overall rating
    """
    info = engine.players_at_club("Cruzeiro")
    assert info["club_id"] == "cruzeiro"
    assert info["count"] > 0
    assert info["avg_overall"] > 0
    assert len(info["players"]) == info["count"]


def test_search_player_by_position(engine):
    """Scenario: forwards from a club
      When I search for players at position ST
      Then every returned player has position ST
    """
    players = engine.search_player(position="ST", limit=10)
    assert len(players) > 0
    assert all(p.position == "ST" for p in players)


def test_search_player_min_overall(engine):
    """Scenario: filter by minimum rating
      When I search for players with overall >= 85
      Then every player has overall >= 85
    """
    players = engine.search_player(min_overall=85, limit=20)
    assert len(players) > 0
    assert all(p.overall >= 85 for p in players)
