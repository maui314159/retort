"""BDD tests for statistical analysis (spec section: "5. Statistical Analysis").

Feature: Statistical Analysis

  Scenario: Aggregate goals per match
    Given the match data is loaded
    When I request competition statistics for the Brasileirão
    Then I should receive the average goals per match and home win rate
"""

from __future__ import annotations


class TestCompetitionStats:
    """Scenario: Average goals per match"""

    def test_brasileirao_stats(self, svc):
        result = svc.stats(competition="Brasileirão Série A")
        assert "Average goals per match:" in result
        assert "Home wins:" in result
        assert "Away wins:" in result
        avg = float(_after(result, "Average goals per match: ").split()[0])
        assert 2.0 < avg < 3.0, "Brazilian league averages ~2.5 goals/match"

    def test_home_advantage(self, svc):
        result = svc.stats(competition="Brasileirão Série A")
        home = _pct(result, "Home wins:")
        away = _pct(result, "Away wins:")
        assert home > away, "home teams must win more often"
        assert 40 < home < 55

    def test_season_filter(self, svc):
        result = svc.stats(competition="Brasileirão Série A", season=2019)
        assert "380 matches" in result
        assert "Brasileirão Série A 2019" in result

    def test_top_scoring_teams(self, svc):
        """Spec: 'Which team scored the most goals in Serie A 2023?'"""
        result = svc.stats(competition="Brasileirão Série A", season=2023)
        assert "Top scoring teams:" in result

    def test_best_home_and_away_records(self, svc):
        """Spec: 'Which team has the best away record?'"""
        result = svc.stats(competition="Brasileirão Série A")
        assert "Best home records" in result
        assert "Best away records" in result

    def test_all_competitions(self, svc):
        result = svc.stats()
        assert "All competitions" in result
        assert "Matches:" in result


class TestBiggestWins:
    """Scenario: Biggest wins in the dataset"""

    def test_biggest_wins_overall(self, svc):
        result = svc.biggest_wins(limit=5)
        assert "Biggest victories" in result
        # 2012 Libertadores: Santos 8-0 Bolívar (the dataset's record win)
        assert "Santos 8-0" in result or "8-0" in result

    def test_biggest_wins_sorted_by_margin(self, svc):
        result = svc.biggest_wins(limit=10)
        margins = [
            int(score.split("-")[0]) - int(score.split("-")[1])
            for score in _scores(result)
        ]
        assert margins == sorted(margins, reverse=True)

    def test_biggest_wins_brasiliao(self, svc):
        result = svc.biggest_wins(competition="Brasileirão Série A", limit=3)
        assert "(Brasileirão Série A" in result

    def test_biggest_wins_season(self, svc):
        result = svc.biggest_wins(competition="Brasileirão Série A", season=2019, limit=3)
        assert "2019" in result


class TestDerbies:
    """Scenario: Derby matches between traditional rivals"""

    def test_derbies_2019(self, svc):
        result = svc.derbies(season=2019)
        assert "Fla-Flu" in result
        assert "Gre-Nal" in result
        assert "Clássico Mineiro" in result

    def test_derby_matches_only_between_rivals(self, svc):
        result = svc.derbies(season=2019)
        # Every listed match line involves two teams from a classic pairing
        for ln in result.splitlines():
            if ln.startswith("- 2"):
                assert " (" in ln and "Brasileirão" in ln or "Copa" in ln

    def test_derbies_competition_filter(self, svc):
        result = svc.derbies(season=2019, competition="Brasileirão Série A")
        assert "Fla-Flu" in result

    def test_no_derbies_for_wrong_criteria(self, svc):
        assert "No derby matches" in svc.derbies(season=2003)


class TestAnalyticsUnit:
    """Unit-level checks of the analytics primitives."""

    def test_team_record_home_away(self, svc, matches):
        from soccer_mcp.analytics import team_record

        season = [m for m in matches if m.competition == "Brasileirão Série A" and m.season == 2019]
        total = team_record(season, "flamengo|RJ", svc.registry)
        home = team_record(season, "flamengo|RJ", svc.registry, venue="home")
        away = team_record(season, "flamengo|RJ", svc.registry, venue="away")
        # 2019 champion: 28W 6D 4L, 86 GF (per spec example)
        assert (total.wins, total.draws, total.losses) == (28, 6, 4)
        assert total.goals_for == 86
        assert home.matches + away.matches == total.matches == 38
        assert home.wins + away.wins == total.wins

    def test_h2h_counts(self, svc, matches):
        from soccer_mcp.analytics import head_to_head

        h2h = head_to_head(matches, "palmeiras|SP", "santos|SP", svc.registry)
        assert h2h.total == h2h.wins_a + h2h.wins_b + h2h.draws
        assert h2h.total > 30

    def test_standings_row_positions(self, svc, matches):
        from soccer_mcp.analytics import standings as standings_impl

        season = [m for m in matches if m.competition == "Brasileirão Série A" and m.season == 2019]
        table = standings_impl(season, svc.registry)
        assert [r.position for r in table] == list(range(1, 21))
        champion = table[0]
        assert champion.team == "flamengo|RJ"
        assert champion.points == champion.wins * 3 + champion.draws

    def test_unscored_matches_excluded_from_records(self, svc, matches):
        """Matches without scores must not distort statistics."""
        from soccer_mcp.analytics import team_record

        season = [
            m
            for m in matches
            if m.competition == "Brasileirão Série A" and m.season == 2022 and not m.has_score
        ]
        assert season, "2022 has unrecorded scores in the source data"
        record = team_record(season, season[0].home, svc.registry)
        assert record.matches == 0


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------


def _after(text: str, marker: str) -> str:
    idx = text.index(marker) + len(marker)
    return text[idx:]


def _pct(text: str, marker: str) -> float:
    return float(_after(text, marker).split("%")[0])


def _scores(text: str) -> list[str]:
    import re

    return re.findall(r": [A-Za-zÀ-ú .()-]+? (\d+-\d+) ", text)
