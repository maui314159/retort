"""Tests for competition standings (R9) and season summaries."""

from collections import defaultdict

from brazilian_soccer_mcp.queries import QueryEngine


class TestStandings:
    def test_2019_champion(self, engine: QueryEngine):
        result = engine.get_standings(competition="Brasileirão", season=2019)
        top = result["standings"][0]
        assert top["team"] == "Flamengo"
        assert top["points"] == 90
        assert top["note"] == "Champion"

    def test_standings_computed_from_matches(self, engine, dataset):
        """Recompute the table independently and compare with the tool."""
        result = engine.get_standings(competition="Brasileirão", season=2018)
        table: dict[str, dict] = defaultdict(
            lambda: {"played": 0, "wins": 0, "draws": 0, "losses": 0,
                     "goals_for": 0, "goals_against": 0}
        )
        for match in dataset.matches:
            if (match.competition != "Brasileirão" or match.season != 2018
                    or match.home_goals is None or match.away_goals is None):
                continue
            home, away = table[match.home_team], table[match.away_team]
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += match.home_goals
            home["goals_against"] += match.away_goals
            away["goals_for"] += match.away_goals
            away["goals_against"] += match.home_goals
            if match.home_goals > match.away_goals:
                home["wins"] += 1
                away["losses"] += 1
            elif match.home_goals < match.away_goals:
                away["wins"] += 1
                home["losses"] += 1
            else:
                home["draws"] += 1
                away["draws"] += 1

        computed = {
            team: 3 * row["wins"] + row["draws"] for team, row in table.items()
        }
        returned = {
            row["team"]: row["points"] for row in result["standings"]
        }
        assert returned == computed
        assert len(returned) == 20

    def test_points_formula_and_ordering(self, engine):
        result = engine.get_standings(competition="Brasileirão", season=2019)
        standings = result["standings"]
        points = [row["points"] for row in standings]
        assert points == sorted(points, reverse=True)
        for row in standings:
            assert row["points"] == 3 * row["wins"] + row["draws"]
            assert row["goal_difference"] == row["goals_for"] - row["goals_against"]
        assert [row["position"] for row in standings] == list(
            range(1, len(standings) + 1)
        )

    def test_complete_season_flag(self, engine):
        result = engine.get_standings(competition="Brasileirão", season=2019)
        assert result["table_complete"] is True
        assert result["note"] is None
        played = {row["played"] for row in result["standings"]}
        assert played == {38}

    def test_relegation_note_on_20_team_season(self, engine):
        result = engine.get_standings(competition="Brasileirão", season=2019)
        bottom_four = result["standings"][-4:]
        assert all(row["note"] == "Relegation zone" for row in bottom_four)

    def test_serie_b_standings(self, engine):
        result = engine.get_standings(competition="Serie B", season=2019)
        assert result["standings"][0]["team"] == "Red Bull Bragantino"

    def test_season_without_matches_errors(self, engine):
        result = engine.get_standings(competition="Brasileirão", season=1900)
        assert "error" in result

    def test_played_consistency(self, engine):
        result = engine.get_standings(competition="Brasileirão", season=2019)
        for row in result["standings"]:
            assert row["played"] == row["wins"] + row["draws"] + row["losses"]


class TestSeasonSummaries:
    def test_season_summary_2019(self, engine):
        result = engine.get_season_summary(season=2019)
        assert result["season"] == 2019
        assert "Brasileirão" in result["competitions"]
        stats = result["competitions"]["Brasileirão"]
        assert stats["matches"] > 300
        assert 1.5 < stats["avg_goals_per_match"] < 4.0
        assert result["champions"]["Brasileirão"]["team"] == "Flamengo"

    def test_compare_seasons(self, engine):
        result = engine.compare_seasons(season_a=2018, season_b=2019)
        assert result["season_a"]["season"] == 2018
        assert result["season_b"]["season"] == 2019
        for side in ("season_a", "season_b"):
            assert result[side]["competitions"]
