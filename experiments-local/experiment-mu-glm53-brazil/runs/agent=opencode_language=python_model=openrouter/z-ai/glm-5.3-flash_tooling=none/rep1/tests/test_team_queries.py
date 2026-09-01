"""Tests for team queries (R6) and head-to-head (R11)."""



class TestTeamStats:
    def test_record_structure(self, engine):
        result = engine.get_team_stats(team="Corinthians")
        record = result["record"]
        assert result["team"] == "Corinthians"
        assert record["played"] == (
            record["wins"] + record["draws"] + record["losses"]
        )
        assert record["played"] > 100
        assert record["goals_for"] > 0
        assert record["goals_against"] > 0
        assert 0 <= record["win_rate"] <= 100

    def test_record_matches_manual_computation(self, engine, dataset):
        canonical = dataset.resolve_team("Santos")
        expected = {"played": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0}
        for match in dataset.matches:
            if match.home_goals is None or match.away_goals is None:
                continue
            if match.home_team == canonical:
                gf, ga = match.home_goals, match.away_goals
            elif match.away_team == canonical:
                gf, ga = match.away_goals, match.home_goals
            else:
                continue
            expected["played"] += 1
            expected["goals_for"] += gf
            expected["goals_against"] += ga
            if gf > ga:
                expected["wins"] += 1
            elif gf < ga:
                expected["losses"] += 1
            else:
                expected["draws"] += 1
        result = engine.get_team_stats(team="Santos")["record"]
        expected_rate = round(expected["wins"] / expected["played"] * 100, 1)
        assert result["played"] == expected["played"]
        assert result["wins"] == expected["wins"]
        assert result["draws"] == expected["draws"]
        assert result["losses"] == expected["losses"]
        assert result["goals_for"] == expected["goals_for"]
        assert result["goals_against"] == expected["goals_against"]
        assert result["win_rate"] == expected_rate

    def test_competition_and_season_filters(self, engine):
        result = engine.get_team_stats(
            team="Corinthians", competition="Brasileirão", season=2022
        )
        record = result["record"]
        assert record["played"] > 0
        assert record["played"] == record["wins"] + record["draws"] + record["losses"]

    def test_venue_filter(self, engine):
        all_games = engine.get_team_stats(team="Corinthians", season=2022)
        home = engine.get_team_stats(
            team="Corinthians", season=2022, venue="home"
        )
        away = engine.get_team_stats(team="Corinthians", season=2022, venue="away")
        assert home["record"]["played"] + away["record"]["played"] == all_games["record"]["played"]
        assert home["record"]["played"] > 0
        assert away["record"]["played"] > 0

    def test_win_rate_consistent(self, engine):
        home = engine.get_team_stats(team="Corinthians", season=2022, venue="home")
        record = home["record"]
        expected_rate = round(record["wins"] / record["played"] * 100, 1)
        assert record["win_rate"] == expected_rate

    def test_seasons_and_competitions_played(self, engine):
        result = engine.get_team_stats(team="Flamengo")
        assert "Brasileirão" in result["competitions_played"]
        assert 2019 in result["seasons_played"]


class TestHeadToHead:
    def test_h2h_record(self, engine):
        result = engine.head_to_head(team_a="Palmeiras", team_b="Santos")
        record = result["record"]
        total = record["team_a_wins"] + record["team_b_wins"] + record["draws"]
        assert total > 20
        assert result["last_meeting"]

    def test_h2h_symmetric(self, engine):
        ab = engine.head_to_head(team_a="Flamengo", team_b="Corinthians")["record"]
        ba = engine.head_to_head(team_a="Corinthians", team_b="Flamengo")["record"]
        assert ab["team_a_wins"] == ba["team_b_wins"]
        assert ab["team_b_wins"] == ba["team_a_wins"]
        assert ab["draws"] == ba["draws"]

    def test_h2h_detects_derby(self, engine):
        result = engine.head_to_head(team_a="Flamengo", team_b="Fluminense")
        assert result["derby"] == "Fla-Flu"

    def test_h2h_recent_matches(self, engine):
        result = engine.head_to_head(team_a="Grêmio", team_b="Internacional")
        assert 0 < len(result["recent_matches"]) <= 5
        for match in result["recent_matches"]:
            assert {match["home_team"], match["away_team"]} == {"Grêmio", "Internacional"}


class TestTeamCompetitions:
    def test_competitions_cross_file(self, engine):
        result = engine.get_team_competitions(team="Palmeiras")
        assert result["total_matches"] > 0
        competitions = result["competitions"]
        assert "Brasileirão" in competitions
        assert competitions["Brasileirão"]["matches"] > 0
        seasons = competitions["Brasileirão"]["seasons"]
        assert seasons == sorted(seasons)

    def test_cup_and_libertadores_appear(self, engine):
        result = engine.get_team_competitions(team="Flamengo")
        assert set(result["competitions"]) & {"Copa do Brasil", "Libertadores"}
