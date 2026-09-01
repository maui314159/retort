"""Cross-file integration checks joining player and match datasets."""

from __future__ import annotations


def test_club_squad_joins_match_history(service):
    """A FIFA club resolves to the same canonical team as the match files."""
    resolution = service.resolve_team("Santos")
    assert resolution["key"] == "santos-sp"

    squad = service.search_players(club="Santos", limit=5)
    assert squad["total"] > 0
    assert all(p["club_key"] == "santos-sp" for p in squad["players"])

    stats = service.team_stats("Santos")
    assert stats["overall"]["matches"] > 500
    assert stats["team"] == resolution["display"]


def test_player_query_and_match_query_agree_on_team(service):
    """Grêmio players and Grêmio matches share one canonical identity."""
    players = service.top_players(club="Grêmio", n=1)
    assert players["players"][0]["club_key"] == "gremio"

    matches = service.search_matches(team="Grêmio", competition="Copa Libertadores")
    sample = matches["matches"][0]
    assert sample["home_key"] == "gremio" or sample["away_key"] == "gremio"


def test_brazilian_clubs_have_both_players_and_matches(service):
    """Every club returned by players_by_club also has match history."""
    by_club = service.players_by_club()
    assert by_club["clubs"]
    for entry in by_club["clubs"][:5]:
        stats = service.team_stats(entry["club"])
        assert stats["overall"]["matches"] > 0, entry["club"]
