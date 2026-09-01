"""Unit tests for team-name normalization (BDD / GWT style)."""


from soccer.normalize import normalize_name, normalize_player_name


class TestTeamNameNormalization:
    def test_state_suffix_is_stripped(self):
        """Given names with state suffixes, they normalize to the base key."""
        assert normalize_name("Palmeiras-SP") == "palmeiras"
        assert normalize_name("Flamengo-RJ") == "flamengo"

    def test_spaced_state_suffix_is_stripped(self):
        assert normalize_name("América - MG") == "america"

    def test_accents_are_removed(self):
        assert normalize_name("Grêmio") == "gremio"
        assert normalize_name("São Paulo") == "sao paulo"

    def test_legal_name_words_are_stripped(self):
        assert normalize_name("Sport Club Corinthians Paulista") == "sport corinthians paulista"

    def test_parenthetical_remarks_are_removed(self):
        key = normalize_name(
            "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
        )
        assert "antigo" not in key
        assert key.startswith("boavista")

    def test_aliases_unify_variants(self):
        """Given cross-dataset variants, they map to one canonical key."""
        assert normalize_name("Vasco") == normalize_name("Vasco da Gama")
        assert normalize_name("Atlético-MG") == normalize_name("Atlético Mineiro")
        assert normalize_name("Athletico-PR") == normalize_name("Atlético Paranaense")

    def test_sport_is_not_a_strippable_word(self):
        assert normalize_name("Sport-PE") == "sport"

    def test_empty_input(self):
        assert normalize_name("") == ""
        assert normalize_name(None) == ""


class TestPlayerNameNormalization:
    def test_case_and_accents(self):
        assert normalize_player_name("Gabriel Barbosa") == "gabriel barbosa"
        assert normalize_player_name("Neymar JR") == "neymar jr"
