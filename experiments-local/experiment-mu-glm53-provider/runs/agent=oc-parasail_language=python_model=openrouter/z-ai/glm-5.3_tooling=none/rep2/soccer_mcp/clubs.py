"""Curated registry of Brazilian soccer clubs.

Every raw team string found in the datasets is normalized (see
``normalize.normalize_text``) and looked up against the alias index below.
Aliases cover the naming variants observed across the six Kaggle files:

* state-suffixed forms ....... "Palmeiras-SP", "Grêmio - RS", "Botafogo RJ"
* plain forms ................ "Palmeiras", "Gremio"
* full/legal names .......... "Atlético Mineiro", "Athletico Paranaense",
                              "Sport Club do Recife", "América FC (Minas Gerais)"

Base names ("flamengo") are claimed by the *major* club only; smaller clubs
sharing a name always carry their state ("Flamengo-PI" is a distinct club).
Foreign Libertadores clubs are not curated: they resolve through the
generic fallback identity built by ``fallback_club``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import (
    FOREIGN_COUNTRY_CODES,
    normalize_text,
    split_state_suffix,
)


@dataclass(frozen=True)
class Club:
    club_id: str
    name: str  # display name (no state suffix)
    state: str | None  # Brazilian UF, or None for foreign clubs
    country: str  # ISO-ish country code, "BRA" for Brazilian clubs
    aliases: frozenset  # normalized keys, incl. state-suffixed variants
    fifa_names: frozenset  # exact FIFA 'Club' column strings (FIFA 19)

    @property
    def display(self) -> str:
        return f"{self.name} ({self.state})" if self.state else self.name


@dataclass(frozen=True)
class Derby:
    name: str
    club_a: str
    club_b: str


def _club(club_id, name, state, aliases, fifa_names=()):
    return Club(
        club_id=club_id,
        name=name,
        state=state,
        country="BRA",
        aliases=frozenset(aliases),
        fifa_names=frozenset(fifa_names),
    )


_CLUBS = [
    # --- Rio de Janeiro ---
    _club("flamengo", "Flamengo", "RJ",
          ["flamengo", "flamengo rj", "cr flamengo"]),
    _club("fluminense", "Fluminense", "RJ",
          ["fluminense", "fluminense rj"], fifa_names=["Fluminense"]),
    _club("vasco", "Vasco da Gama", "RJ",
          ["vasco", "vasco rj", "vasco da gama", "vasco da gama rj",
           "cr vasco da gama"]),
    _club("botafogo_rj", "Botafogo", "RJ",
          ["botafogo", "botafogo rj", "botafogo de futebol e regatas"],
          fifa_names=["Botafogo"]),
    # --- São Paulo ---
    _club("corinthians", "Corinthians", "SP",
          ["corinthians", "corinthians sp", "sport club corinthians paulista"]),
    _club("palmeiras", "Palmeiras", "SP",
          ["palmeiras", "palmeiras sp", "se palmeiras"]),
    _club("sao_paulo", "São Paulo", "SP",
          ["sao paulo", "sao paulo sp", "sao paulo fc"]),
    _club("santos", "Santos", "SP",
          ["santos", "santos sp", "santos fc"], fifa_names=["Santos"]),
    _club("ponte_preta", "Ponte Preta", "SP",
          ["ponte preta", "ponte preta sp"]),
    _club("portuguesa", "Portuguesa", "SP",
          ["portuguesa", "portuguesa sp", "portuguesa desportos"]),
    _club("bragantino", "Red Bull Bragantino", "SP",
          ["bragantino", "red bull bragantino", "red bull bragantino sp",
           "rb bragantino"]),
    _club("guarani", "Guarani", "SP", ["guarani", "guarani sp"]),
    _club("ituano", "Ituano", "SP", ["ituano", "ituano sp"]),
    _club("oeste", "Oeste", "SP", ["oeste", "oeste sp"]),
    _club("santo_andre", "Santo André", "SP", ["santo andre", "santo andre sp"]),
    # --- Minas Gerais ---
    _club("atletico_mg", "Atlético Mineiro", "MG",
          ["atletico mg", "atletico mineiro", "clube atletico mineiro"],
          fifa_names=["Atlético Mineiro"]),
    _club("cruzeiro", "Cruzeiro", "MG",
          ["cruzeiro", "cruzeiro mg"], fifa_names=["Cruzeiro"]),
    _club("america_mg", "América Mineiro", "MG",
          ["america mg", "america mineiro", "america fc minas gerais",
           "america fc mg"], fifa_names=["América FC (Minas Gerais)"]),
    # --- Rio Grande do Sul ---
    _club("gremio", "Grêmio", "RS",
          ["gremio", "gremio rs"], fifa_names=["Grêmio"]),
    _club("internacional", "Internacional", "RS",
          ["internacional", "internacional rs", "sc internacional"],
          fifa_names=["Internacional"]),
    _club("juventude", "Juventude", "RS",
          ["juventude", "juventude rs", "ec juventude"]),
    # --- Paraná ---
    _club("atletico_pr", "Athletico Paranaense", "PR",
          ["atletico pr", "athletico pr", "atletico paranaense",
           "athletico paranaense", "athletico"],
          fifa_names=["Atlético Paranaense"]),
    _club("coritiba", "Coritiba", "PR", ["coritiba", "coritiba pr"]),
    _club("parana", "Paraná", "PR",
          ["parana", "parana pr", "parana clube"], fifa_names=["Paraná"]),
    _club("londrina", "Londrina", "PR", ["londrina", "londrina pr"]),
    _club("operario_pr", "Operário-PR", "PR",
          ["operario pr", "operario ferroviario"]),
    # --- Santa Catarina ---
    _club("avai", "Avaí", "SC", ["avai", "avai sc"]),
    _club("chapecoense", "Chapecoense", "SC",
          ["chapecoense", "chapecoense sc"], fifa_names=["Chapecoense"]),
    _club("criciuma", "Criciúma", "SC", ["criciuma", "criciuma sc"]),
    _club("figueirense", "Figueirense", "SC", ["figueirense", "figueirense sc"]),
    _club("joinville", "Joinville", "SC", ["joinville", "joinville sc"]),
    _club("brusque", "Brusque", "SC", ["brusque", "brusque sc"]),
    # --- Bahia ---
    _club("bahia", "Bahia", "BA",
          ["bahia", "bahia ba", "ec bahia", "esporte clube bahia"],
          fifa_names=["Bahia"]),
    _club("vitoria", "Vitória", "BA",
          ["vitoria", "vitoria ba", "ec vitoria", "esporte clube vitoria"],
          fifa_names=["Vitória"]),
    _club("bahia_de_feira", "Bahia de Feira", "BA",
          ["bahia de feira", "bahia de feira ba"]),
    _club("vitoria_da_conquista", "Vitória da Conquista", "BA",
          ["vitoria da conquista", "vitoria da conquista ba"]),
    # --- Pernambuco ---
    _club("sport", "Sport", "PE",
          ["sport", "sport pe", "sport recife", "sport club recife",
           "sport club do recife"], fifa_names=["Sport Club do Recife"]),
    _club("nautico", "Náutico", "PE",
          ["nautico", "nautico pe", "nautico capibaribe"]),
    _club("santa_cruz", "Santa Cruz", "PE",
          ["santa cruz", "santa cruz pe", "santa cruz fc"]),
    # --- Ceará ---
    _club("ceara", "Ceará", "CE",
          ["ceara", "ceara ce", "ceara sporting club", "ceara sc"],
          fifa_names=["Ceará Sporting Club"]),
    _club("fortaleza", "Fortaleza", "CE",
          ["fortaleza", "fortaleza ce", "fortaleza ec", "fortaleza fc"]),
    # --- Goiás / Centro-Oeste ---
    _club("goias", "Goiás", "GO", ["goias", "goias go", "goias ec"]),
    _club("atletico_go", "Atlético Goianiense", "GO",
          ["atletico go", "atletico goianiense"]),
    _club("vila_nova", "Vila Nova", "GO", ["vila nova", "vila nova go"]),
    _club("cuiaba", "Cuiabá", "MT", ["cuiaba", "cuiaba mt", "cuiaba ec"]),
    _club("brasiliense", "Brasiliense", "DF", ["brasiliense", "brasiliense df"]),
    # --- North / Northeast ---
    _club("paysandu", "Paysandu", "PA", ["paysandu", "paysandu pa"]),
    _club("remo", "Remo", "PA", ["remo", "remo pa", "clube do remo"]),
    _club("csa", "CSA", "AL", ["csa", "csa al"]),
    _club("asa", "ASA", "AL", ["asa", "asa al"]),
    _club("crb", "CRB", "AL", ["crb", "crb al"]),
    _club("abc", "ABC", "RN", ["abc", "abc rn"]),
    _club("america_rn", "América-RN", "RN",
          ["america rn", "america de natal", "america fc natal"]),
    _club("sampaio_correa", "Sampaio Corrêa", "MA",
          ["sampaio correa", "sampaio correa ma"]),
    _club("confianca", "Confiança", "SE",
          ["confianca", "confianca se", "ad confianca"]),
    _club("nacional_am", "Nacional-AM", "AM", ["nacional am"]),
    _club("atletico_ac", "Atlético Acreano", "AC",
          ["atletico ac", "atletico acreano"]),
    _club("atletico_alagoinhas", "Atlético de Alagoinhas", "BA",
          ["atletico ba", "atletico alagoinhas"]),
    _club("atletico_cearense", "Atlético Cearense", "CE",
          ["atletico cearense", "fc atletico cearense"]),
    # --- same-name smaller clubs (must not fall through to major clubs) ---
    _club("flamengo_pi", "Flamengo-PI", "PI",
          ["flamengo pi", "flamengo do piaui", "flamengo do piaui pi"]),
    _club("fluminense_pi", "Fluminense-PI", "PI", ["fluminense pi"]),
    _club("fluminense_de_feira", "Fluminense de Feira", "BA",
          ["fluminense de feira", "fluminense de feira ba"]),
    _club("internacional_sc", "Internacional-SC", "SC",
          ["internacional sc", "ec internacional sc"]),
    _club("botafogo_pb", "Botafogo-PB", "PB", ["botafogo pb"]),
    _club("botafogo_sp", "Botafogo-SP", "SP", ["botafogo sp"]),
    _club("bragantino_pa", "Bragantino-PA", "PA", ["bragantino pa"]),
    _club("boavista_rj", "Boavista", "RJ",
          ["boavista", "boavista rj", "boavista sport club",
           "boavista sport club antigo esporte clube barreira",
           "boavista sport club antigo esporte clube barreira rj"]),
    _club("macae", "Macae", "RJ", ["macae", "macae esporte fc", "macae esporte rj"]),
    _club("campinense", "Campinense", "PB",
          ["campinense", "campinense clube"]),
    _club("tombense", "Tombense", "MG", ["tombense", "tombense mg"]),
    _club("tupi_mg", "Tupi", "MG", ["tupi", "tupi mg"]),
    _club("ypiranga_rs", "Ypiranga", "RS", ["ypiranga", "ypiranga rs"]),
    # --- same-base clubs that must stay distinct from each other ---
    _club("central_pe", "Central", "PE", ["central pe"]),
    _club("central_sc", "Central", "SC", ["central sc"]),
    _club("comercial_ms", "Comercial", "MS", ["comercial ms"]),
    _club("comercial_pi", "Comercial", "PI", ["comercial pi"]),
    _club("operario_ms", "Operário-MS", "MS", ["operario ms"]),
    _club("operario_mt", "Operário-MT", "MT", ["operario mt"]),
    _club("river_ac", "River", "AC", ["river ac"]),
    _club("river_pi", "River", "PI", ["river pi"]),
    _club("river_plate_se", "River Plate", "SE", ["river plate se"]),
    _club("penarol_am", "Peñarol", "AM", ["penarol am"]),
    _club("rio_branco_ac", "Rio Branco", "AC", ["rio branco ac"]),
    _club("rio_branco_es", "Rio Branco", "ES", ["rio branco es"]),
    _club("santa_cruz_rn", "Santa Cruz-RN", "RN", ["santa cruz rn"]),
    _club("santa_cruz_rs", "Santa Cruz-RS", "RS", ["santa cruz rs"]),
    _club("sao_francisco_ac", "São Francisco", "AC", ["sao francisco ac"]),
    _club("sao_francisco_pa", "São Francisco", "PA", ["sao francisco pa"]),
    _club("sao_jose_pa", "São Jose", "PA", ["sao jose pa"]),
    _club("sao_jose_rs", "São Jose", "RS", ["sao jose rs", "sao jose poa"]),
    _club("sao_raimundo_am", "São Raimundo", "AM", ["sao raimundo am"]),
    _club("sao_raimundo_pa", "São Raimundo", "PA", ["sao raimundo pa"]),
    _club("sao_raimundo_rr", "São Raimundo", "RR", ["sao raimundo rr"]),
    _club("moto_clube", "Moto Club", "MA",
          ["moto clube", "moto club", "moto club de sao luis"]),
]

CLUBS: dict[str, Club] = {c.club_id: c for c in _CLUBS}

# alias key -> club_id (aliases include state-suffixed variants)
ALIAS_INDEX: dict[str, str] = {
    alias: club.club_id for club in _CLUBS for alias in club.aliases
}
assert len(ALIAS_INDEX) == sum(len(c.aliases) for c in _CLUBS), "alias collision"

# exact FIFA club string -> canonical club id
FIFA_CLUB_INDEX: dict[str, str] = {
    fifa_name: club.club_id for club in _CLUBS for fifa_name in club.fifa_names
}

# --- Brazilian derbies (traditional rivalries) -------------------------------
DERBIES = [
    Derby("Fla-Flu", "flamengo", "fluminense"),
    Derby("Clássico dos Milhões", "flamengo", "vasco"),
    Derby("Clássico Vovô", "botafogo_rj", "fluminense"),
    Derby("Grenal", "gremio", "internacional"),
    Derby("Clássico Majestoso", "corinthians", "sao_paulo"),
    Derby("Derby Paulista", "corinthians", "palmeiras"),
    Derby("Choque-Rei", "palmeiras", "sao_paulo"),
    Derby("San-São", "santos", "sao_paulo"),
    Derby("Clássico da Saudade", "palmeiras", "santos"),
    Derby("Ba-Vi", "bahia", "vitoria"),
    Derby("Clássico-Rei (Minas Gerais)", "atletico_mg", "cruzeiro"),
    Derby("Atletiba", "atletico_pr", "coritiba"),
    Derby("Clássico-Rei (Ceará)", "ceara", "fortaleza"),
]


def resolve_club(query: str) -> Club | None:
    """Resolve a raw/user string to a curated club, or None.

    Tier 1: exact normalized alias ("flamengo rj", "atletico mineiro").
    Tier 2: strip a trailing Brazilian UF, then re-check the alias index,
            accepting only when the UF matches the club's own state. This
            lets "Flamengo RJ" resolve while "Flamengo-PI" stays distinct.
    """
    if not query or not query.strip():
        return None
    key = normalize_text(query)
    if not key:
        return None
    club_id = ALIAS_INDEX.get(key)
    if club_id:
        return CLUBS[club_id]
    base, uf = split_state_suffix(key)
    if base != key and uf:
        club_id = ALIAS_INDEX.get(base)
        if club_id and CLUBS[club_id].state == uf:
            return CLUBS[club_id]
    return None


def fallback_club(raw_name: str) -> Club:
    """Build a synthetic Club identity for names outside the registry.

    Used for foreign Libertadores clubs ("Boca Juniors", "River Plate")
    and small Brazilian clubs not curated above. The identity is the
    *state-stripped* base key, so "Luverdense - MT" (Cup file) and
    "Luverdense" (BR-Football) unify as one club, while parenthetical
    qualifiers are kept ("Nacional (URU)" vs "Nacional (PAR)") so
    same-named foreign clubs stay distinct. The UF is preserved as the
    club's state for display purposes.
    """
    raw = raw_name.strip()
    key = normalize_text(raw)
    base, uf = split_state_suffix(key)
    display = raw
    if uf:
        # drop the trailing state marker ("- PI" or "(PI)") from the display
        if m := re.search(r"^(.*?)[\s]*[-–]\s*[A-Za-z]{2}$", raw):
            display = m.group(1).strip()
        elif m := re.search(r"^(.*?)\s*\([A-Za-z]{2}\)$", raw):
            display = m.group(1).strip()
    tokens = key.split()
    country = "BRA"
    if not uf and len(tokens) >= 2 and tokens[-1].upper() in FOREIGN_COUNTRY_CODES:
        country = FOREIGN_COUNTRY_CODES[tokens[-1].upper()]
    elif not uf:
        country = "INT"
    return Club(
        club_id=f"x_{base.replace(' ', '_')}",
        name=display,
        state=uf,
        country=country,
        aliases=frozenset({key, base}),
        fifa_names=frozenset(),
    )
