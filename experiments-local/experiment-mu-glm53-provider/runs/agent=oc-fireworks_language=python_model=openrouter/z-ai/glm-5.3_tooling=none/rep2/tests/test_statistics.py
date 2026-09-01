"""BDD scenarios for statistical analysis.

Feature: Statistical analysis
  Scenario: Rank the biggest wins
    Given the match data is loaded
    When I ask for the biggest victories
    Then matches are ranked by descending goal margin
"""

from __future__ import annotations

import re

from brazilian_soccer.models import Match


def _margins(text: str) -> list[int]:
    return [
        abs(int(a) - int(b))
        for a, b in re.findall(
            r"\d{4}-\d{2}-\d{2}: .+? (\d+)-(\d+) ", text
        )
    ]


class TestBiggestWins:
    def test_ranked_by_descending_margin(self, svc):
        # Given all played matches
        # When I ask for the biggest victories
        result = svc.biggest_wins(limit=10)
        # Then margins are non-increasing and the top is huge
        margins = _margins(result)
        assert len(margins) == 10
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 8

    def test_competition_filter_applies(self, svc):
        # Given matches from many competitions
        # When I filter to the Brasileirão
        result = svc.biggest_wins(competition="Brasileirão", limit=10)
        # Then every line is a Serie A match
        assert "(Brasileirão Serie A)" in result
        assert "(Copa" not in result

    def test_season_filter_applies(self, svc):
        # Given matches from many seasons
        # When I filter to 2019
        result = svc.biggest_wins(season=2019, limit=5)
        # Then only 2019 matches are listed
        assert re.search(r"Biggest victories \(all competitions 2019\)", result)
        for line in result.splitlines():
            if line[0].isdigit():
                assert "2019-" in line


class TestGoalAverages:
    def test_average_goals_per_match_is_sane(self, svc):
        # Given all Brasileirão matches
        # When I compute competition statistics
        result = svc.competition_info("Brasileirão")
        # Then the average is a plausible per-match figure
        avg = float(re.search(r"Average goals per match: ([\d.]+)", result).group(1))
        assert 2.0 < avg < 3.0

    def test_total_goals_matches_match_count(self, svc, dataset):
        # Given the Libertadores matches
        # When I compute competition statistics
        result = svc.competition_info("Libertadores")
        # Then the reported rates are consistent with the match data
        played = sum(
            1 for m in dataset.matches
            if m.competition == "libertadores" and m.played
        )
        assert f"Matches played: {played}" in result


class TestHomeAdvantage:
    def test_home_wins_exceed_away_wins(self, svc):
        # Given two decades of matches
        # When I compute result rates
        result = svc.competition_info("Brasileirão")
        # Then home teams win clearly more often than away teams
        home = float(re.search(r"Home wins: \d+ \(([\d.]+)%\)", result).group(1))
        away = float(re.search(r"Away wins: \d+ \(([\d.]+)%\)", result).group(1))
        assert home > away + 10

    def test_team_home_form_beats_away_form_for_a_champion(self, svc):
        # Given Flamengo's 2019 championship season
        # When I split its record by venue
        home = svc.team_stats("Flamengo", season=2019, competition="Brasileirão", venue="home")
        away = svc.team_stats("Flamengo", season=2019, competition="Brasileirão", venue="away")
        # Then home form is stronger
        home_rate = float(re.search(r"Win rate: ([\d.]+)%", home).group(1))
        away_rate = float(re.search(r"Win rate: ([\d.]+)%", away).group(1))
        assert home_rate > away_rate


class TestHeadToHeadMath:
    def test_gre_nal_aggregate_is_consistent(self, svc):
        # Given the Gre-Nal derby matches
        # When I request the derby record
        result = svc.derby_matches("Gre-Nal")
        # Then wins + draws + losses equals the match count
        h2h = [ln for ln in result.splitlines() if ln.startswith("Head-to-head")][0]
        numbers = [int(n) for n in re.findall(r"\b(\d+)\b", h2h)]
        total = int(re.search(r"(\d+) matches in dataset", result).group(1))
        assert sum(numbers) == total

    def test_match_result_method_agrees_with_goals(self, dataset):
        # Given any played match
        # When result_for() is evaluated for both teams
        # Then the two results are complementary
        played = [
            m for m in dataset.matches
            if m.competition == "brasileirao" and m.played and m.season == 2019
        ]
        for match in played[:100]:
            home_result = match.result_for(match.home.key)
            away_result = match.result_for(match.away.key)
            assert {home_result, away_result} in ({"W", "L"}, {"D", "D"})


class TestDerbies:
    def test_listing_all_derbies(self, svc):
        # Given the derby registry
        # When I list derbies without a name
        result = svc.derby_matches()
        # Then every known derby appears with a match count
        for name in ("Fla-Flu", "Gre-Nal", "Derby Paulista", "Ba-Vi", "Atletiba"):
            assert name in result
        assert re.search(r"Fla-Flu.*\d+ matches in dataset", result)

    def test_derby_in_one_season(self, svc):
        # Given derbies across many seasons
        # When I scope to 2023
        result = svc.derby_matches(derby="Derby Paulista", season=2023)
        # Then only 2023 matches are returned
        assert "2023" in result
        for line in result.splitlines():
            if line.startswith("- "):
                assert "2023" in line

    def test_unknown_derby_lists_known_ones(self, svc):
        # Given an unrecognized derby name
        # When I ask for it
        result = svc.derby_matches(derby="El Clásico")
        # Then the known derbies are offered
        assert "not found" in result
        assert "Fla-Flu" in result


class TestMatchModel:
    def test_match_describe_includes_all_required_fields(self, dataset):
        # Given a played Brasileirão match
        # When described in one line
        played = [
            m for m in dataset.matches
            if m.competition == "brasileirao" and m.played and m.round_label
        ]
        match = played[0]
        line = match.describe(include_stats=False)
        # Then date, both teams, the score and the competition appear
        assert match.date.isoformat() in line
        assert match.home.display in line and match.away.display in line
        assert f"{match.home_goals}-{match.away_goals}" in line
        assert match.competition_display in line

    def test_unplayed_match_is_flagged(self):
        # Given a match without scores
        from brazilian_soccer.models import TeamRef

        match = Match(
            competition="libertadores",
            competition_display="Copa Libertadores",
            season=2022,
            date=None,
            time=None,
            home=TeamRef("flamengorj", "Flamengo"),
            away=TeamRef("atleticopr", "Atlético-PR"),
        )
        # When asked whether it was played
        # Then False comes back
        assert match.played is False
        assert "not played/recorded" in match.describe()
