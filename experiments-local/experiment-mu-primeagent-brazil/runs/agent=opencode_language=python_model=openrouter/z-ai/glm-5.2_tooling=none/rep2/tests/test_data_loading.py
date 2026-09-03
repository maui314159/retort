"""BDD tests: all six bundled CSV files are loadable and queryable.

Feature: Data Loading
  Given the data directory under data/kaggle
  When the loader runs
  Then all six CSV files are loaded into a unified schema and every row carries
  the canonical team keys.
"""
from __future__ import annotations

from brsl import data_loader as dl


class TestDataLoading:
    # Scenario: every match file is represented in the unified frame
    def test_all_five_match_files_present(self, matches_df):
        sources = set(matches_df["source"].unique())
        expected = {"brasileirao", "copa_do_brasil", "libertadores",
                    "br_football", "historico"}
        assert expected <= sources

    def test_unified_match_schema(self, matches_df):
        required = ["date", "home_team", "away_team", "home_goal",
                    "away_goal", "competition", "season", "home_team_key",
                    "away_team_key", "winner"]
        for col in required:
            assert col in matches_df.columns, f"missing {col}"

    def test_match_row_counts_reasonable(self, matches_df):
        # The dataset should contain tens of thousands of matches.
        assert len(matches_df) > 20000

    def test_deduplication_removes_cross_file_duplicates(self, deduped_df):
        # The deduplicated frame must be strictly smaller than the raw union
        # because many matches appear in more than one file.
        raw = dl.load_matches()
        assert len(deduped_df) < len(raw)
        assert len(deduped_df) > 15000

    def test_fifa_player_database_loads(self, players_df):
        assert "Name" in players_df.columns
        assert "Nationality" in players_df.columns
        assert "Club" in players_df.columns
        assert len(players_df) > 18000

    def test_brazilian_players_present(self, players_df):
        braz = players_df[players_df["Nationality"].astype(str).str.contains(
            "Brazil", case=False)]
        assert len(braz) > 500

    def test_dates_are_parsed(self, matches_df):
        # Both ISO ("2012-05-19 18:30:00") and Brazilian ("29/03/2003")
        # formats must parse into real datetimes.
        assert matches_df["date"].notna().sum() > 20000

    def test_goals_are_numeric(self, matches_df):
        scored = matches_df[(matches_df["home_goal"].notna())
                            & (matches_df["away_goal"].notna())]
        assert (scored["home_goal"] >= 0).all()
        assert (scored["away_goal"] >= 0).all()
