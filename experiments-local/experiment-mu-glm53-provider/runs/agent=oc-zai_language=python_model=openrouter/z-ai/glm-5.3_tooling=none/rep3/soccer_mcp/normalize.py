"""
soccer_mcp.normalize -- name, competition, date and position normalization.

CONTEXT
-------
This module implements the "Data Quality" requirements of the Brazilian Soccer
MCP Server specification (TASK.md / brazilian-soccer-mcp-guide.md):

* Team names appear in the six Kaggle CSV files under wildly different
  conventions:
      - with a state suffix ............. "Palmeiras-SP", "América - MG"
      - without a suffix ................ "Palmeiras", "Flamengo"
      - with dot-separated initials ..... "A.b.c. - RN", "C.r.b. - AL"
      - with full legal names ........... "Sport Club Corinthians Paulista"
      - with parenthetical remarks ...... "Boavista Sport Club (antigo ...)"
      - foreign clubs with country tags . "Nacional (URU)", "Barcelona-EQU"
  Every raw spelling must fold onto ONE canonical team id so that match
  records from different files can be joined.

* Dates appear as ISO ("2023-09-24"), ISO+time ("2012-05-19 18:30:00") and
  Brazilian ("29/03/2003") formats, plus the sentinel "NA".

* Competitions are referred to by many names ("Brasileirão", "Serie A",
  "Campeonato Brasileiro", "Copa do Brasil", "Libertadores", ...).

DESIGN
------
``parse_team_name`` decomposes a raw club name into ``(base, state, country)``
via a strict, order-sensitive pipeline (parenthetical extraction, country-tag
extraction, trailing-UF extraction, accent folding, punctuation cleanup,
single-letter-run collapsing).  An explicit ``ALIASES`` table then folds known
historical/branding renames (e.g. "Athletico Paranaense" -> Atlético-PR,
"Grêmio Prudente" -> Barueri).  States for *bare* spellings are auto-derived
by the TeamRegistry in ``data_loader`` (a base observed with exactly one state
inherits it, e.g. "Coritiba" -> PR); the small set of bases observed with
several states is resolved through ``FAMOUS_STATE_HINTS`` (e.g. "Flamengo" ->
RJ rather than PI).  Canonical ids look like ``"flamengo rj"``,
``"atletico pr"`` or ``"nacional uru"``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Basic text helpers
# ---------------------------------------------------------------------------


def strip_accents(value: str) -> str:
    """Return ``value`` with combining marks removed (NFD + Mn filtering)."""
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def text_key(value: str) -> str:
    """Case/accent-insensitive lookup key used for fuzzy name search."""
    return re.sub(r"\s+", " ", strip_accents(value).casefold()).strip()


# ---------------------------------------------------------------------------
# Team-name parsing
# ---------------------------------------------------------------------------

#: The 27 Brazilian federal-unit (UF) abbreviations.
VALID_UFS = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms",
    "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc",
    "sp", "se", "to",
}

#: Full state names sometimes written in parentheses, e.g. "América FC (Minas Gerais)".
STATE_NAMES = {
    "minas gerais": "mg",
    "sao paulo": "sp",
    "rio de janeiro": "rj",
    "rio grande do sul": "rs",
    "rio grande do norte": "rn",
    "santa catarina": "sc",
    "bahia": "ba",
    "ceara": "ce",
    "goias": "go",
    "para": "pa",
    "parana": "pr",
    "pernambuco": "pe",
    "piaui": "pi",
    "maranhao": "ma",
    "mato grosso": "mt",
    "mato grosso do sul": "ms",
    "amazonas": "am",
    "paraiba": "pb",
    "sergipe": "se",
    "alagoas": "al",
    "espirito santo": "es",
    "distrito federal": "df",
    "acre": "ac",
    "amapa": "ap",
    "rondonia": "ro",
    "roraima": "rr",
    "tocantins": "to",
}

#: South/Latin-American country codes used as suffixes in the Libertadores file.
COUNTRY_CODES = {"uru", "par", "equ", "per", "ven", "arg", "chi", "col", "bol", "mex", "ecu"}

_RE_TRAILING_PAREN = re.compile(r"\(([^)]*)\)\s*$")
_RE_COUNTRY_SUFFIX = re.compile(r"[-\u2013]\s*([A-Za-z]{3})$")
_RE_STATE_SUFFIX = re.compile(r"(?:^|\s|[-\u2013])\s*([A-Za-z]{2})\s*$")


@dataclass(frozen=True)
class ParsedTeamName:
    """Decomposed raw club name."""

    base: str
    state: str | None
    country: str | None

    @property
    def team_id(self) -> str:
        """Canonical id: ``"<base> <state|country>"`` (or bare base)."""
        suffix = self.state or self.country
        return f"{self.base} {suffix}" if suffix else self.base


def _collapse_single_letter_runs(base: str) -> str:
    """Join consecutive single-letter tokens: ``"c r b" -> "crb"``.

    Dot-separated abbreviations ("C. R. B.", "A.b.c.") lose their dots in
    ``_clean_base`` and end up as runs of one-letter tokens; they must fold to
    a single token so they match their undotted spellings ("CRB", "ABC").
    """
    tokens = base.split(" ")
    out: list[str] = []
    run: list[str] = []
    for token in tokens:
        if len(token) == 1:
            run.append(token)
            continue
        if run:
            out.append("".join(run))
            run = []
        out.append(token)
    if run:
        out.append("".join(run))
    return " ".join(out)


def _clean_base(raw: str) -> str:
    """Lowercase, accent-folded, punctuation-normalized club base name."""
    text = strip_accents(raw).casefold().strip()
    text = text.replace(".", "")  # "a.b.c." -> "abc", "s.francisco" -> "sfrancisco"
    text = re.sub(r"[^\w\s]", " ", text)  # hyphens, apostrophes, etc. -> spaces
    text = re.sub(r"\s+", " ", text).strip()
    return _collapse_single_letter_runs(text)


def parse_team_name(raw: str) -> ParsedTeamName:
    """Decompose a raw club spelling into ``base`` / ``state`` / ``country``.

    Order of operations (important -- suffixes must be peeled off before the
    base is cleaned):

    1. trailing ``-XXX`` country tag ("Barcelona-EQU");
    2. trailing 2-letter UF ("Palmeiras-SP", "América - MG", "Botafogo PB")
       -- also runs after step 3 so "X (antigo Y) - RJ" works;
    3. trailing parenthetical: a 2-letter UF ("(PI)"), a state name
       ("(Minas Gerais)") or a country code ("(URU)") is promoted to
       ``state``/``country``; anything else (e.g. "(antigo Esporte Clube
       Barreira)") is dropped as a remark.
    """
    text = raw.strip()
    state: str | None = None
    country: str | None = None

    match = _RE_COUNTRY_SUFFIX.search(text)
    if match and match.group(1).casefold() in COUNTRY_CODES:
        country = match.group(1).casefold()
        text = text[: match.start()].strip()

    if state is None and country is None:
        match = _RE_STATE_SUFFIX.search(text)
        if match and match.group(1).casefold() in VALID_UFS:
            state = match.group(1).casefold()
            text = text[: match.start()].strip()

    match = _RE_TRAILING_PAREN.search(text)
    if match:
        inner = strip_accents(match.group(1)).casefold().strip()
        text = text[: match.start()].strip()
        if inner in VALID_UFS and state is None:
            state = inner
        elif inner in STATE_NAMES and state is None:
            state = STATE_NAMES[inner]
        elif inner in COUNTRY_CODES and country is None:
            country = inner
        # any other parenthetical is a remark and is simply dropped

    if state is None and country is None:
        match = _RE_STATE_SUFFIX.search(text)
        if match and match.group(1).casefold() in VALID_UFS:
            state = match.group(1).casefold()
            text = text[: match.start()].strip()

    return ParsedTeamName(base=_clean_base(text), state=state, country=country)


#: Alias keys that must only fire for *bare* spellings (the base also exists
#: with a different state for another club, so a suffixed spelling must not be
#: hijacked).
BARE_ONLY_ALIASES = {("bragantino", None)}

#: Explicit folds for clubs whose *base* itself changes between sources.
#: Keys are ``(base, state_or_None)``.  A ``None`` key state means the rename
#: applies to any spelling of that base (bare or state-suffixed), unless the
#: key is listed in ``BARE_ONLY_ALIASES``.  Exact ``(base, state)`` keys are
#: state-specific merges.  Values are the canonical ``(base, state)``.
ALIASES: dict[tuple[str, str | None], tuple[str, str | None]] = {
    # -- Atlético family -----------------------------------------------------
    ("atletico mineiro", None): ("atletico", "mg"),
    ("atletico goianiense", None): ("atletico", "go"),
    ("atletico paranaense", None): ("atletico", "pr"),
    ("athletico paranaense", None): ("atletico", "pr"),
    ("athletico", None): ("atletico", "pr"),  # "Athletico" (Libertadores) = Athletico-PR
    ("atletico acreano", None): ("atletico", "ac"),
    ("atletico alagoinhas", None): ("atletico", "ba"),
    ("fc atletico cearense", None): ("atletico cearense", "ce"),
    # -- América family -------------------------------------------------------
    ("america fc", "mg"): ("america", "mg"),  # FIFA "América FC (Minas Gerais)"
    ("america fc natal", None): ("america", "rn"),
    ("america de natal", None): ("america", "rn"),
    # -- Rio / São Paulo classics ---------------------------------------------
    ("vasco", None): ("vasco da gama", None),
    ("sport club corinthians paulista", None): ("corinthians", "sp"),
    ("sport recife", None): ("sport", "pe"),
    ("sport club do recife", None): ("sport", "pe"),
    ("gremio prudente", None): ("barueri", "sp"),  # Barueri was renamed Grêmio Prudente in 2010
    ("gremio barueri", None): ("barueri", "sp"),
    ("gremio novorizontino", None): ("novorizontino", "sp"),
    ("bragantino", None): ("red bull bragantino", "sp"),  # bare "Bragantino" = RB Bragantino-SP
    ("bragantino", "sp"): ("red bull bragantino", "sp"),
    # -- state-specific merges (same club, different base spellings) ------------
    ("vitoria fc", "es"): ("vitoria", "es"),  # Cup "Vitoria F. C. - ES"
    ("parnahyba sc", "pi"): ("parnahyba", "pi"),  # Cup "Parnahyba S.c - PI"
    ("operario fc", "ms"): ("operario", "ms"),  # BR-Football "Operario FC MS"
    ("sfrancisco", "pa"): ("sao francisco", "pa"),  # Cup "S.francisco - PA"
    ("aguia", "pa"): ("aguia de maraba", "pa"),  # Cup "Aguia - PA"
    ("anapolis", "go"): ("anapolis fc", "go"),
    ("uniao", "mt"): ("uniao rondonopolis", "mt"),  # Cup "União - MT"
    ("brasil", "rs"): ("brasil de pelotas", "rs"),  # Cup "Brasil - RS"
    ("ec internacional", "sc"): ("internacional", "sc"),  # BR "EC Internacional SC"
    # -- clubs whose full/legal name appears in some sources --------------------
    ("ser caxias", None): ("caxias", "rs"),
    ("ceara sporting club", None): ("ceara", "ce"),
    ("nautico capibaribe", None): ("nautico", "pe"),
    ("santa cruz fc", None): ("santa cruz", "pe"),
    ("ec vitoria", None): ("vitoria", "ba"),
    ("vitoria ec", None): ("vitoria", "ba"),
    ("ec juventude", None): ("juventude", "rs"),
    ("portuguesa desportos", None): ("portuguesa", "sp"),
    ("macae esporte", None): ("macae", "rj"),
    ("esportivo bento goncalves", None): ("esportivo", "rs"),
    ("boavista sport club", None): ("boavista", "rj"),
    ("boavista sc saquarema", None): ("boavista", "rj"),
    ("operario ferroviario esporte c", None): ("operario", "pr"),
    ("ceo varzeagrandense", None): ("operario", "ms"),  # historic name of Operário-MS
    ("aquidauanense futebol clube", None): ("aquidauanense", "ms"),
    ("rio branco vn", None): ("rio branco", "es"),
    ("independente de tucurui", None): ("independente", "pa"),
    ("santa quiteria futebol clube", None): ("santa quiteria", "ma"),
    ("sao domingos futebol clube", None): ("sao domingos", "se"),
    ("arapongas esporte clube", None): ("arapongas", "pr"),
    ("paulista futebol clube", None): ("paulista", "sp"),
    ("desportiva ferroviaria", None): ("desportiva", "es"),
    ("real noroeste capixaba", None): ("real noroeste", "es"),
    ("flamengo do piaui", None): ("flamengo", "pi"),
    ("fluminense de feira", None): ("fluminense", "ba"),
    ("fortaleza fc", None): ("fortaleza", "ce"),
    ("fortaleza ec", None): ("fortaleza", "ce"),
    ("vitoria da conquista", None): ("vitoria da conquista", "ba"),
    ("madureira ec", None): ("madureira", "rj"),
    ("moto club de sao luis", None): ("moto club", "ma"),
    ("moto clube", None): ("moto club", "ma"),
    ("afogados da ingazeira", None): ("afogados", "pe"),
    ("ae altos", None): ("altos", "pi"),
    ("ad confianca", None): ("confianca", "se"),
    ("ad frei paulistano", None): ("frei paulistano", "se"),
    ("amadense ec", None): ("amadense", "se"),
    ("cordino ec", None): ("cordino", "ma"),
    ("tocantinopolis ec", None): ("tocantinopolis", "to"),
    ("toledo ec", None): ("toledo", "pr"),
    ("sinop fc", None): ("sinop", "mt"),
    ("sousa ec", None): ("sousa", "pb"),
    ("nova mutum ec", None): ("nova mutum", "mt"),
    ("nova venecia fc", None): ("nova venecia", "es"),
    ("porto velho ec", None): ("porto velho", "ro"),
    ("sc genus", None): ("genus", "ro"),
    ("ce aimore", None): ("aimore", "rs"),
    ("ce dom bosco", None): ("dom bosco", "mt"),
    ("ca votuporanguense", None): ("votuporanguense", "sp"),
    ("ca taguatinga", None): ("taguatinga", "df"),
    ("campinense clube", None): ("campinense", "pb"),
    ("cs alagoano", None): ("csa", "al"),
    ("sete de setembro", None): ("7 de setembro", "ms"),
    ("duque de caxias fc", None): ("duque de caxias", "rj"),
    ("uniao de rondonopolis", None): ("uniao rondonopolis", "mt"),
    ("brasilia fc", None): ("brasilia", "df"),
    ("se gama", None): ("gama", "df"),
    ("sao jose poa", None): ("sao jose", "rs"),  # "São José - POA" (Porto Alegre)
    ("xv piracicaba", None): ("xv de piracicaba", "sp"),
    ("tuntum ec", None): ("tuntum", "ma"),
    ("palmas fr", None): ("palmas", "to"),
    ("palmas ltda", None): ("palmas", "to"),
    ("clube do remo", None): ("remo", "pa"),
    ("retro fc brasil", None): ("retro", "pe"),
    ("ferroviario", None): ("ferroviario", "ce"),  # bare "Ferroviário" = CRF (CE)
    ("floresta ec", None): ("floresta", "ce"),
    ("guarani de juazeiro", None): ("guarani de juazeiro", "ce"),
    ("guarany de sobral", None): ("guarany de sobral", "ce"),
    ("inter de limeira", None): ("inter de limeira", "sp"),
    ("ge bage", None): ("bage", "rs"),
    ("ge gloria", None): ("gloria", "rs"),
    # foreign clubs whose spelling varies inside the Libertadores file
    ("tolima", None): ("deportes tolima", None),
}

#: States for the handful of *ambiguous* famous bases (the same base exists
#: with several states in the data).  Unambiguous bases inherit their state
#: automatically from the registry, so they are not listed here.
FAMOUS_STATE_HINTS: dict[str, str] = {
    "flamengo": "rj",       # also Flamengo-PI exists
    "fluminense": "rj",     # also Fluminense-BA / Fluminense-PI exist
    "botafogo": "rj",       # also Botafogo-PB / Botafogo-SP exist
    "santos": "sp",         # also Santos-AP exists
    "internacional": "rs",  # also Internacional-SC exists
    "juventude": "rs",      # also Juventude-MA exists
    "vitoria": "ba",        # also Vitória-ES exists
    "nautico": "pe",        # also Náutico-RR exists
    "santa cruz": "pe",     # also Santa Cruz-RN / Santa Cruz-RS exist
    "guarani": "sp",        # also Guarani-CE exists
    "portuguesa": "sp",     # also Portuguesa-RJ exists
}

#: Foreign clubs whose bare name collides with an obscure Brazilian club of
#: the same base (River Plate-SE, Peñarol-AM).  These must NOT inherit a
#: Brazilian state; they stay stateless so the famous foreign club and the
#: small Brazilian club remain separate entities.
FOREIGN_BARE_NAMES = {"river plate", "penarol"}

#: Popular nicknames accepted as queries (not present in the raw data).
NICKNAMES: dict[str, str] = {
    "fla": "flamengo rj",
    "mengao": "flamengo rj",
    "flu": "fluminense rj",
    "tricolor carioca": "fluminense rj",
    "timao": "corinthians sp",
    "verdao": "palmeiras sp",
    "galo": "atletico mg",
    "furacao": "atletico pr",
    "peixe": "santos sp",
    "fogao": "botafogo rj",
    "leao": "sport pe",
    "tricolor paulista": "sao paulo sp",
    "nao": "nautico pe",
    "raposa": "cruzeiro mg",
}


def apply_aliases(parsed: ParsedTeamName) -> ParsedTeamName:
    """Fold known base-name renames onto the canonical base/state.

    Exact ``(base, state)`` entries always win.  ``(base, None)`` entries are
    base renames that apply to any spelling (bare or suffixed), except for the
    few keys in ``BARE_ONLY_ALIASES`` which must only fire for bare spellings
    (e.g. "Bragantino" alone means RB Bragantino-SP, but "Bragantino-PA" is a
    different club in Pará).
    """
    folded = ALIASES.get((parsed.base, parsed.state))
    if folded is None:
        candidate = ALIASES.get((parsed.base, None))
        if candidate is not None and (
            parsed.state is None or (parsed.base, None) not in BARE_ONLY_ALIASES
        ):
            folded = candidate
    if folded is None:
        return parsed
    new_base, new_state = folded
    state = new_state if new_state is not None else parsed.state
    return ParsedTeamName(base=new_base, state=state, country=parsed.country)


def canonical_team_name(raw: str, *, registry_states: dict[str, set[str]] | None = None) -> ParsedTeamName:
    """Fold a raw club spelling onto its canonical ``(base, state, country)``.

    ``registry_states`` optionally maps a base to the set of states observed
    for it across all files; it lets *bare* spellings of non-ambiguous clubs
    inherit their state automatically (e.g. "Coritiba" -> PR because
    "Coritiba - PR" exists elsewhere).  Ambiguous bases fall back to
    ``FAMOUS_STATE_HINTS``; bases in ``FOREIGN_BARE_NAMES`` never inherit a
    Brazilian state.
    """
    parsed = apply_aliases(parse_team_name(raw))
    if parsed.state is not None or parsed.country is not None:
        return parsed
    if parsed.base in FOREIGN_BARE_NAMES:
        return parsed
    states = registry_states.get(parsed.base, set()) if registry_states else set()
    if len(states) == 1:
        return ParsedTeamName(base=parsed.base, state=next(iter(states)), country=None)
    hint = FAMOUS_STATE_HINTS.get(parsed.base)
    if hint is not None:
        return ParsedTeamName(base=parsed.base, state=hint, country=None)
    return parsed


# ---------------------------------------------------------------------------
# Competition normalization
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompetitionDef:
    """Static competition metadata."""

    id: str
    display: str
    type: str  # "league" | "cup"
    aliases: tuple[str, ...]


COMPETITIONS: dict[str, CompetitionDef] = {
    "serie_a": CompetitionDef(
        id="serie_a",
        display="Brasileirão Série A",
        type="league",
        aliases=(
            "serie a", "série a", "brasileirao", "brasileirão", "brasileirao serie a",
            "brasileirão série a", "campeonato brasileiro", "campeonato brasileiro serie a",
            "serie a (brasileirao)", "serie a brasileirao",
        ),
    ),
    "serie_b": CompetitionDef(
        id="serie_b",
        display="Brasileirão Série B",
        type="league",
        aliases=("serie b", "série b", "brasileirao serie b", "brasileirão série b",
                 "campeonato brasileiro serie b", "segunda divisao"),
    ),
    "serie_c": CompetitionDef(
        id="serie_c",
        display="Brasileirão Série C",
        type="league",
        aliases=("serie c", "série c", "brasileirao serie c", "brasileirão série c",
                 "campeonato brasileiro serie c", "terceira divisao"),
    ),
    "copa_do_brasil": CompetitionDef(
        id="copa_do_brasil",
        display="Copa do Brasil",
        type="cup",
        aliases=("copa do brasil", "brazilian cup", "copa nacional", "cdb"),
    ),
    "libertadores": CompetitionDef(
        id="libertadores",
        display="Copa Libertadores",
        type="cup",
        aliases=("libertadores", "copa libertadores", "conmebol libertadores",
                 "copa libertadores da america", "liberta"),
    ),
}

_COMP_LOOKUP: dict[str, str] = {}
for _comp in COMPETITIONS.values():
    _COMP_LOOKUP[text_key(_comp.id)] = _comp.id
    _COMP_LOOKUP[text_key(_comp.display)] = _comp.id
    for _alias in _comp.aliases:
        _COMP_LOOKUP[text_key(_alias)] = _comp.id


def normalize_competition(query: str | None) -> str | None:
    """Map a free-text competition reference onto a competition id."""
    if not query:
        return None
    key = text_key(query)
    if key in _COMP_LOOKUP:
        return _COMP_LOOKUP[key]
    for alias_key, comp_id in _COMP_LOOKUP.items():
        if alias_key and (alias_key in key or key in alias_key):
            return comp_id
    return None


# ---------------------------------------------------------------------------
# Date parsing / normalization
# ---------------------------------------------------------------------------

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M")


def parse_date_any(value: str | None) -> date | None:
    """Parse ISO, ISO+time and Brazilian (DD/MM/YYYY) date strings.

    Returns ``None`` for empty values and the "NA" sentinel used by the
    Libertadores file.
    """
    if not value:
        return None
    text = value.strip()
    if not text or text.upper() == "NA":
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Player-position normalization
# ---------------------------------------------------------------------------

POSITION_GROUPS: dict[str, tuple[str, ...]] = {
    "GK": ("GK",),
    "DEF": ("CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"),
    "MID": ("CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM", "LAM", "RAM", "LM", "RM"),
    "FWD": ("ST", "LS", "RS", "CF", "LW", "RW", "LF", "RF"),
}

_GROUP_BY_POSITION = {
    position: group for group, positions in POSITION_GROUPS.items() for position in positions
}


def position_group(position: str | None) -> str | None:
    """Map a raw FIFA position code to its group (GK/DEF/MID/FWD)."""
    if not position:
        return None
    return _GROUP_BY_POSITION.get(position.strip().upper())
