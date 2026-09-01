"""
BDD scenarios: team-name normalization.

Feature: Team name normalization
  TASK.md "Data Quality Notes" -> "Team Name Variations": the datasets mix
  state-suffixed names ("Palmeiras-SP"), bare names ("Palmeiras"), full
  official names ("Sport Club Corinthians Paulista", "Atlético Mineiro"),
  accented spellings ("Goiás"/"Goias") and foreign markers
  ("Barcelona-EQU", "Nacional (URU)"). The registry must map all variants
  of one club onto one identity while keeping genuinely different clubs
  that share a base name APART (Atlético-MG vs Atlético-PR; Flamengo-RJ
  vs Flamengo-PI; Botafogo-RJ vs Botafogo-SP; Santos-SP vs Santos-AP).
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.normalizer import parse_name, strip_accents


class TestParseName:
    """Scenario Outline: parsing every documented naming pattern."""

    @pytest.mark.parametrize(
        ("raw", "expected_base", "expected_state"),
        [
            # With state suffix (TASK.md: 'Palmeiras-SP', 'Flamengo-RJ')
            ("Palmeiras-SP", "palmeiras", "sp"),
            ("Flamengo-RJ", "flamengo", "rj"),
            ("América - MG", "america", "mg"),          # spaced dash variant
            ("Botafogo RJ", "botafogo", "rj"),          # space-separated state
            # Without suffix
            ("Palmeiras", "palmeiras", None),
            ("Boca Juniors", "boca juniors", None),
            # Accents normalized (TASK.md: 'São Paulo, Grêmio, Avaí')
            ("São Paulo", "sao paulo", None),
            ("Goiás", "goias", None),
            ("Grêmio-RS", "gremio", "rs"),
            # Filler tokens stripped from full official names
            ("São Paulo FC", "sao paulo", None),
            ("EC Bahia", "bahia", None),
            ("Fortaleza Esporte Clube", "fortaleza", None),
            ("Sport Club Corinthians Paulista", "corinthians", None),
            # 'Sport' alone must survive (Sport Recife IS named Sport)
            ("Sport-PE", "sport", "pe"),
            # Alias table resolves full club names to base+state
            ("Atlético Mineiro", "atletico", "mg"),
            ("Atletico Paranaense", "atletico", "pr"),
            ("Athletico Paranaense", "atletico", "pr"),
            ("Vasco da Gama", "vasco", None),
            ("Sport Club do Recife", "sport", None),
            ("Ceará Sporting Club", "ceara", None),
            # Parenthetical notes dropped entirely
            (
                "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ",
                "boavista sport",
                "rj",
            ),
        ],
    )
    def test_parse_patterns(self, raw, expected_base, expected_state):
        # When I parse the raw name
        parsed = parse_name(raw)
        # Then base and state match the documented convention
        assert parsed.base == expected_base
        assert parsed.state == expected_state

    def test_foreign_marker_paren(self):
        # Given a Libertadores name with a parenthetical country marker
        # When I parse it
        parsed = parse_name("Nacional (URU)")
        # Then the foreign marker is kept and the note is not part of the base
        assert parsed.base == "nacional"
        assert parsed.foreign == "uru"

    def test_foreign_marker_dash(self):
        # Given dash-form foreign markers
        # When I parse them
        # Then they are marked foreign, not Brazilian states
        assert parse_name("Barcelona-EQU").foreign == "equ"
        assert parse_name("Olimpia-PAR").foreign == "par"


class TestRegistryResolution:
    """Scenario: one club, many spellings -> one canonical id."""

    def test_state_suffix_and_bare_name_unify(self, service):
        # Given the loaded registry
        # When I resolve 'Palmeiras-SP' and 'Palmeiras'
        suffixed = service.resolve_team("Palmeiras-SP")
        bare = service.resolve_team("Palmeiras")
        # Then both resolve to the same team
        assert suffixed.team_id == bare.team_id == "palmeiras"

    def test_accented_query_matches(self, service):
        assert service.resolve_team("Goiás").team_id == "goias"
        assert service.resolve_team("Goias").team_id == "goias"

    def test_full_official_name_matches(self, service):
        # Given the full official name from TASK.md's naming notes
        # When I resolve it
        ref = service.resolve_team("Sport Club Corinthians Paulista")
        # Then it maps to the same club as the short name
        assert ref.team_id == service.resolve_team("Corinthians").team_id

    def test_atletico_mineiro_alias(self, service):
        assert service.resolve_team("Atletico Mineiro").team_id == "atletico-mg"
        assert service.resolve_team("Atlético-MG").team_id == "atletico-mg"

    def test_same_base_different_clubs_stay_apart(self, service):
        # Given clubs that share a base name but differ by state
        # When I resolve each variant
        # Then they are distinct identities
        atletico = {
            service.resolve_team(n).team_id for n in ("Atlético-MG", "Atlético-PR", "Atlético-GO")
        }
        assert len(atletico) == 3
        def team_id_for(name: str) -> str:
            return service.resolve_team(name).team_id

        assert team_id_for("Botafogo RJ") != team_id_for("Botafogo SP")
        assert team_id_for("América - MG") != team_id_for("América - RN")
        # Flamengo-RJ (the famous club) vs Flamengo-PI (a small Copa club)
        assert team_id_for("Flamengo-RJ") != team_id_for("Flamengo-PI")

    def test_bare_ambiguous_name_prefers_famous_club(self, service):
        # Given a bare ambiguous base like 'Flamengo' or 'Santos'
        # When I resolve it without a state
        # Then the famous club is chosen
        assert service.resolve_team("Flamengo").team_id == "flamengo-rj"
        assert service.resolve_team("Santos").team_id == "santos-sp"
        assert service.resolve_team("Internacional").team_id == "internacional-rs"

    def test_athletico_spelling_is_paranaense(self, service):
        # Given the FIFA-era 'Athletico' spelling
        # When I resolve it bare
        # Then it is Athletico Paranaense (atletico-pr), never Atlético Mineiro
        assert service.resolve_team("Athletico").team_id == "atletico-pr"

    def test_fuzzy_and_unknown_input(self, service):
        # Given input that only partially matches
        ref = service.resolve_team("Fluminense-RJ")
        # base "fluminense" is ambiguous (Fluminense-RJ vs Fluminense-PI in
        # Copa do Brasil), so the canonical id keeps the state
        assert ref.team_id == "fluminense-rj"
        # And input that matches nothing
        # Then a helpful error is raised
        with pytest.raises(LookupError):
            service.resolve_team("ZZZ Not A Team ZZZ")

    def test_display_names_keep_accents(self, service):
        # Given teams with accented Portuguese names
        # When I ask for display names
        # Then UTF-8 accents survive (TASK.md 'Character Encoding')
        assert service.registry.display("sao paulo") == "São Paulo"
        assert service.registry.display("gremio") == "Grêmio"
        assert service.registry.display("atletico-mg") == "Atlético Mineiro"

    def test_variants_expose_raw_spellings(self, service):
        variants = service.registry.variants("palmeiras")
        assert "Palmeiras" in variants or "Palmeiras-SP" in variants


def test_strip_accents_is_pure():
    assert strip_accents("São Paulo") == "Sao Paulo"
    assert strip_accents("Avaí") == "Avai"
    assert strip_accents("plain") == "plain"
