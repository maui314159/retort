from brazilian_soccer_mcp import QueryEngine


def test_average_goals_per_match(engine):
    """Feature: Statistical Analysis
    Scenario: average goals per match in the Brasileirao
      Given the match data is loaded
      When I request average goals per match
      Then I get a positive float around 2-3 goals
    """
    avg = engine.average_goals_per_match("Brasileirao")
    assert 1.5 < avg < 4.0


def test_average_goals_for_season(engine):
    """Scenario: average goals for a specific season
      When I request average goals for 2019 Brasileirao
      Then the value is positive
    """
    avg = engine.average_goals_per_match("Brasileirao", 2019)
    assert 1.5 < avg < 4.0


def test_home_vs_away_performance(engine):
    """Scenario: home vs away performance
      When I request home/away performance
      Then home wins should exceed away wins
    """
    perf = engine.home_vs_away_performance("Brasileirao")
    assert perf["matches"] > 0
    assert perf["home_wins"] + perf["away_wins"] + perf["draws"] == perf["matches"]
    assert perf["home_win_rate"] > perf["away_win_rate"]


def test_biggest_wins(engine):
    """Scenario: biggest wins in the dataset
      When I request biggest wins
      Then matches are sorted by goal difference descending
    """
    matches = engine.biggest_wins("Brasileirao", limit=10)
    assert len(matches) > 0
    diffs = [abs(m.home_goal - m.away_goal) for m in matches]
    assert diffs == sorted(diffs, reverse=True)
    assert diffs[0] >= 5


def test_derbies_found(engine):
    """Scenario: derbies in 2023
      When I request derbies for 2023
      Then at least one derby pair has matches
    """
    derbies = engine.derbies(season=2023)
    assert len(derbies) > 0
    total = sum(d["count"] for d in derbies)
    assert total > 0
    fla_flu = [d for d in derbies if d["derby_name"] == "Fla-Flu"][0]
    assert fla_flu["team_a"] == "Flamengo"
    assert fla_flu["team_b"] == "Fluminense"


def test_match_stats_available(engine):
    """Scenario: extended match statistics
      When I request match stats for a team
      Then some matches include corners and shots
    """
    rows = engine.match_stats(team="Flamengo", season=2023, limit=20)
    assert len(rows) > 0
    has_stats = any(r.get("home_shots") is not None for r in rows)
    assert has_stats
