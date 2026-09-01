"""
 brazilian_soccer_mcp / normalizer.py
 ===================================

 Why
 ---
 The six source CSV files write the same club in many different ways
 ("Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "Sport Club Corinthians
 Paulista", "Grêmio", "Gremio-RS", ...) and use three different date
 conventions ("2012-05-19 18:30:00", "2023-09-24", "29/03/2003").
 Every other module depends on a single, canonical way to identify clubs,
 competitions and dates, so all of that knowledge is centralised here.

 What
 ---
 * ``deaccent`` / ``squash``       - text helpers (UTF-8 aware, case folded).
 * ``parse_club_name``            - raw team string -> :class:`ClubIdentity`
                                    (core name, optional state, optional
                                    country) using state/country suffix
                                    detection, club-form-word stripping and
                                    a curated alias table.
 * ``ClubNormalizer``             - two-pass resolver.  Pass 1 learns, for
                                    every core name, which state/country
                                    suffix the data actually uses (so a
                                    stateless "Santos" from the BR-Football
                                    file resolves to Santos-SP, the club
                                    with the overwhelming majority of
                                    matches).  Pass 2 turns identities into
                                    canonical keys such as ``flamengo|RJ``.
 * ``canonical_key``              - canonical key for one raw name.
 * ``normalize_competition``      - "brasileirão", "serie a", "CDB", ... ->
                                    canonical competition ids.
 * ``parse_date`` / ``parse_goals`` / ``parse_money`` - per-source cell
                                    parsing (multiple date formats, 'NA'/'-'
                                    goal sentinels, "€110.5M" values).

 Data notes (verified against the shipped CSVs)
 ----------------------------------------------
 * novo_campeonato_brasileiro.csv mistags Bahia as UF "BH" (should be BA)
   and sometimes tags Vitória as "ES" (should be BA); the loader repairs
   those two columns via ``NOVO_UF_FIX`` / ``NOVO_TEAM_UF_FIX`` below.
 * Libertadores names carry foreign country suffixes ("Nacional (URU)",
   "Barcelona-EQU") and the 2019+ spelling "Athletico" for the Paranaense
   club; aliases below unify "Athletico"/"Atletico".
 * 'NA' or '-' in a goals column means the match was scheduled but not
   played (e.g. the 2016 Chapecoense round, the unfinished 2022 Brasileirão
   tail in Brasileirao_Matches.csv) - parsed as ``None``.

 Test: ``tests/test_normalizer.py``
====================================
"""

from __future__ import annotations

import datetime as _dt
import re
import unicodedata
from dataclasses import dataclass, replace

# --------------------------------------------------------------------------
# Text helpers
# --------------------------------------------------------------------------


def deaccent(text: str) -> str:
    """Return ``text`` with combining marks removed (São Paulo -> Sao Paulo)."""
    return "".join(
        ch
        for ch in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(ch)
    )


def squash(text: str) -> str:
    """Case-fold, de-accent, drop quotes and collapse whitespace."""
    text = deaccent(text).casefold().replace("'", "").replace("\u2019", "")
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------
# Club name parsing
# --------------------------------------------------------------------------

#: Brazilian state (UF) abbreviations that appear as team-name suffixes.
STATE_ABBREVS = frozenset(
    {
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    }
)

#: Foreign country suffixes used by the Libertadores dataset (uppercase,
#: matched against the upper-cased token).
COUNTRY_ABBREVS = frozenset({"URU", "PAR", "EQU", "PER", "VEN"})

#: Club-organisation words stripped from the front/end of a name while at
#: least one meaningful token remains ("EC Bahia" -> "bahia",
#: "Fortaleza FC" -> "fortaleza").  'sport' is front-strippable (see the
#: spec's "Sport Club Corinthians Paulista" example) but the real clubs
#: where that would be wrong are protected below.
_FORM_WORDS = frozenset(
    {
        "ec",
        "sc",
        "fc",
        "ce",
        "ge",
        "ca",
        "ad",
        "se",
        "aa",
        "ae",
        "ac",
        "club",
        "clube",
        "futebol",
        "esporte",
        "esportivo",
        "ltda",
        "sodre",
        "sport",
    }
)

#: Cores whose front 'sport' must never be stripped ("Sport Boys", Bolivia).
_PROTECTED_CORES = frozenset({"sport boys"})

#: Known-bad UF codes in novo_campeonato_brasileiro.csv -> correct value.
NOVO_UF_FIX = {"BH": "BA"}

#: Per-(team, UF) repairs for that same file (Vitória is Bahia, not ES).
NOVO_TEAM_UF_FIX = {("vitoria", "ES"): "BA"}

#: Spelling unification applied to the final core ("Athletico" = "Atletico").
CORE_ALIAS = {"athletico": "atletico"}

#: (name, state-or-None) -> (core, state).  Entries are needed whenever two
#: spellings of the same club must merge ("Atletico Mineiro" = "Atletico-MG")
#: or a stateless full name must adopt its home state ("Sport Recife" -> PE).
ALIASES: dict[tuple[str, str | None], tuple[str, str | None]] = {
    # Atletico Mineiro / Atletico-MG
    ("atletico mineiro", "MG"): ("atletico", "MG"),
    ("atletico mineiro", None): ("atletico", "MG"),
    # Athletico Paranaense / Atletico-PR (renamed 2019, same club)
    ("athletico paranaense", "PR"): ("atletico", "PR"),
    ("atletico paranaense", "PR"): ("atletico", "PR"),
    ("athletico paranaense", None): ("atletico", "PR"),
    ("atletico paranaense", None): ("atletico", "PR"),
    ("athletico", None): ("atletico", "PR"),
    # Atletico Goianiense = Atletico-GO
    ("atletico goianiense", "GO"): ("atletico", "GO"),
    ("atletico goianiense", None): ("atletico", "GO"),
    # other full names of "Atletico <state>"
    ("atletico acreano", "AC"): ("atletico", "AC"),
    ("atletico acreano", None): ("atletico", "AC"),
    ("atletico alagoinhas", "BA"): ("atletico", "BA"),
    ("atletico alagoinhas", None): ("atletico", "BA"),
    ("atletico cearense", "CE"): ("atletico", "CE"),
    ("atletico cearense", None): ("atletico", "CE"),
    # Corinthians full name (see spec's data-quality note)
    ("corinthians paulista", "SP"): ("corinthians", "SP"),
    ("corinthians paulista", None): ("corinthians", "SP"),
    # Vasco da Gama / Vasco
    ("vasco da gama", "RJ"): ("vasco", "RJ"),
    ("vasco da gama", None): ("vasco", "RJ"),
    ("vasco", None): ("vasco", "RJ"),
    # Sport Recife / Sport-PE
    ("sport recife", "PE"): ("sport", "PE"),
    ("sport recife", None): ("sport", "PE"),
    ("sport", None): ("sport", "PE"),
    # Nautico
    ("nautico capibaribe", "PE"): ("nautico", "PE"),
    ("nautico capibaribe", None): ("nautico", "PE"),
    # Portuguesa
    ("portuguesa desportos", "SP"): ("portuguesa", "SP"),
    ("portuguesa desportos", None): ("portuguesa", "SP"),
    # Red Bull Bragantino / Bragantino-SP (Bragantino-PA is a different club)
    ("red bull bragantino", "SP"): ("bragantino", "SP"),
    ("red bull bragantino", None): ("bragantino", "SP"),
    ("bragantino", None): ("bragantino", "SP"),
    # America de Natal / America-RN
    ("america de natal", "RN"): ("america", "RN"),
    ("america de natal", None): ("america", "RN"),
    ("america fc natal", "RN"): ("america", "RN"),
    ("america fc natal", None): ("america", "RN"),
    # Remo
    ("clube do remo", "PA"): ("remo", "PA"),
    ("clube do remo", None): ("remo", "PA"),
    # Guarani de Juazeiro (CE) != Guarani (SP)
    ("guarani de juazeiro", "CE"): ("guarani", "CE"),
    ("guarani de juazeiro", None): ("guarani", "CE"),
    # SER Caxias = Caxias-RS
    ("ser caxias", "RS"): ("caxias", "RS"),
    ("ser caxias", None): ("caxias", "RS"),
    # Operario-PR (Operario-MS/MT are different clubs)
    ("operario ferroviario", "PR"): ("operario", "PR"),
    ("operario ferroviario", None): ("operario", "PR"),
    # Sao Francisco-PA written "S.francisco"
    ("sfrancisco", "PA"): ("sao francisco", "PA"),
    ("sfrancisco", None): ("sao francisco", "PA"),
    # Sousa/PB spelled both ways
    ("sousa", "PB"): ("souza", "PB"),
    ("sousa", None): ("souza", "PB"),
    # XV de Piracicaba
    ("xv piracicaba", "SP"): ("xv de piracicaba", "SP"),
    ("xv piracicaba", None): ("xv de piracicaba", "SP"),
    # Gremio Novorizontino / Novorizontino
    ("gremio novorizontino", "SP"): ("novorizontino", "SP"),
    ("gremio novorizontino", None): ("novorizontino", "SP"),
    ("novorizontino", None): ("novorizontino", "SP"),
    # Desportiva Ferroviaria-ES
    ("desportiva ferroviaria", "ES"): ("desportiva", "ES"),
    ("desportiva ferroviaria", None): ("desportiva", "ES"),
    # Real Noroeste-ES
    ("real noroeste capixaba", "ES"): ("real noroeste", "ES"),
    ("real noroeste capixaba", None): ("real noroeste", "ES"),
    # Macae
    ("macae esporte", "RJ"): ("macae", "RJ"),
    ("macae esporte", None): ("macae", "RJ"),
    # CS Alagoano = CSA
    ("cs alagoano", "AL"): ("csa", "AL"),
    ("cs alagoano", None): ("csa", "AL"),
    # Independente de Tucurui = Independente-PA
    ("independente de tucurui", "PA"): ("independente", "PA"),
    ("independente de tucurui", None): ("independente", "PA"),
    # Sao Jose-POA (Porto Alegre) = Sao Jose-RS
    ("sao jose poa", "RS"): ("sao jose", "RS"),
    ("sao jose poa", None): ("sao jose", "RS"),
    # Rio Branco - Vn - ES
    ("rio branco vn", "ES"): ("rio branco", "ES"),
    ("rio branco vn", None): ("rio branco", "ES"),
    # Deportes Tolima = Tolima
    ("deportes tolima", None): ("tolima", None),
}

#: Pretty display names for the most-queried clubs (core, state) -> name.
DISPLAY_OVERRIDES: dict[tuple[str, str | None], str] = {
    ("flamengo", "RJ"): "Flamengo",
    ("fluminense", "RJ"): "Fluminense",
    ("vasco", "RJ"): "Vasco da Gama",
    ("botafogo", "RJ"): "Botafogo",
    ("corinthians", "SP"): "Corinthians",
    ("palmeiras", "SP"): "Palmeiras",
    ("sao paulo", "SP"): "São Paulo",
    ("santos", "SP"): "Santos",
    ("ponte preta", "SP"): "Ponte Preta",
    ("portuguesa", "SP"): "Portuguesa",
    ("santo andre", "SP"): "Santo André",
    ("sao caetano", "SP"): "São Caetano",
    ("bragantino", "SP"): "Red Bull Bragantino",
    ("guarani", "SP"): "Guarani",
    ("gremio", "RS"): "Grêmio",
    ("internacional", "RS"): "Internacional",
    ("juventude", "RS"): "Juventude",
    ("cruzeiro", "MG"): "Cruzeiro",
    ("atletico", "MG"): "Atlético Mineiro",
    ("america", "MG"): "América Mineiro",
    ("atletico", "PR"): "Athletico Paranaense",
    ("coritiba", "PR"): "Coritiba",
    ("parana", "PR"): "Paraná",
    ("bahia", "BA"): "Bahia",
    ("vitoria", "BA"): "Vitória",
    ("sport", "PE"): "Sport Recife",
    ("nautico", "PE"): "Náutico",
    ("santa cruz", "PE"): "Santa Cruz",
    ("ceara", "CE"): "Ceará",
    ("fortaleza", "CE"): "Fortaleza",
    ("avai", "SC"): "Avaí",
    ("chapecoense", "SC"): "Chapecoense",
    ("criciuma", "SC"): "Criciúma",
    ("figueirense", "SC"): "Figueirense",
    ("goias", "GO"): "Goiás",
    ("vila nova", "GO"): "Vila Nova",
    ("atletico", "GO"): "Atlético Goianiense",
    ("csa", "AL"): "CSA",
    ("crb", "AL"): "CRB",
    ("paysandu", "PA"): "Paysandu",
    ("remo", "PA"): "Remo",
    ("cuiaba", "MT"): "Cuiabá",
    ("brasiliense", "DF"): "Brasiliense",
    ("gama", "DF"): "Gama",
    ("ipatinga", "MG"): "Ipatinga",
    ("abc", "RN"): "ABC",
    ("america", "RN"): "América de Natal",
    ("sampaio correa", "MA"): "Sampaio Corrêa",
    ("athletico", None): "Athletico Paranaense",
}


@dataclass(frozen=True)
class ClubIdentity:
    """Parsed club name: bare core plus optional state or country."""

    core: str
    state: str | None = None
    country: str | None = None

    @property
    def region(self) -> str | None:
        return self.state or self.country

    def key(self) -> str:
        return f"{self.core}|{self.region or ''}"


_PAREN_RE = re.compile(r"\(([^)]*)\)")
_TOKEN_RE = re.compile(r"[\s\-–]+")


def parse_club_name(raw: str, state_hint: str | None = None) -> ClubIdentity:
    """
    Turn one raw team string into a :class:`ClubIdentity`.

    Handles state suffixes ("Palmeiras-SP", "America MG", "Botafogo RJ"),
    country suffixes ("Barcelona-EQU", "Nacional (URU)"), parenthetical
    remarks ("Boavista Sport Club (antigo Esporte Clube Barreira)"),
    dotted abbreviations ("C.r.b. - AL"), club form words ("EC Bahia",
    "Fortaleza FC") and the curated ALIASES table ("Sport Recife" ...).
    """
    if not raw:
        return ClubIdentity(core="")

    text = squash(raw)
    state = state_hint.strip().upper() if state_hint else None
    country: str | None = None

    # Parentheticals: "(URU)" / "(PI)" carry region info, "(antigo ...)" is noise.
    for content in _PAREN_RE.findall(text):
        token = content.replace(".", "").strip()
        if len(token) == 2 and token.upper() in STATE_ABBREVS:
            state = state or token.upper()
        elif len(token) == 3 and token.upper() in COUNTRY_ABBREVS:
            country = token.upper()
    text = _PAREN_RE.sub(" ", text)

    tokens = [t for t in _TOKEN_RE.split(text) if t]

    # Trailing state / country suffix ("palmeiras-sp" -> "palmeiras" + SP).
    if len(tokens) > 1 and tokens[-1].upper() in STATE_ABBREVS:
        state = tokens[-1].upper()
        tokens = tokens[:-1]
    elif len(tokens) > 1 and tokens[-1].upper() in COUNTRY_ABBREVS:
        country = tokens[-1].upper()
        tokens = tokens[:-1]

    # Dotted abbreviations: "a.b.c." -> "abc", "s.c" -> "sc" (a form word).
    tokens = [t.replace(".", "") for t in tokens]
    tokens = [t for t in tokens if t]

    pre = " ".join(tokens)

    # Alias lookup BEFORE form stripping (protects "Sport Recife").
    hit = ALIASES.get((pre, state))
    if hit:
        core, state = hit
        return ClubIdentity(core=core, state=state, country=country)

    # Form-word stripping, but never for protected cores and never down to "".
    if pre not in _PROTECTED_CORES:
        while len(tokens) > 1 and tokens[0] in _FORM_WORDS:
            tokens = tokens[1:]
        while len(tokens) > 1 and tokens[-1] in _FORM_WORDS:
            tokens = tokens[:-1]
        while len(tokens) > 1 and len(tokens[-1]) == 1:  # "... Esporte C"
            tokens = tokens[:-1]

    core = " ".join(tokens)

    # Alias lookup AFTER form stripping ("Fortaleza FC" -> "fortaleza").
    hit = ALIASES.get((core, state))
    if hit:
        core, state = hit

    core = CORE_ALIAS.get(core, core)
    return ClubIdentity(core=core, state=state, country=country)


class ClubNormalizer:
    """
    Two-pass club-name resolver.

    Pass 1 (:meth:`register`): every raw name seen in the data is parsed and,
    when it carries a region, counted under ``core -> region``.  Pass 2
    (:meth:`finalize`): for cores seen without a region, the dominant region
    from pass 1 is adopted - so the stateless "Santos" of the BR-Football
    file resolves to Santos-SP (hundreds of matches) rather than Santos-AP
    (a handful).  After finalize, :meth:`identity` / :meth:`key` produce the
    canonical identity/key used by the registry, the loader's dedup step and
    every user query.
    """

    def __init__(self) -> None:
        self._region_votes: dict[str, dict[str, int]] = {}
        self._dominant: dict[str, str] = {}
        self._finalized = False

    # -- pass 1 ------------------------------------------------------------

    def register(self, raw: str, state_hint: str | None = None) -> ClubIdentity:
        """Parse a raw name and record its region vote."""
        ident = parse_club_name(raw, state_hint)
        if ident.core and ident.region:
            votes = self._region_votes.setdefault(ident.core, {})
            votes[ident.region] = votes.get(ident.region, 0) + 1
        return ident

    # -- pass 2 ------------------------------------------------------------

    def finalize(self) -> None:
        """Compute the dominant region per core (deterministic ordering)."""
        self._dominant = {
            core: min(votes.items(), key=lambda kv: (-kv[1], kv[0]))[0]
            for core, votes in self._region_votes.items()
        }
        self._finalized = True

    # -- resolution ----------------------------------------------------------

    def identity(self, raw: str, state_hint: str | None = None) -> ClubIdentity:
        """Canonical identity for a raw name (stateless cores adopt the dominant region)."""
        ident = parse_club_name(raw, state_hint)
        if ident.core and not ident.region and not self._finalized:
            raise RuntimeError("ClubNormalizer.finalize() must be called first")
        if ident.core and not ident.region and ident.core in self._dominant:
            region = self._dominant[ident.core]
            if region in STATE_ABBREVS:
                ident = replace(ident, state=region)
            else:
                ident = replace(ident, country=region)
        return ident

    def key(self, raw: str, state_hint: str | None = None) -> str:
        return self.identity(raw, state_hint).key()

    def dominant_region(self, core: str) -> str | None:
        return self._dominant.get(core)


def canonical_key(raw: str, state_hint: str | None = None) -> str:
    """One-shot canonical key (no dominant-region resolution)."""
    return parse_club_name(raw, state_hint).key()


# --------------------------------------------------------------------------
# Competitions
# --------------------------------------------------------------------------

#: Canonical competition registry.  "sources" documents which files feed it.
COMPETITIONS: dict[str, dict] = {
    "serie_a": {
        "display": "Brasileirão Série A",
        "description": "Brazilian top-flight league (2003-2023 in this dataset)",
        "aliases": [
            "serie a",
            "brasileirao",
            "brasileirao serie a",
            "serie-a",
            "campeonato brasileiro",
            "serie a brasil",
            "brasileirão",
            "a",
            "serie a (brazil)",
            "serie a brazilian",
        ],
    },
    "serie_b": {
        "display": "Brasileirão Série B",
        "description": "Brazilian second division (2014-2023)",
        "aliases": ["serie b", "serie-b", "brasileirao serie b", "b", "serie b brasil"],
    },
    "serie_c": {
        "display": "Brasileirão Série C",
        "description": "Brazilian third division (2014-2023)",
        "aliases": ["serie c", "serie-c", "brasileirao serie c", "c", "serie c brasil"],
    },
    "copa_do_brasil": {
        "display": "Copa do Brasil",
        "description": "Brazilian national cup (2012-2023)",
        "aliases": [
            "copa do brasil",
            "brazilian cup",
            "cdb",
            "copa",
            "copa do brasil cup",
            "copa brasil",
            "cup of brazil",
        ],
    },
    "libertadores": {
        "display": "Copa Libertadores",
        "description": "CONMEBOL continental championship (2013-2022)",
        "aliases": [
            "libertadores",
            "copa libertadores",
            "conmebol libertadores",
            "libertadores da america",
            "copa libertadores da america",
            "conmebol",
            "libertadores cup",
        ],
    },
}

_ALIASES_TO_ID: dict[str, str] = {
    alias: comp_id
    for comp_id, meta in COMPETITIONS.items()
    for alias in meta["aliases"]
}


def normalize_competition(text: str | None) -> str | None:
    """
    Map free text ("the brasileirão", "CDB", "Série A") to a canonical
    competition id.  Returns ``None`` when nothing matches; 'all'/'any'/'
    every competition' map to ``"all"``.
    """
    if text is None:
        return None
    cleaned = squash(text).replace("the ", "").strip()
    if not cleaned:
        return None
    if cleaned in {
        "all",
        "any",
        "*",
        "every competition",
        "all competitions",
        "everything",
    }:
        return "all"
    if cleaned in COMPETITIONS:  # the canonical id itself (serie_a, ...)
        return cleaned
    hit = _ALIASES_TO_ID.get(cleaned)
    if hit:
        return hit
    # Longer aliases may appear inside a phrase ("who won the 2019
    # libertadores"); single-letter shortcuts ('a', 'b', 'c') only match
    # exactly, or they would fire inside unrelated words.
    for alias, comp_id in sorted(_ALIASES_TO_ID.items(), key=lambda kv: -len(kv[0])):
        if len(alias) >= 4 and alias in cleaned:
            return comp_id
    return None


# --------------------------------------------------------------------------
# Cell parsing helpers
# --------------------------------------------------------------------------

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y")


def parse_date(value: str | None) -> _dt.date | None:
    """Parse the date conventions used across the datasets; None if unparseable."""
    if not value:
        return None
    value = value.strip()
    if not value or value.upper() in {"NA", "N/A", "-"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            # Calendar dates, not timestamps: naive by design.
            return _dt.datetime.strptime(value, fmt).date()  # noqa: DTZ007
        except ValueError:
            continue
    return None


def parse_time(value: str | None) -> str | None:
    """Return HH:MM for kick-off cells like '20:00:00'."""
    if not value:
        return None
    value = value.strip()
    if not value or value.upper() in {"NA", "-"}:
        return None
    match = re.match(r"^(\d{1,2}):(\d{2})", value)
    return f"{int(match.group(1)):02d}:{match.group(2)}" if match else None


def parse_goals(value: str | None) -> int | None:
    """
    Parse a goals cell.  'NA' and '-' mean the match was scheduled but not
    played - returned as ``None`` so statistics can skip it.
    """
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.upper() in {"NA", "N/A", "-"}:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def parse_money(value: str | None) -> int | None:
    """Parse FIFA money cells like '€110.5M' / '€565K' into whole euros."""
    if not value:
        return None
    value = str(value).strip()
    match = re.match(r"^[€$£]?([\d.,]+)\s*([KMB]?)", value, re.IGNORECASE)
    if not match:
        return None
    number = float(match.group(1).replace(",", ""))
    scale = match.group(2).upper()
    multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(scale, 1)
    return int(number * multiplier)
