"""BDD scenarios for match queries.

Feature: Match queries
  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  ... plus season filters, date ranges, finals, and head-to-head records.
"""

from __future__ import annotations

import re

SCORE_RE = re.compile(r"\d+-\d+")


class TestFindMatchesBetweenTwoTeams:
    def test_flu_flu_derby_matches_are_found(self, svc):
        # Given the match data is loaded
        # When I search for matches between "Flamengo" and "Fluminense"
        result = svc.search_matches(team="Flamengo", opponent="Fluminense")
        # Then I should receive a list of matches
        assert "found" in result
        count = int(re.search(r"(\d+) found", result).group(1))
        assert count >= 30
        # And each match line has date, scores, and competition
        lines = [ln for ln in result.splitlines() if ln.startswith("- ")]
        assert len(lines) >= 10
        for line in lines:
            assert SCORE_RE.search(line), line
            assert "(Brasileirão" in line or "(Copa" in line, line
        # And the head-to-head aggregate is included
        assert "Head-to-head in dataset" in result

    def test_matches_are_most_recent_first(self, svc):
        # Given matches spanning 2003-2023
        # When I search without filters
        # Then results are sorted by date descending
        result = svc.search_matches(
            team="Palmeiras", opponent="Santos", limit=5
        )
        years = [
            int(ln[2:6])
            for ln in result.splitlines()
            if ln.startswith("- ") and ln[2:6].isdigit()
        ]
        assert years == sorted(years, reverse=True)


class TestSeasonQueries:
    def test_palmeiras_2023_season(self, svc):
        # Given the merged datasets cover 2023 via the extended file
        # When I ask for Palmeiras matches in 2023
        result = svc.search_matches(team="Palmeiras", season=2023)
        # Then only 2023 matches come back, a full league season plus cups
        assert int(re.search(r"(\d+) found", result).group(1)) >= 30
        assert all(
            "2023" in ln or "date unknown" in ln
            for ln in result.splitlines()
            if ln.startswith("- ")
        )

    def test_2012_matches_come_from_the_primary_file(self, svc, dataset):
        # Given 2012 is covered by Brasileirao_Matches.csv
        # When I search that season
        # Then round labels are present
        result = svc.search_matches(competition="Brasileirão", season=2012, limit=3)
        assert "Round" in result


class TestDateRangeQueries:
    def test_date_range_filters_matches(self, svc):
        # Given matches across many dates
        # When I filter to a one-month window
        result = svc.search_matches(
            team="Flamengo", date_from="2019-11-01", date_to="2019-11-30"
        )
        # Then every returned match falls inside the window
        lines = [ln for ln in result.splitlines() if ln.startswith("- ")]
        assert lines
        for line in lines:
            assert line.startswith("- 2019-11-"), line

    def test_brazilian_date_format_is_accepted(self, svc):
        # Given dates in DD/MM/YYYY form
        # When used as a range bound
        result = svc.search_matches(team="Palmeiras", date_from="24/09/2023")
        # Then the filter still applies
        assert "found" in result
        lines = [ln for ln in result.splitlines() if ln.startswith("- ")]
        assert all(ln[2:6] == "2023" for ln in lines)


class TestFinalsQueries:
    def test_copa_do_brasil_finals_are_searchable(self, svc):
        # Given the cup rounds are numeric
        # When I search for the "final" stage
        result = svc.search_matches(
            competition="Copa do Brasil", stage="final", limit=30
        )
        # Then every season's final is returned
        assert int(re.search(r"(\d+) found", result).group(1)) >= 20
        assert "Final" in result
        # And the final does not accidentally match semifinals
        assert "Semifinals" not in result.split("By competition")[0]

    def test_libertadores_final_stage_does_not_match_semifinals(self, svc):
        # Given Libertadores stages include both "final" and "semifinals"
        # When I search for the final stage
        result = svc.search_matches(
            competition="Libertadores", stage="final", limit=30
        )
        # Then only final matches are returned (2013-2020: 2 legs or 1)
        count = int(re.search(r"(\d+) found", result).group(1))
        assert 10 <= count <= 16
        assert "Semifinals" not in result.split("By competition")[0]


class TestHeadToHead:
    def test_head_to_head_aggregate_sums_to_played_matches(self, svc, dataset):
        # Given the match data is loaded
        # When I request the Palmeiras x Santos head-to-head
        result = svc.head_to_head("Palmeiras", "Santos")
        # Then the aggregate wins/draws/losses sum to the played matches
        line = [ln for ln in result.splitlines() if ln.startswith("Head-to-head")][0]
        wins, draws, losses = map(
            int, re.findall(r"(\d+) wins", line) + re.findall(r"(\d+) draws", line)[:1]
        )
        played = sum(
            1
            for m in dataset.matches
            if {m.home.key, m.away.key} == {"palmeirassp", "santossp"} and m.played
        )
        assert wins + draws + losses == played

    def test_head_to_head_detects_derby_name(self, svc):
        # Given Fla-Flu is a registered derby
        # When I compare the two teams
        # Then the derby name appears in the title
        result = svc.head_to_head("Flamengo", "Fluminense")
        assert "Fla-Flu" in result.splitlines()[0]

    def test_head_to_head_can_be_scoped_to_a_competition(self, svc):
        # Given teams meet in several competitions
        # When I scope the comparison to the Brasileirão
        result = svc.head_to_head(
            "Flamengo", "Fluminense", competition="Brasileirão"
        )
        all_comps = svc.head_to_head("Flamengo", "Fluminense")
        scoped = int(re.search(r"(\d+) matches in dataset", result).group(1))
        total = int(re.search(r"(\d+) matches in dataset:", all_comps).group(1))
        # Then the scoped count is smaller than the overall count
        assert 0 < scoped < total


class TestUnplayedMatches:
    def test_unplayed_matches_are_reported_honestly(self, svc):
        # Given the 2022 Libertadores final has no score in the data
        # When I list Libertadores finals
        result = svc.search_matches(
            competition="Libertadores", stage="final", limit=20
        )
        # Then the unplayed final is marked as not recorded
        assert "not played/recorded" in result
