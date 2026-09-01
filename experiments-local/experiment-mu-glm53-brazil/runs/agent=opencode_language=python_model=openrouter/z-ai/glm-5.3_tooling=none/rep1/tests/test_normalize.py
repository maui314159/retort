"""Unit tests for team-name canonicalization (spec: Data Quality Notes - Team Name Variations).

Covers state suffixes, spelling variants, official full names, foreign clubs
with country tags and accent handling.
"""

from brasil_mcp.normalize import parse_team_name, strip_accents


class TestStripAccents:
    def test_accents(self):
        assert strip_accents("São Paulo") == "Sao Paulo"
        assert strip_accents("Grêmio") == "Gremio"
        assert strip_accents("Avaí") == "Avai"
        assert strip_accents("Fortaleza") == "Fortaleza"


class TestParseTeamName:
    def test_state_suffix_hyphen(self):
        assert parse_team_name("Palmeiras-SP") == ("palmeiras", "SP", None)

    def test_state_suffix_space(self):
        assert parse_team_name("America MG") == ("america", "MG", None)

    def test_state_suffix_spaced_dash(self):
        assert parse_team_name("América - MG") == ("america", "MG", None)

    def test_bare_name(self):
        assert parse_team_name("Palmeiras") == ("palmeiras", None, None)

    def test_athletico_folds_to_atletico(self):
        assert parse_team_name("Athletico-PR") == parse_team_name("Atlético-PR")

    def test_full_official_name(self):
        assert parse_team_name("Sport Club Corinthians Paulista") == ("corinthians", "SP", None)

    def test_vasco_full_name_with_state(self):
        assert parse_team_name("Vasco da Gama-RJ") == ("vasco", "RJ", None)

    def test_fifa_full_names(self):
        assert parse_team_name("Atlético Mineiro") == ("atletico", "MG", None)
        assert parse_team_name("Atlético Paranaense") == ("atletico", "PR", None)
        assert parse_team_name("Sport Club do Recife") == ("sport", "PE", None)
        assert parse_team_name("América FC (Minas Gerais)") == ("america", "MG", None)

    def test_country_tag_parens(self):
        assert parse_team_name("Nacional (URU)") == ("nacional", None, "URU")

    def test_country_tag_suffix(self):
        assert parse_team_name("Barcelona-EQU") == ("barcelona", None, "EQU")

    def test_parenthetical_note_removed(self):
        base, uf, _ = parse_team_name(
            "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
        )
        assert (base, uf) == ("boavista", "RJ")

    def test_gremio_variants(self):
        assert parse_team_name("Grêmio") == ("gremio", None, None)
        assert parse_team_name("Gremio-RS") == ("gremio", "RS", None)
        assert parse_team_name("Grêmio - RS") == ("gremio", "RS", None)


class TestRegistryResolution:
    """Resolution merges name variants onto one canonical id per club."""

    def test_registry_merges_flamengo_variants(self):
        from brasil_mcp.store import SoccerStore

        store = SoccerStore("data/kaggle")
        ids = {
            store.resolve_team(v)
            for v in ("Flamengo", "Flamengo-RJ", "Flamengo - RJ", "flamengo rj")
        }
        assert ids == {"flamengo-rj"}

    def test_registry_merges_atletico_pr_variants(self):
        from brasil_mcp.store import SoccerStore

        store = SoccerStore("data/kaggle")
        ids = {
            store.resolve_team(v)
            for v in ("Athletico-PR", "Atlético-PR", "Atletico - PR", "Athletico Paranaense")
        }
        assert ids == {"atletico-pr"}

    def test_atletico_clubs_stay_distinct(self):
        from brasil_mcp.store import SoccerStore

        store = SoccerStore("data/kaggle")
        assert store.resolve_team("Atlético-MG") != store.resolve_team("Athletico-PR")
        assert store.resolve_team("Atlético-GO") != store.resolve_team("Atlético-MG")

    def test_santos_clubs_stay_distinct(self):
        from brasil_mcp.store import SoccerStore

        store = SoccerStore("data/kaggle")
        santos_sp = store.resolve_team("Santos")
        santos_ap = store.resolve_team("Santos-AP")
        santos_laguna = store.resolve_team("Santos Laguna")
        assert len({santos_sp, santos_ap, santos_laguna}) == 3

    def test_vasco_variants_merge(self):
        from brasil_mcp.store import SoccerStore

        store = SoccerStore("data/kaggle")
        ids = {store.resolve_team(v) for v in ("Vasco", "Vasco da Gama", "Vasco da Gama-RJ")}
        assert ids == {"vasco-rj"}

    def test_display_names_are_friendly(self):
        from brasil_mcp.store import SoccerStore

        store = SoccerStore("data/kaggle")
        assert store.team_display(store.resolve_team("Palmeiras")) == "Palmeiras"
        assert store.team_display(store.resolve_team("São Paulo")) == "São Paulo"
        assert store.team_display(store.resolve_team("América-MG")) == "América-MG"

    def test_suggestions_for_partial_names(self):
        from brasil_mcp.store import SoccerStore

        store = SoccerStore("data/kaggle")
        assert any("fluminense" in cid for cid in store.suggest_teams("Flu"))
