"""
Feature: Team name, competition and date normalisation
  The six source datasets spell one club many different ways and use three
  date conventions.  Every query capability depends on normalisation
  collapsing those variations onto one canonical club identity.
"""

from __future__ import annotations

import datetime as dt

from brazilian_soccer_mcp.normalizer import (
    ClubNormalizer,
    canonical_key,
    normalize_competition,
    parse_club_name,
    parse_date,
    parse_goals,
    parse_money,
    parse_time,
)


class TestTeamNameVariations:
    """Scenario outlines: one club, many spellings, one canonical key."""

    def test_state_suffixes_collapse(self):
        """
        Scenario: state-suffixed and bare spellings are the same club
          Given the team name normaliser
          When I parse "Palmeiras-SP", "Palmeiras - SP" and "Palmeiras"
          Then all three produce the core "palmeiras"
        """
        assert parse_club_name("Palmeiras-SP").core == "palmeiras"
        assert parse_club_name("Palmeiras - SP").state == "SP"
        assert parse_club_name("Palmeiras").core == "palmeiras"

    def test_accents_are_ignored(self):
        """
        Scenario: accented and unaccented spellings match
          Given the team name normaliser
          When I parse "Grêmio", "Gremio" and "Gremio-RS"
          Then all three produce the core "gremio"
        """
        assert parse_club_name("Grêmio").core == "gremio"
        assert parse_club_name("Gremio").core == "gremio"
        assert parse_club_name("Gremio-RS") == parse_club_name("Grêmio-RS")

    def test_full_official_names(self):
        """
        Scenario: official club names reduce to the common name
          Given the team name normaliser
          When I parse "Sport Club Corinthians Paulista"
          Then the canonical key equals the key of "Corinthians-SP"
        """
        assert canonical_key("Sport Club Corinthians Paulista") == canonical_key(
            "Corinthians-SP"
        )

    def test_curated_aliases(self):
        """
        Scenario: known aliases merge to one club
          Given the team name normaliser
          When I parse "Atlético Mineiro" and "Atletico-MG"
          Then both resolve to core "atletico" with state "MG"
          And "Athletico Paranaense" merges with "Atletico-PR"
          And "Vasco da Gama" merges with "Vasco"
          And "Red Bull Bragantino" merges with "Bragantino-SP"
        """
        assert parse_club_name("Atlético Mineiro") == parse_club_name("Atletico-MG")
        assert parse_club_name("Athletico Paranaense") == parse_club_name("Atletico-PR")
        assert parse_club_name("Vasco da Gama") == parse_club_name("Vasco")
        assert parse_club_name("Red Bull Bragantino").core == "bragantino"
        assert parse_club_name("Red Bull Bragantino").state == "SP"
        assert parse_club_name("Sport Recife") == parse_club_name("Sport-PE")

    def test_stateless_full_names_need_dominance(self):
        """
        Scenario: stateless full names adopt their state after finalize
          Given a normaliser fed the datasets' spellings
          When I resolve "Fortaleza FC" and "EC Bahia"
          Then they land on the same keys as "Fortaleza-CE" and "Bahia-BA"
        """
        normalizer = ClubNormalizer()
        for raw in (
            "Fortaleza-CE",
            "Fortaleza - CE",
            "Bahia-BA",
            "Bahia - BA",
            "Fortaleza FC",
            "EC Bahia",
        ):
            normalizer.register(raw)
        normalizer.finalize()
        assert normalizer.key("Fortaleza FC") == normalizer.key("Fortaleza-CE")
        assert normalizer.key("EC Bahia") == normalizer.key("Bahia-BA")

    def test_parentheticals_and_countries(self):
        """
        Scenario: parentheticals carry region info or are noise
          Given the team name normaliser
          When I parse "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
          Then it resolves to the same key as "Boavista - RJ"
          And "Nacional (URU)" gets country URU
          And "River (PI)" gets state PI
        """
        long_name = parse_club_name(
            "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
        )
        assert long_name == parse_club_name("Boavista - RJ")
        assert parse_club_name("Nacional (URU)").country == "URU"
        assert parse_club_name("River (PI)").state == "PI"
        assert parse_club_name("Barcelona-EQU").country == "EQU"

    def test_dotted_abbreviations(self):
        """
        Scenario: dotted abbreviations normalise to their common form
          Given the team name normaliser
          When I parse "C.r.b. - AL" and "A.b.c. - RN"
          Then the cores are "crb" and "abc"
        """
        assert parse_club_name("C.r.b. - AL").core == "crb"
        assert parse_club_name("A.b.c. - RN").core == "abc"
        assert parse_club_name("C.r.b. - AL").state == "AL"

    def test_sport_clubs_are_not_over_stripped(self):
        """
        Scenario: clubs whose name *is* a form word survive
          Given the team name normaliser
          When I parse "Sport-PE", "Sport Recife" and "Sport Boys"
          Then the first two are the same club and "Sport Boys" stays intact
        """
        assert parse_club_name("Sport-PE") == parse_club_name("Sport Recife")
        assert parse_club_name("Sport Boys").core == "sport boys"

    def test_different_states_are_different_clubs(self):
        """
        Scenario: same core, different state means a different club
          Given the team name normaliser
          When I parse "Botafogo - RJ", "Botafogo - PB" and "Botafogo - SP"
          Then their canonical keys are all different
        """
        keys = {
            canonical_key(n)
            for n in ("Botafogo - RJ", "Botafogo - PB", "Botafogo - SP")
        }
        assert len(keys) == 3


class TestDominantRegionResolution:
    """Scenario: stateless names adopt the region the data actually uses."""

    def test_stateless_name_adopts_dominant_state(self):
        """
        Scenario: "Santos" from a stateless source resolves to Santos-SP
          Given a normaliser fed the spellings the datasets use
          When I finalize it and resolve the stateless "Santos"
          Then the canonical key is "santos|SP"
        """
        normalizer = ClubNormalizer()
        for raw, state in [
            ("Santos-SP", None),
            ("Santos-SP", None),
            ("Santos-AP", None),
            ("Santos", None),
        ]:
            normalizer.register(raw, state)
        normalizer.finalize()
        assert normalizer.key("Santos") == "santos|SP"

    def test_resolution_fails_before_finalize(self):
        """
        Scenario: using the resolver before finalize is a programming error
          Given a fresh ClubNormalizer that has not been finalized
          When I resolve a stateless name
          Then a RuntimeError is raised
        """
        normalizer = ClubNormalizer()
        normalizer.register("Santos-SP", None)
        try:
            normalizer.key("Santos")
        except RuntimeError:
            assert True
        else:
            raise AssertionError("expected RuntimeError before finalize()")


class TestCompetitionNormalisation:
    """Scenario: competition aliases map to canonical ids."""

    def test_aliases(self):
        """
        Scenario: free-text competition names
          Given the competition alias table
          When I normalise "brasileirão", "Série A", "the brasileirao",
            "Copa do Brasil", "CDB", "Libertadores" and "Serie B"
          Then I receive the canonical competition ids
        """
        assert normalize_competition("brasileirão") == "serie_a"
        assert normalize_competition("Série A") == "serie_a"
        assert normalize_competition("the brasileirao") == "serie_a"
        assert normalize_competition("Copa do Brasil") == "copa_do_brasil"
        assert normalize_competition("CDB") == "copa_do_brasil"
        assert normalize_competition("Libertadores") == "libertadores"
        assert normalize_competition("Serie B") == "serie_b"
        assert normalize_competition("Serie C") == "serie_c"

    def test_unknown_and_all(self):
        """
        Scenario: unknown names and wildcards
          Given the competition alias table
          When I normalise "Premier League" and "all"
          Then the first is unknown and the second means every competition
        """
        assert normalize_competition("Premier League") is None
        assert normalize_competition("all") == "all"
        assert normalize_competition(None) is None


class TestCellParsing:
    """Scenario: the per-source cell formats."""

    def test_dates(self):
        """
        Scenario: the three date conventions
          Given the date parser
          When I parse "2012-05-19 18:30:00", "2023-09-24" and "29/03/2003"
          Then I receive the correct dates
        """
        assert parse_date("2012-05-19 18:30:00") == dt.date(2012, 5, 19)
        assert parse_date("2023-09-24") == dt.date(2023, 9, 24)
        assert parse_date("29/03/2003") == dt.date(2003, 3, 29)
        assert parse_date("NA") is None
        assert parse_date("") is None

    def test_goals_sentinels(self):
        """
        Scenario: unplayed fixtures
          Given the goals parser
          When I parse "NA", "-", "2", "1.0" and ""
          Then the sentinels become None and the numbers become ints
        """
        assert parse_goals("NA") is None
        assert parse_goals("-") is None
        assert parse_goals("") is None
        assert parse_goals("2") == 2
        assert parse_goals("1.0") == 1

    def test_time_and_money(self):
        """
        Scenario: kick-off times and FIFA money strings
          Given the time and money parsers
          When I parse "20:00:00" and "€110.5M"
          Then I receive "20:00" and 110500000
        """
        assert parse_time("20:00:00") == "20:00"
        assert parse_time("NA") is None
        assert parse_money("€110.5M") == 110_500_000
        assert parse_money("€565K") == 565_000
        assert parse_money("") is None
