"""Unit tests for team-name normalization."""

import pytest

from brazilian_soccer_mcp.normalization import (
    display_team,
    normalize_team,
    strip_accents,
    teams_equal,
)

# (raw spelling, expected canonical key) — the same club spelled the
# way each source dataset spells it must map to one canonical key.
SAME_CLUB_CASES = [
    ("Palmeiras-SP", "palmeiras"),
    ("Palmeiras", "palmeiras"),
    ("Atletico-MG", "atletico mineiro"),
    ("Atlético-MG", "atletico mineiro"),
    ("Atletico Mineiro", "atletico mineiro"),
    ("Athletico-PR", "athletico paranaense"),
    ("Atletico-PR", "athletico paranaense"),
    ("Athletico Paranaense", "athletico paranaense"),
    ("Sport-PE", "sport recife"),
    ("Sport", "sport recife"),
    ("Sport Club do Recife", "sport recife"),
    ("Sport Recife", "sport recife"),
    ("Vasco da Gama-RJ", "vasco da gama"),
    ("Vasco", "vasco da gama"),
    ("Vasco Da Gama RJ", "vasco da gama"),
    ("Gremio-RS", "gremio"),
    ("Grêmio", "gremio"),
    ("Gremio RS", "gremio"),
    ("Sao Paulo-SP", "sao paulo"),
    ("São Paulo", "sao paulo"),
    ("America-MG", "america mineiro"),
    ("América-MG", "america mineiro"),
    ("America MG", "america mineiro"),
    ("Botafogo-RJ", "botafogo"),
    ("Botafogo RJ", "botafogo"),
    ("Botafogo - RJ", "botafogo"),
    ("Nautico Capibaribe", "nautico"),
    ("Náutico", "nautico"),
    ("Nautico-PE", "nautico"),
    ("Red Bull Bragantino-SP", "red bull bragantino"),
    ("Bragantino", "red bull bragantino"),
    ("Bragantino - SP", "red bull bragantino"),
    ("Ceará", "ceara"),
    ("Ceara-CE", "ceara"),
    ("Ceará Sporting Club", "ceara"),
    ("EC Vitoria", "vitoria"),
    ("Vitória", "vitoria"),
    ("Vitoria-BA", "vitoria"),
    ("EC Bahia", "bahia"),
    ("Bahia-BA", "bahia"),
    ("Guarani", "guarani"),
    ("Guarani-SP", "guarani"),
    ("Guarani SP", "guarani"),
    ("4 de Julho EC", "4 de julho"),
    ("4 de Julho", "4 de julho"),
    ("Madureira EC", "madureira"),
    ("Madureira RJ", "madureira"),
    ("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista"),
    ("Boavista SC Saquarema", "boavista"),
    ("Boavista-RJ", "boavista"),
    ("Flamengo-RJ", "flamengo"),
    ("Flamengo", "flamengo"),
]

# Different clubs that share a base name must NOT be merged.
DISTINCT_CLUB_CASES = [
    ("Atletico-GO", "atletico goianiense"),
    ("Atletico - ES", "atletico es"),
    ("Atlético - AC", "atletico ac"),
    ("Botafogo PB", "botafogo pb"),
    ("Botafogo SP", "botafogo sp"),
    ("Fluminense PI", "fluminense pi"),
    ("Santos AP", "santos ap"),
    ("Guarani - CE", "guarani ce"),
    ("Guaraní (PAR)", "guarani par"),
    ("Guaraní-PAR", "guarani par"),
    ("Nacional (URU)", "nacional uru"),
    ("Nacional-URU", "nacional uru"),
    ("Nacional AM", "nacional am"),
    ("Peñarol", "penarol"),
    ("Penarol AM", "penarol am"),
    ("River Plate", "river plate"),
    ("River (PI)", "river pi"),
    ("Bragantino - PA", "bragantino pa"),
    ("Portuguesa RJ", "portuguesa rj"),
    ("Santa Cruz RN", "santa cruz rn"),
    ("Juventude MA", "juventude ma"),
    ("Grêmio Prudente", "gremio prudente"),
    ("Internacional-RS", "internacional"),
    ("Barcelona-EQU", "barcelona"),
]


@pytest.mark.parametrize("raw,expected", SAME_CLUB_CASES)
def test_same_club_variants_unify(raw, expected):
    assert normalize_team(raw) == expected


@pytest.mark.parametrize("raw,expected", DISTINCT_CLUB_CASES)
def test_distinct_clubs_stay_distinct(raw, expected):
    assert normalize_team(raw) == expected


def test_ambiguous_bases_do_not_merge():
    assert normalize_team("Atletico-MG") != normalize_team("Atletico-GO")
    assert normalize_team("Botafogo-RJ") != normalize_team("Botafogo PB")
    assert normalize_team("Guarani") != normalize_team("Guaraní (PAR)")


def test_strip_accents():
    assert strip_accents("São Paulo") == "Sao Paulo"
    assert strip_accents("Grêmio") == "Gremio"
    assert strip_accents("Avaí") == "Avai"


def test_display_team_known_and_fallback():
    assert display_team("gremio") == "Grêmio"
    assert display_team("atletico mineiro") == "Atlético Mineiro"
    assert display_team("sport recife") == "Sport Recife"
    assert display_team("csa") == "CSA"
    assert display_team("4 de julho") == "4 De Julho"


def test_teams_equal():
    assert teams_equal("Flamengo", "Flamengo-RJ")
    assert teams_equal("São Paulo", "Sao Paulo-SP")
    assert not teams_equal("Flamengo", "Fluminense")


def test_empty_and_garbage_input():
    assert normalize_team("") == ""
    assert normalize_team(None) == "none"  # documented: str() coercion
    assert teams_equal("", "Flamengo") is False
