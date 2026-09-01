"""Tests for text, team-name, date, and number normalization (R2 prerequisites)."""

from brazilian_soccer_mcp.normalize import (
    DERBIES,
    club_alias,
    derby_name,
    identity_key,
    parse_date,
    parse_int,
    parse_money,
    parse_season,
    strip_accents,
    strip_team_suffix,
    team_key,
    text_key,
)


class TestTextKeys:
    def test_strip_accents(self):
        assert strip_accents("São Paulo") == "Sao Paulo"
        assert strip_accents("Grêmio") == "Gremio"
        assert strip_accents("Avaí") == "Avai"

    def test_text_key_case_and_punctuation(self):
        assert text_key("Atlético - PR") == "atletico pr"
        assert text_key("Nacional (URU)") == "nacional uru"
        assert text_key("  São   PAULO ") == "sao paulo"

    def test_text_key_utf8_input(self):
        assert text_key("Fortaleza Esporte Clube") == "fortaleza esporte clube"


class TestTeamNames:
    def test_state_suffix_stripped(self):
        base, code = strip_team_suffix("Palmeiras-SP")
        assert base == "Palmeiras"
        assert code == "SP"

    def test_parenthesised_country_code(self):
        base, code = strip_team_suffix("Nacional (URU)")
        assert base == "Nacional"
        assert code == "URU"

    def test_normalize_state_suffix(self):
        assert team_key("Palmeiras-SP") == team_key("Palmeiras")
        assert team_key("Flamengo-RJ") == team_key("Flamengo")

    def test_normalize_missing_accents(self):
        assert team_key("Sao Paulo") == team_key("São Paulo")
        assert team_key("Gremio") == team_key("Grêmio")
        assert team_key("avai") == team_key("Avaí")

    def test_normalize_known_aliases(self):
        assert team_key("Athletico-PR") == team_key("Athletico Paranaense")
        assert team_key("Atletico MG") == team_key("Atlético Mineiro")
        assert team_key("Vasco") == team_key("Vasco da Gama")

    def test_identity_ignores_generic_suffixes(self):
        assert identity_key("Fortaleza FC") == identity_key("Fortaleza")
        assert identity_key("Fortaleza Esporte Clube") == identity_key("Fortaleza")
        assert identity_key("SC Internacional") == identity_key("Internacional")

    def test_identity_does_not_merge_distinct_teams(self):
        assert identity_key("Santos") != identity_key("São Paulo")
        assert identity_key("Botafogo") != identity_key("Botafogo-PB")


class TestDerbies:
    def test_known_derby_either_order(self):
        assert derby_name("Flamengo", "Fluminense") == "Fla-Flu"
        assert derby_name("Fluminense", "Flamengo") == "Fla-Flu"
        assert derby_name("Grêmio", "Internacional") == "Gre-Nal"
        assert derby_name("Internacional", "Grêmio") == "Gre-Nal"

    def test_reordered_entries_still_match(self):
        # ("Flamengo", "Botafogo") was historically stored unsorted.
        assert derby_name("Flamengo", "Botafogo") == "Clássico da Rivalidade"
        assert derby_name("Botafogo", "Flamengo") == "Clássico da Rivalidade"

    def test_all_derby_keys_are_sorted(self):
        for pair in DERBIES:
            assert pair == tuple(sorted(pair)), pair

    def test_non_derby_returns_none(self):
        assert derby_name("Flamengo", "Cruzeiro") is None


class TestDates:
    def test_iso_date(self):
        assert parse_date("2023-09-24").isoformat() == "2023-09-24"

    def test_iso_datetime(self):
        assert parse_date("2012-05-19 18:30:00").isoformat() == "2012-05-19"

    def test_brazilian_format(self):
        assert parse_date("29/03/2003").isoformat() == "2003-03-29"

    def test_brazilian_datetime(self):
        assert parse_date("24/09/2023 16:00:00").isoformat() == "2023-09-24"

    def test_missing_values(self):
        assert parse_date(None) is None
        assert parse_date("") is None
        assert parse_date("NA") is None


class TestNumbers:
    def test_parse_int(self):
        assert parse_int("2") == 2
        assert parse_int(3.0) == 3
        assert parse_int(None) is None
        assert parse_int("NA") is None
        assert parse_int("D") is None

    def test_parse_season(self):
        assert parse_season("2019") == 2019
        assert parse_season(2019) == 2019
        assert parse_season("NA") is None

    def test_parse_money(self):
        assert parse_money("€110.5M") == 110_500_000.0
        assert parse_money("€565K") == 565_000.0
        assert parse_money("€1M") == 1_000_000.0
        assert parse_money(None) is None


class TestClubAlias:
    def test_fifa_formal_spellings(self):
        assert club_alias("Sport Club do Recife") == "Sport Recife"
        assert club_alias("América FC (Minas Gerais)") == "América Mineiro"
        assert club_alias("Ceará Sporting Club") == "Ceará"
        assert club_alias("Atlético Paranaense") == "Athletico Paranaense"

    def test_unknown_club_returns_none(self):
        assert club_alias("Manchester United") is None
        assert club_alias("") is None
