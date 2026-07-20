"""Unit tests for the query layer.

Ground-truth anchors:
- 2019 Brasileirão: Flamengo champion with 90 pts (28W, 6D, 4L),
  Santos 2nd with 74 pts — matches the specification's example output.
- Corinthians' 2019 home record recomputed independently from the raw
  historical CSV.
"""

import pandas as pd
import pytest

from brazilian_soccer_mcp import queries
from brazilian_soccer_mcp.data import BRASILEIRAO_A, COPA_DO_BRASIL, LIBERTADORES
from brazilian_soccer_mcp.queries import resolve_competition

# ----------------------------------------------------------------------
# Match queries
# ----------------------------------------------------------------------


def test_find_matches_between_two_teams(ds):
    res = queries.find_matches(team="Flamengo", opponent="Fluminense", dataset=ds)
    assert res["count"] > 0
    for m in res["matches"]:
        pair = {m["home_team"], m["away_team"]}
        assert pair == {"Flamengo", "Fluminense"}
        assert m["date"] and m["competition"]
        assert m["home_goals"] is not None and m["away_goals"] is not None


def test_find_matches_by_team_and_season(ds):
    res = queries.find_matches(team="Palmeiras", season=2023, dataset=ds)
    assert res["count"] > 0
    assert all(m["season"] == 2023 for m in res["matches"])
    assert all(
        "Palmeiras" in (m["home_team"], m["away_team"]) for m in res["matches"]
    )


def test_find_matches_by_date_range(ds):
    res = queries.find_matches(
        team="Flamengo", date_from="2023-01-01", date_to="2023-12-31", dataset=ds
    )
    assert res["count"] > 0
    assert all(m["date"].startswith("2023") for m in res["matches"])


def test_find_matches_by_competition_alias(ds):
    res = queries.find_matches(team="Flamengo", competition="libertadores", dataset=ds)
    assert res["count"] > 0
    assert all(m["competition"] == LIBERTADORES for m in res["matches"])


def test_find_matches_venue_filter(ds):
    home = queries.find_matches(
        team="Corinthians", venue="home", competition="Brasileirão", season=2019, dataset=ds
    )
    assert home["count"] == 19
    assert all(m["home_team"] == "Corinthians" for m in home["matches"])
    with pytest.raises(ValueError):
        queries.find_matches(team="Corinthians", venue="sidelines", dataset=ds)


def test_find_matches_libertadores_finals(ds):
    res = queries.find_matches(competition="Copa Libertadores", stage="final", dataset=ds)
    assert res["count"] > 0
    assert all(m["stage"] == "final" for m in res["matches"])


def test_find_matches_copa_do_brasil_finals(ds):
    """Cup finals = the last round of each season in the cup file."""
    res = queries.find_matches(competition="Copa do Brasil", stage="final", dataset=ds)
    assert res["count"] > 0
    by_season = {}
    for m in ds.matches[ds.matches["competition"] == COPA_DO_BRASIL].itertuples():
        if pd.notna(m.round):
            by_season[int(m.season)] = max(by_season.get(int(m.season), 0), int(m.round))
    for m in res["matches"]:
        assert m["round"] == by_season[m["season"]]


def test_find_matches_respects_limit(ds):
    res = queries.find_matches(team="Flamengo", limit=5, dataset=ds)
    assert len(res["matches"]) == 5
    assert res["count"] > 5


def test_find_matches_unknown_team_returns_empty(ds):
    res = queries.find_matches(team="Nonexistent FC", dataset=ds)
    assert res["count"] == 0
    assert res["matches"] == []


# ----------------------------------------------------------------------
# Team queries
# ----------------------------------------------------------------------


def test_head_to_head_balance_is_consistent(ds):
    res = queries.head_to_head("Flamengo", "Fluminense", dataset=ds)
    assert res["matches_played"] > 0
    assert (
        res["team_a_wins"] + res["team_b_wins"] + res["draws"] == res["matches_played"]
    )
    assert res["team_a"] == "Flamengo"
    assert res["team_b"] == "Fluminense"
    assert "Head-to-head in dataset" in res["summary"]


def test_head_to_head_is_symmetric(ds):
    ab = queries.head_to_head("Palmeiras", "Santos", dataset=ds)
    ba = queries.head_to_head("Santos", "Palmeiras", dataset=ds)
    assert ab["matches_played"] == ba["matches_played"]
    assert ab["team_a_wins"] == ba["team_b_wins"]
    assert ab["draws"] == ba["draws"]


def test_team_statistics_crosscheck_with_raw_csv(ds):
    """Recompute Corinthians' 2019 home record straight from the raw file."""
    raw = pd.read_csv(ds.data_dir / "novo_campeonato_brasileiro.csv")
    home = raw[(raw["Ano"] == 2019) & (raw["Equipe_mandante"] == "Corinthians")]
    exp_wins = int((home["Gols_mandante"] > home["Gols_visitante"]).sum())
    exp_draws = int((home["Gols_mandante"] == home["Gols_visitante"]).sum())
    exp_gf = int(home["Gols_mandante"].sum())
    exp_ga = int(home["Gols_visitante"].sum())

    stats = queries.team_statistics(
        "Corinthians", season=2019, venue="home", competition="Brasileirão", dataset=ds
    )
    assert stats["matches"] == len(home) == 19
    assert stats["wins"] == exp_wins
    assert stats["draws"] == exp_draws
    assert stats["losses"] == len(home) - exp_wins - exp_draws
    assert stats["goals_for"] == exp_gf
    assert stats["goals_against"] == exp_ga
    assert stats["goal_difference"] == exp_gf - exp_ga
    assert 0 <= stats["win_rate_pct"] <= 100


def test_team_statistics_name_variants(ds):
    a = queries.team_statistics("São Paulo", season=2019, dataset=ds)
    b = queries.team_statistics("Sao Paulo-SP", season=2019, dataset=ds)
    assert a["matches"] == b["matches"] > 0
    assert a["wins"] == b["wins"]


def test_team_competitions(ds):
    res = queries.team_competitions("Flamengo", dataset=ds)
    comps = {c["competition"] for c in res["competitions"]}
    assert {BRASILEIRAO_A, COPA_DO_BRASIL, LIBERTADORES} <= comps


# ----------------------------------------------------------------------
# Competition queries
# ----------------------------------------------------------------------


def test_standings_2019_brasileirao(ds):
    res = queries.standings(2019, dataset=ds)
    assert res["matches_counted"] == 380
    assert len(res["table"]) == 20
    top = res["table"][0]
    assert res["champion"] == "Flamengo"
    assert top["team"] == "Flamengo"
    assert top["points"] == 90
    assert (top["wins"], top["draws"], top["losses"]) == (28, 6, 4)
    second, third = res["table"][1], res["table"][2]
    assert second["team"] == "Santos" and second["points"] == 74
    assert third["team"] == "Palmeiras" and third["points"] == 74


def test_standings_internal_consistency(ds):
    res = queries.standings(2018, dataset=ds)
    table = res["table"]
    points = [t["points"] for t in table]
    assert points == sorted(points, reverse=True)
    for t in table:
        assert t["points"] == 3 * t["wins"] + t["draws"]
        assert t["played"] == t["wins"] + t["draws"] + t["losses"]
        assert t["goal_difference"] == t["goals_for"] - t["goals_against"]


def test_standings_unknown_season_raises(ds):
    with pytest.raises(ValueError):
        queries.standings(1950, dataset=ds)


def test_list_competitions(ds):
    res = queries.list_competitions(dataset=ds)
    names = {c["competition"] for c in res["competitions"]}
    assert {BRASILEIRAO_A, COPA_DO_BRASIL, LIBERTADORES} <= names
    assert all(c["matches"] > 0 for c in res["competitions"])


def test_list_teams(ds):
    res = queries.list_teams(competition="Brasileirão Série A", season=2019, dataset=ds)
    assert res["count"] == 20
    assert "Flamengo" in res["teams"] and "Grêmio" in res["teams"]


# ----------------------------------------------------------------------
# Player queries
# ----------------------------------------------------------------------


def test_search_players_by_name(ds):
    res = queries.search_players(name="Neymar", dataset=ds)
    assert res["count"] >= 1
    top = res["players"][0]
    assert top["name"] == "Neymar Jr"
    assert top["overall"] == 92
    assert top["nationality"] == "Brazil"


def test_search_players_name_is_accent_insensitive(ds):
    assert queries.search_players(name="Neymar", dataset=ds)["count"] >= 1


def test_filter_brazilian_players(ds):
    res = queries.search_players(nationality="brazil", dataset=ds)
    assert res["count"] == 827
    assert all(p["nationality"] == "Brazil" for p in res["players"])


def test_filter_players_by_brazilian_club(ds):
    res = queries.search_players(club="Grêmio", dataset=ds)
    assert res["count"] > 0
    assert all(p["club"] == "Grêmio" for p in res["players"])


def test_filter_players_by_position_group(ds):
    res = queries.search_players(club="Santos", position="forward", dataset=ds)
    assert res["count"] > 0
    forwards = {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"}
    assert all(p["position"] in forwards for p in res["players"])


def test_top_players_brazil(ds):
    res = queries.top_players(nationality="Brazil", limit=5, dataset=ds)
    names = [p["name"] for p in res["players"]]
    assert names[0] == "Neymar Jr"
    overalls = [p["overall"] for p in res["players"]]
    assert overalls == sorted(overalls, reverse=True)


def test_search_players_min_overall(ds):
    res = queries.search_players(min_overall=90, dataset=ds)
    assert res["count"] > 0
    assert all(p["overall"] >= 90 for p in res["players"])


def test_search_players_no_results(ds):
    res = queries.search_players(name="Zzz Nonexistent", dataset=ds)
    assert res["count"] == 0
    assert res["players"] == []


def test_players_by_club(ds):
    res = queries.players_by_club(nationality="Brazil", dataset=ds)
    assert len(res["clubs"]) > 0
    clubs = {c["club"] for c in res["clubs"]}
    assert any(c in clubs for c in ("Grêmio", "Flamengo", "Santos", "Palmeiras"))
    for c in res["clubs"]:
        assert c["players"] > 0 and 40 <= c["avg_overall"] <= 95


# ----------------------------------------------------------------------
# Statistical analysis
# ----------------------------------------------------------------------


def test_biggest_wins(ds):
    res = queries.biggest_wins(limit=10, dataset=ds)
    margins = [r["margin"] for r in res["results"]]
    assert margins == sorted(margins, reverse=True)
    top = res["results"][0]
    assert top["home_team"] == "São Paulo"
    assert top["home_goals"] == 9 and top["away_goals"] == 1


def test_competition_overview_brasileirao_2019(ds):
    res = queries.competition_overview(competition="Brasileirão Série A", season=2019, dataset=ds)
    assert res["matches"] == 380
    assert 1.5 < res["avg_goals_per_match"] < 4.0
    total_pct = res["home_win_pct"] + res["draw_pct"] + res["away_win_pct"]
    assert abs(total_pct - 100.0) < 0.5
    assert res["home_win_pct"] > res["away_win_pct"]  # home advantage


def test_competition_resolution():
    matches = pd.DataFrame({"competition": [BRASILEIRAO_A, COPA_DO_BRASIL]})
    assert resolve_competition("brasileirao", matches) == BRASILEIRAO_A
    assert resolve_competition("Serie A", matches) == BRASILEIRAO_A
    assert resolve_competition("Brasileirão Série A", matches) == BRASILEIRAO_A
    assert resolve_competition("copa do brasil", matches) == COPA_DO_BRASIL
    with pytest.raises(ValueError):
        resolve_competition("Champions League", matches)


# ----------------------------------------------------------------------
# Performance (success criteria: < 2 s lookups, < 5 s aggregates)
# ----------------------------------------------------------------------


def test_query_performance(ds, monkeypatch):
    import time

    start = time.perf_counter()
    queries.find_matches(team="Flamengo", opponent="Fluminense", dataset=ds)
    queries.search_players(name="Neymar", dataset=ds)
    assert time.perf_counter() - start < 2.0

    start = time.perf_counter()
    queries.standings(2019, dataset=ds)
    queries.competition_overview(dataset=ds)
    queries.biggest_wins(dataset=ds)
    assert time.perf_counter() - start < 5.0
