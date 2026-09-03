"""BDD tests for the data loader.

Feature: Data Loading

  Scenario: All six Kaggle CSV files load into the in-memory knowledge graph
    Given the bundled ``data/kaggle`` datasets
    When the loader is run
    Then matches are loaded from the five match CSVs
    And FIFA players are loaded from ``fifa_data.csv``
    And overlapping cross-source fixtures are de-duplicated
    And every team has a registered display name
"""

from __future__ import annotations

from brazilian_soccer_mcp.data_loader import DATA_DIR


def test_all_six_files_present_on_disk():
    import os
    expected = [
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
        "fifa_data.csv",
    ]
    for name in expected:
        assert os.path.exists(os.path.join(DATA_DIR, name)), f"missing {name}"


def test_matches_loaded_from_all_five_match_files(data):
    sources = {m.source for m in data.matches}
    for name in (
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
    ):
        assert name in sources, f"no matches loaded from {name}"
    assert len(data.matches) > 15_000


def test_fifa_players_loaded(data):
    assert len(data.players) > 15_000
    nationalities = {p.nationality for p in data.players}
    assert "Brazil" in nationalities


def test_teams_have_display_names(data):
    for key, display in data.team_display.items():
        assert display, f"empty display for {key!r}"
    assert data.display_name("flamengo") == "Flamengo"
    assert data.display_name("palmeiras") == "Palmeiras"


def test_no_duplicate_matches_after_dedupe(data):
    seen = set()
    dupes = 0
    for m in data.matches:
        key = (m.season, m.home, m.away, m.home_goal, m.away_goal)
        if key in seen:
            dupes += 1
        seen.add(key)
    assert dupes == 0


def test_all_goals_are_integers(data):
    for m in data.matches:
        assert isinstance(m.home_goal, int)
        assert isinstance(m.away_goal, int)
        assert m.home_goal >= 0 and m.away_goal >= 0
