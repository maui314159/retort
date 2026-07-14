from brazilian_soccer_mcp import QueryEngine


def test_team_statistics_structure(engine):
    """Feature: Team Queries
    Scenario: get team statistics
      Given the match data is loaded
      When I request statistics for "Palmeiras" in season "2023"
      Then I should receive wins, losses, draws, and goals
    """
    s = engine.team_statistics("Palmeiras", season=2023, competition="Brasileirao")
    d = s.to_dict()
    assert d["matches"] > 0
    assert d["wins"] + d["draws"] + d["losses"] == d["matches"]
    assert d["goals_for"] >= 0 and d["goals_against"] >= 0
    assert 0.0 <= d["win_rate"] <= 1.0


def test_home_record_2022(engine):
    """Scenario: Corinthians home record in 2022
      When I request Corinthians home record for 2022 Brasileirao
      Then the matches count equals wins+draws+losses and all are home
    """
    s = engine.team_statistics("Corinthians", season=2022, competition="Brasileirao", home_away="home")
    assert s.home_away == "home"
    assert s.wins + s.draws + s.losses == s.matches
    assert s.matches > 0


def test_team_statistics_home_vs_away(engine):
    """Scenario: home record stronger than away record
      When I compute overall vs home vs away stats
      Then home+away match counts sum to overall
    """
    overall = engine.team_statistics("Flamengo", season=2019, competition="Brasileirao")
    home = engine.team_statistics("Flamengo", season=2019, competition="Brasileirao", home_away="home")
    away = engine.team_statistics("Flamengo", season=2019, competition="Brasileirao", home_away="away")
    assert home.matches + away.matches == overall.matches
    assert home.wins >= away.wins


def test_head_to_head(engine):
    """Scenario: compare Palmeiras and Santos head-to-head
      When I request head-to-head
      Then wins+draws+losses equals the number of matches
    """
    h2h = engine.head_to_head("Palmeiras", "Santos")
    d = h2h.to_dict()
    assert d["team_a_wins"] + d["team_b_wins"] + d["draws"] == len(d["matches"])
    assert d["team_a_id"] == "palmeiras" and d["team_b_id"] == "santos"


def test_most_goals_scored(engine):
    """Scenario: which team scored the most goals in Serie A 2023
      When I request most goals scored for Brasileirao 2023
      Then I get a ranked list with goals
    """
    rows = engine.most_goals_scored(competition="Brasileirao", season=2023, limit=5)
    assert len(rows) == 5
    assert rows[0]["goals"] >= rows[-1]["goals"]
    assert all("team_name" in r and r["goals"] > 0 for r in rows)


def test_top_team_by_record(engine):
    """Scenario: best home record
      When I rank teams by home win rate in 2019
      Then the ranking is non-increasing
    """
    rows = engine.top_teams_by_record(
        competition="Brasileirao", season=2019, home_away="overall", metric="win_rate", limit=5
    )
    assert len(rows) == 5
    rates = [r.win_rate for r in rows]
    assert rates == sorted(rates, reverse=True)
