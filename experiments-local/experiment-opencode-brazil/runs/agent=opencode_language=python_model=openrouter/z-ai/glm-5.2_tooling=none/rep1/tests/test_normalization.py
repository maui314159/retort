from brazilian_soccer_mcp.normalizers import (
    canonical_team_id,
    parse_date,
    team_display_name,
)


def test_state_suffix_normalized():
    """Scenario: team name with state suffix
    Given team names written with different conventions
    When they are canonicalized
    Then the state suffix variants collapse to the same id
    """
    assert canonical_team_id("Flamengo-RJ") == canonical_team_id("Flamengo")
    assert canonical_team_id("Palmeiras-SP") == canonical_team_id("Palmeiras")
    assert canonical_team_id("CSA-AL") == canonical_team_id("CSA")
    assert canonical_team_id("Ceará-CE") == canonical_team_id("Ceara")


def test_accents_and_full_names():
    """Scenario: accented and full team names
    Given names like São Paulo, Grêmio, Sport Club Corinthians Paulista
    When canonicalized
    Then accents are stripped and full names resolve to the club
    """
    assert canonical_team_id("São Paulo") == "sao_paulo"
    assert canonical_team_id("São Paulo-SP") == "sao_paulo"
    assert canonical_team_id("Grêmio") == canonical_team_id("Gremio-RS")
    assert canonical_team_id("Sport Club Corinthians Paulista") == "corinthians"


def test_state_specific_clubs_stay_distinct():
    """Scenario: clubs sharing a base name in different states
    Given Atletico-MG and Atletico-GO
    When canonicalized
    Then they remain distinct ids
    """
    assert canonical_team_id("Atlético-MG") == "atletico_mg"
    assert canonical_team_id("Atlético-GO") == "atletico_go"
    assert canonical_team_id("Atlético-MG") != canonical_team_id("Atlético-GO")


def test_display_name_roundtrip():
    assert team_display_name("flamengo") == "Flamengo"
    assert team_display_name("atletico_mg") == "Atletico-MG"


def test_date_formats():
    """Scenario: multiple date formats
    Given ISO, Brazilian and datetime strings
    When parsed
    Then they all yield the correct date
    """
    assert parse_date("2023-09-24") == parse_date("24/09/2023")
    assert parse_date("2023-09-24 18:30:00") == parse_date("2023-09-24")
    assert parse_date("29/03/2003").isoformat() == "2003-03-29"
    assert parse_date("") is None
    assert parse_date(None) is None
