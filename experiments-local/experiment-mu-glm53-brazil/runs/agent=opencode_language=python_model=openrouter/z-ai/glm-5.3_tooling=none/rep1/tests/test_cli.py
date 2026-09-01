"""CLI tests: each subcommand prints a formatted summary and exits 0."""

from brasil_mcp.cli import main


def run_cli(capsys, *argv) -> str:
    assert main(list(argv)) == 0
    return capsys.readouterr().out


def test_cli_standings(capsys):
    out = run_cli(capsys, "standings", "--season", "2019")
    assert "Flamengo - 90 pts (28W, 6D, 4L) - Champion" in out


def test_cli_matches(capsys):
    out = run_cli(
        capsys, "matches", "--team", "Flamengo", "--opponent", "Fluminense", "--limit", "3"
    )
    assert "Flamengo vs Fluminense" in out or "Matches for Flamengo vs Fluminense" in out
    assert "Head-to-head in dataset" in out


def test_cli_h2h(capsys):
    out = run_cli(capsys, "h2h", "Palmeiras", "Santos")
    assert "Head-to-head in dataset" in out


def test_cli_stats(capsys):
    out = run_cli(capsys, "stats", "Corinthians", "--season", "2022", "--competition", "Série A")
    assert "Corinthians record (2022, Série A)" in out or "Corinthians record" in out


def test_cli_players(capsys):
    out = run_cli(capsys, "players", "--nationality", "Brazil", "--min-overall", "90")
    assert "Neymar Jr" in out


def test_cli_squad(capsys):
    out = run_cli(capsys, "squad", "Grêmio")
    assert "Grêmio squad in FIFA dataset" in out


def test_cli_competitions(capsys):
    out = run_cli(capsys, "competitions")
    assert "Brasileirão Série A" in out
    assert "Copa Libertadores" in out


def test_cli_derbies(capsys):
    out = run_cli(capsys, "derbies", "--season", "2023")
    assert "Fla-Flu" in out


def test_cli_biggest_wins(capsys):
    out = run_cli(capsys, "biggest-wins", "--limit", "3")
    assert "Biggest victories" in out


def test_cli_goals(capsys):
    out = run_cli(capsys, "goals", "--competition", "Série A")
    assert "Average goals per match" in out


def test_cli_best_records(capsys):
    out = run_cli(capsys, "best-records", "--venue", "away")
    assert "Best away records" in out


def test_cli_compare(capsys):
    out = run_cli(capsys, "compare", "Grêmio", "Internacional")
    assert "vs" in out


def test_cli_find_team(capsys):
    out = run_cli(capsys, "find-team", "Sport Club Corinthians Paulista")
    assert "Team: Corinthians" in out


def test_cli_history(capsys):
    out = run_cli(capsys, "history", "Flamengo")
    assert "season-by-season" in out


def test_cli_unknown_team_prints_error(capsys):
    out = run_cli(capsys, "find-team", "Flamenguinho da Silva")
    assert "not found" in out.lower()
