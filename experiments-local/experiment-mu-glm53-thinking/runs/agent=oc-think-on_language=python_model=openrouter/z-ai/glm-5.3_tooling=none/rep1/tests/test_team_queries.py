"""Feature: Team Queries

BDD scenarios for the TASK.md examples:
- "What is Corinthians' home record in 2022?"
- "Compare Palmeiras and Santos head-to-head"
- Team statistics: wins, losses, goals; performance by competition.
"""

from __future__ import annotations

from brazilian_soccer import queries as q


class TestGetTeamStatistics:
    """Feature: Team Queries - Scenario: Get team statistics."""

    def test_statistics_for_a_team_in_a_season(self, soccer):
        """Scenario: 'I request statistics for Palmeiras in season 2019'."""
        # Given the match data is loaded
        # When I request statistics for "Palmeiras" in season "2019"
        result = q.team_stats(soccer, "Palmeiras", season=2019)
        # Then I should receive wins, losses, draws, and goals
        record = result["record"]
        assert record["matches"] == 52  # Série A (38) + Libertadores (8) + Copa do Brasil (6)
        assert record["wins"] > record["losses"]
        assert record["goals_for"] > record["goals_against"]
        assert record["matches"] == record["wins"] + record["draws"] + record["losses"]

    def test_home_record_for_a_complete_season(self, soccer):
        """Scenario: 'What is Corinthians' home record in 2019?' (complete data)."""
        # Given the 2019 Brasileirão is fully recorded
        # When I request Corinthians' home record
        result = q.team_stats(
            soccer, "Corinthians", season=2019, venue="home", competition="Série A"
        )
        # Then I receive matches, wins, draws, losses, goals and win rate
        record = result["record"]
        assert record == {
            "matches": 19,
            "wins": 10,
            "draws": 7,
            "losses": 2,
            "goals_for": 25,
            "goals_against": 13,
            "win_rate": 52.6,
            "form_last_10": record["form_last_10"],
        }

    def test_home_record_for_an_incomplete_season_is_flagged(self, soccer):
        """Scenario: 'What is Corinthians' home record in 2022?' (data gap)."""
        # Given the 2022 dataset lacks scores for some late-season fixtures
        # When I request Corinthians' home record
        result = q.team_stats(
            soccer, "Corinthians", season=2022, venue="home", competition="Série A"
        )
        # Then only recorded matches count and the gap is disclosed
        assert result["record"]["matches"] == 15
        assert "no recorded score" in result["data_note"]

    def test_away_record(self, soccer):
        # Given the 2019 Brasileirão
        # When I request Flamengo's away record
        result = q.team_stats(
            soccer, "Flamengo", season=2019, venue="away", competition="Série A"
        )
        # Then the 2019 champions' away form is strong (best in the league)
        assert result["record"]["matches"] == 19
        assert result["record"]["wins"] == 11

    def test_breakdowns_when_no_season_given(self, soccer):
        # Given the match data is loaded
        # When I request Sport's overall statistics
        result = q.team_stats(soccer, "Sport")
        # Then per-season and per-competition breakdowns are included
        assert result["by_season"], "expected per-season breakdown"
        assert result["by_competition"], "expected per-competition breakdown"
        seasons = [row["season"] for row in result["by_season"]]
        assert 2012 in seasons and 2019 in seasons
        comps = {row["competition"] for row in result["by_competition"]}
        assert "Brasileirão Série A" in comps
        assert "Copa do Brasil" in comps


class TestCompareTeamsHeadToHead:
    """Feature: Team Queries - Scenario: 'Compare Palmeiras and Santos'."""

    def test_head_to_head_comparison(self, soccer):
        # Given the match data is loaded
        # When I compare Palmeiras and Santos
        result = q.head_to_head(soccer, "Palmeiras", "Santos")
        # Then I receive their full record and goal totals
        assert result["total_matches"] > 40
        record = result["record"]
        assert (
            record["Palmeiras_wins"] + record["Santos_wins"] + record["draws"]
            == result["total_matches"]
        )
        goals = result["goals"]
        assert goals["Palmeiras"] > 0 and goals["Santos"] > 0


class TestResolveTeam:
    """Feature: Team Queries - name variation handling."""

    def test_resolve_team_shows_all_spellings(self, soccer):
        # Given team names vary across files
        # When I resolve Corinthians
        result = q.resolve_team_info(soccer, "Corinthians")
        # Then the canonical club and every spelling variant are returned
        assert result["key"] == "corinthians"
        variant_names = [v["name"] for v in result["variants"]]
        assert "Corinthians-SP" in variant_names
        assert "Corinthians" in variant_names
        assert "novo_campeonato_brasileiro.csv" in result["sources"]
        assert result["matches_in_datasets"] > 500

    def test_uf_suffixed_input_resolves(self, soccer):
        # Given state-suffixed input
        # When resolved
        # Then it maps to the same club as the bare name
        assert soccer.resolve_team("Palmeiras-SP") == soccer.resolve_team("palmeiras")
        assert soccer.resolve_team("Atlético Paranaense") == soccer.resolve_team("Athletico-PR")


class TestClubOverview:
    """Feature: Team Queries - cross-file club profile."""

    def test_overview_joins_match_data_and_fifa_squad(self, soccer):
        # Given match data and the FIFA player database
        # When I request the Grêmio club overview
        result = q.club_overview(soccer, "Grêmio")
        # Then I receive competitions played, a record, and the squad
        assert "Brasileirão Série A" in result["competitions_played"]
        assert result["overall_record"]["matches"] > 600
        squad = result["fifa_squad"]
        assert squad["players"] == 20
        assert squad["avg_overall"] == 73.3
        assert squad["top_players"][0]["overall"] >= squad["top_players"][-1]["overall"]

    def test_overview_for_a_club_missing_from_fifa_discloses_it(self, soccer):
        # Given Flamengo is not in the FIFA dataset
        # When I request its club overview
        result = q.club_overview(soccer, "Flamengo")
        # Then the match record is present and the squad gap is disclosed
        assert result["overall_record"]["matches"] > 500
        assert result["fifa_squad"] is None
        assert "No FIFA-database players" in result["fifa_squad_note"]
