"""Data coverage tests: all six CSV files load and are queryable.

Spec success criteria: 'All 6 CSV files are loadable and queryable'.
"""


from brasil_mcp.loaders import (
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_A,
    load_br_football,
    load_brasileirao,
    load_copa_do_brasil,
    load_fifa,
    load_historico,
    load_libertadores,
)
from brasil_mcp.normalize import TeamRegistry
from brasil_mcp.store import SERIE_B, SERIE_C, SoccerStore, default_data_dir

DATA_DIR = default_data_dir()

EXPECTED_ROWS = {
    "Brasileirao_Matches.csv": 4180,
    "Brazilian_Cup_Matches.csv": 1337,
    "Libertadores_Matches.csv": 1255,
    "BR-Football-Dataset.csv": 10296,
    "novo_campeonato_brasileiro.csv": 6886,
    "fifa_data.csv": 18207,
}


def _registry():
    registry = TeamRegistry()
    import csv

    for filename, columns in (
        ("Brasileirao_Matches.csv", ("home_team", "away_team")),
        ("Brazilian_Cup_Matches.csv", ("home_team", "away_team")),
        ("Libertadores_Matches.csv", ("home_team", "away_team")),
        ("BR-Football-Dataset.csv", ("home", "away")),
        ("novo_campeonato_brasileiro.csv", ("Equipe_mandante", "Equipe_visitante")),
    ):
        with open(DATA_DIR / filename, encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                for column in columns:
                    registry.observe(row[column].strip())
    registry.finalize()
    return registry


def test_all_files_have_expected_row_counts():
    registry = _registry()
    counts = {
        "Brasileirao_Matches.csv": len(
            load_brasileirao(DATA_DIR / "Brasileirao_Matches.csv", registry)
        ),
        "Brazilian_Cup_Matches.csv": len(
            load_copa_do_brasil(DATA_DIR / "Brazilian_Cup_Matches.csv", registry)
        ),
        "Libertadores_Matches.csv": len(
            load_libertadores(DATA_DIR / "Libertadores_Matches.csv", registry)
        ),
        "BR-Football-Dataset.csv": len(
            load_br_football(DATA_DIR / "BR-Football-Dataset.csv", registry)
        ),
        "novo_campeonato_brasileiro.csv": len(
            load_historico(DATA_DIR / "novo_campeonato_brasileiro.csv", registry)
        ),
        "fifa_data.csv": len(load_fifa(DATA_DIR / "fifa_data.csv", registry)),
    }
    assert counts == EXPECTED_ROWS


def test_loader_competitions():
    registry = _registry()
    bras = load_brasileirao(DATA_DIR / "Brasileirao_Matches.csv", registry)
    assert {m.competition for m in bras} == {SERIE_A}
    cup = load_copa_do_brasil(DATA_DIR / "Brazilian_Cup_Matches.csv", registry)
    assert {m.competition for m in cup} == {COPA_DO_BRASIL}
    lib = load_libertadores(DATA_DIR / "Libertadores_Matches.csv", registry)
    assert {m.competition for m in lib} == {LIBERTADORES}
    brf = load_br_football(DATA_DIR / "BR-Football-Dataset.csv", registry)
    assert {m.competition for m in brf} == {SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL}


def test_loader_handles_special_values():
    registry = _registry()
    lib = load_libertadores(DATA_DIR / "Libertadores_Matches.csv", registry)
    abandoned = [m for m in lib if not m.played]
    assert abandoned, "the abandoned Boca x River 2015 tie should load without a result"
    assert all(m.home_goals is None for m in abandoned)

    novo = load_historico(DATA_DIR / "novo_campeonato_brasileiro.csv", registry)
    assert all(m.date is not None for m in novo)
    assert any(m.venue for m in novo), "historico loader should carry stadium names"


def test_utf8_names_survive_loading():
    registry = _registry()
    novo = load_historico(DATA_DIR / "novo_campeonato_brasileiro.csv", registry)
    displays = {m.home_display for m in novo}
    assert any("Goiás" in d for d in displays)
    lib = load_libertadores(DATA_DIR / "Libertadores_Matches.csv", registry)
    assert any("Grêmio" in m.home_display for m in lib)


def test_store_deduplicates_cross_file_matches(store: SoccerStore):
    """Overlapping seasons across files must be merged, not double-counted.

    Every Série A season 2006-2022 has exactly 380 matches. 2015 has 381
    because the source BR-Football file contains one regional fixture
    (Brasilia FC x CA Taguatinga, Jan 2016) mislabeled as 'Serie A'; the
    standings calculation filters such one-off teams out.
    """
    serie_a_per_season = {}
    for match in store.matches:
        if match.competition == SERIE_A and match.season:
            serie_a_per_season[match.season] = serie_a_per_season.get(match.season, 0) + 1
    for season in range(2006, 2023):
        expected = 381 if season == 2015 else 380
        assert serie_a_per_season[season] == expected, (
            f"{season} should have exactly {expected} matches"
        )
    assert serie_a_per_season[2003] == 552
    assert serie_a_per_season[2005] == 462


def test_store_has_players_and_matches(store: SoccerStore):
    assert len(store.players) == EXPECTED_ROWS["fifa_data.csv"]
    assert len(store.matches) > 15000
    assert store.duplicate_count > 5000, "cross-file duplicates should be merged"


def test_competitions_summary_covers_all_trophies(store: SoccerStore):
    rows = {row["competition"]: row for row in store.competitions_summary()}
    assert set(rows) == {SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES}
    assert rows[SERIE_A]["matches"] > 8000
    assert rows[COPA_DO_BRASIL]["matches"] > 1500
    assert rows[LIBERTADORES]["matches"] > 1200
