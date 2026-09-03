"""
Context Block
=============

Module: tests.test_normalizer
Purpose: Unit tests for the team-name and date normalisation
         utilities in ``brazilian_soccer_mcp.normalizer``.
"""

from __future__ import annotations

from brazilian_soccer_mcp.normalizer import (
    team_match_key,
    team_state,
    team_canonical,
    display_name,
    parse_date,
    format_date,
)


# ---------------------------------------------------------------------------
# team_match_key
# ---------------------------------------------------------------------------
class TestTeamMatchKey:
    """Tests for team name normalisation."""

    def test_strips_state_suffix(self):
        """Given a team name with state suffix, the key has no suffix."""
        assert team_match_key("Palmeiras-SP") == "palmeiras"
        assert team_match_key("Flamengo-RJ") == "flamengo"
        assert team_match_key("Corinthians-SP") == "corinthians"

    def test_without_suffix(self):
        """Given a team name without suffix, the key is the base name."""
        assert team_match_key("Palmeiras") == "palmeiras"
        assert team_match_key("Flamengo") == "flamengo"

    def test_strips_accents(self):
        """Given an accented name, the key has no accents."""
        assert team_match_key("Grêmio") == "gremio"
        assert team_match_key("São Paulo") == "sao paulo"
        assert team_match_key("Criciúma") == "criciuma"

    def test_strips_spaced_state_suffix(self):
        """Given 'America - MG' style, the state is stripped."""
        assert team_match_key("America - MG") == "america"

    def test_strips_trailing_state_word(self):
        """Given 'America MG' style, the state word is stripped."""
        assert team_match_key("America MG") == "america"
        assert team_match_key("America RN") == "america"

    def test_strips_parenthetical(self):
        """Given a name with parenthetical notes, they are removed."""
        key = team_match_key("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")
        assert key == "boavista sport"

    def test_alias_atletico_mineiro(self):
        """Given 'Atletico Mineiro', it resolves to the same key as 'Atletico-MG'."""
        assert team_match_key("Atletico Mineiro") == team_match_key("Atletico-MG")

    def test_alias_atletico_paranaense(self):
        """Given 'Atletico Paranaense', it resolves to the same key as 'Atletico-PR'."""
        assert team_match_key("Atletico Paranaense") == team_match_key("Atletico-PR")

    def test_alias_america_fc_natal(self):
        """Given 'America FC Natal', it resolves to the same key as 'America-RN'."""
        assert team_match_key("America FC Natal") == team_match_key("America-RN")

    def test_empty_name(self):
        """Given an empty name, the key is empty."""
        assert team_match_key("") == ""
        assert team_match_key(None) == ""

    def test_foreign_suffix(self):
        """Given a foreign suffix, it is stripped."""
        assert team_match_key("Barcelona-EQU") == "barcelona"
        assert team_match_key("Nacional (URU)") == "nacional"


# ---------------------------------------------------------------------------
# team_state
# ---------------------------------------------------------------------------
class TestTeamState:
    """Tests for state extraction."""

    def test_from_suffix(self):
        assert team_state("Palmeiras-SP") == "SP"
        assert team_state("Flamengo-RJ") == "RJ"

    def test_from_spaced_suffix(self):
        assert team_state("America - MG") == "MG"

    def test_from_trailing_word(self):
        assert team_state("America MG") == "MG"

    def test_from_alias(self):
        assert team_state("Atletico Mineiro") == "MG"
        assert team_state("Atletico Paranaense") == "PR"

    def test_no_state(self):
        assert team_state("Flamengo") is None
        assert team_state("Santos") is None

    def test_empty(self):
        assert team_state("") is None
        assert team_state(None) is None


# ---------------------------------------------------------------------------
# team_canonical
# ---------------------------------------------------------------------------
class TestTeamCanonical:
    """Tests for the canonical (base, state) tuple."""

    def test_with_state(self):
        base, state = team_canonical("Palmeiras-SP")
        assert base == "palmeiras"
        assert state == "SP"

    def test_without_state(self):
        base, state = team_canonical("Flamengo")
        assert base == "flamengo"
        assert state is None


# ---------------------------------------------------------------------------
# display_name
# ---------------------------------------------------------------------------
class TestDisplayName:
    """Tests for display name formatting."""

    def test_strips_suffix(self):
        assert display_name("Palmeiras-SP") == "Palmeiras"

    def test_strips_parenthetical(self):
        name = display_name("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")
        assert "antigo" not in name
        assert "- RJ" not in name

    def test_keeps_accents(self):
        assert display_name("Grêmio") == "Grêmio"
        assert display_name("São Paulo") == "São Paulo"


# ---------------------------------------------------------------------------
# parse_date / format_date
# ---------------------------------------------------------------------------
class TestParseDate:
    """Tests for date parsing."""

    def test_iso_format(self):
        dt = parse_date("2023-09-24")
        assert format_date(dt) == "2023-09-24"

    def test_iso_with_time(self):
        dt = parse_date("2012-05-19 18:30:00")
        assert format_date(dt) == "2012-05-19"

    def test_brazilian_format(self):
        dt = parse_date("29/03/2003")
        assert format_date(dt) == "2003-03-29"

    def test_brazilian_with_time(self):
        dt = parse_date("15/07/2018 16:00")
        assert format_date(dt) == "2018-07-15"

    def test_invalid_returns_none(self):
        assert parse_date("not a date") is None
        assert parse_date(None) is None
        assert parse_date("") is None

    def test_preserves_datetime(self):
        from datetime import datetime
        dt = datetime(2020, 1, 15)
        assert parse_date(dt) == dt
