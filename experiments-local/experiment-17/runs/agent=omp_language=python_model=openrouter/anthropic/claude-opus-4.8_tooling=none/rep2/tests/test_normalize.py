"""
Context
=======
Module: tests.test_normalize
Purpose: Unit tests for team-name canonicalization — the foundation every
         cross-source query relies on. These are pure-function tests (no data
         load) covering suffix stripping, accent folding, identity vs base keys,
         and the bidirectional match predicate.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp import normalize as nz


class TestSuffixStripping:
    @pytest.mark.parametrize("raw,base,region", [
        ("Palmeiras-SP", "Palmeiras", "SP"),
        ("América - MG", "América", "MG"),
        ("Nacional (URU)", "Nacional", "URU"),
        ("Guaraní-PAR", "Guaraní", "PAR"),
        ("Flamengo", "Flamengo", None),
        ("Boca Juniors", "Boca Juniors", None),
    ])
    def test_split_suffix(self, raw, base, region):
        assert nz.split_suffix(raw) == (base, region)


class TestBaseKey:
    @pytest.mark.parametrize("raw,expected", [
        ("Grêmio-RS", "gremio"),
        ("Gremio", "gremio"),
        ("São Paulo-SP", "sao paulo"),
        ("Sao Paulo", "sao paulo"),
        ("ABC - RN", "abc"),
        ("Abc - RN", "abc"),
    ])
    def test_accent_and_case_fold_collapse(self, raw, expected):
        assert nz.base_key(raw) == expected

    def test_variants_share_base_key(self):
        # All spellings of São Paulo collapse to one base key.
        keys = {nz.base_key(x) for x in ("São Paulo", "Sao Paulo-SP", "SÃO PAULO")}
        assert keys == {"sao paulo"}


class TestTeamIdentityKey:
    def test_same_base_different_state_are_distinct(self):
        # The crucial invariant: the three Atléticos must NOT collapse, or
        # standings double-count their fixtures.
        mg = nz.team_key("Atletico-MG")
        pr = nz.team_key("Atletico-PR")
        go = nz.team_key("Atlético - GO")
        assert mg != pr != go
        assert {mg, pr, go} == {"atletico|mg", "atletico|pr", "atletico|go"}

    def test_accent_variants_share_identity(self):
        assert nz.team_key("Grêmio-RS") == nz.team_key("Gremio - RS") == "gremio|rs"


class TestMatchPredicate:
    def test_partial_name_matches_suffixed(self):
        assert nz.matches("Flamengo", "Flamengo-RJ")
        assert nz.matches("Palmeiras", "Palmeiras-SP")

    def test_accent_insensitive(self):
        assert nz.matches("Gremio", "Grêmio-RS")
        assert nz.matches("Sao Paulo", "São Paulo")

    def test_non_match(self):
        assert not nz.matches("Santos", "Flamengo-RJ")

    def test_empty_query_never_matches(self):
        assert not nz.matches("", "Flamengo-RJ")
