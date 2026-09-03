"""Normalisation helpers for the Brazilian soccer datasets.

The Kaggle datasets reuse several incompatible conventions for team names,
competition names and dates.  Brazilian clubs are particularly messy:

* the same club is written ``"Atlético-MG"``, ``"Atletico Mineiro"`` or
  ``"Atlético Mineiro - MG"`` depending on the file;
* distinct clubs share a nickname (``"Botafogo-RJ"`` vs ``"Botafogo-SP"``,
  ``"Atlético-MG"`` vs ``"Atlético-GO"`` vs ``"Atlético-PR"``) and are only
  disambiguated by their state suffix;
* club suffix tokens (``"EC"``, ``"FC"``, ``"SC"``) are sometimes present.

To handle this :func:`normalize_team_name` first reduces a raw name to a
*generic* form (parenthetical notes dropped, accents stripped, lowercased, dash
turned into a space, short club tokens removed, state tokens *kept*) and then
looks the result up in :data:`ALIASES` which collapses all known variants of a
club onto a single canonical key.  Distinct same-named clubs keep their state
in the canonical key (``"atletico mg"`` vs ``"atletico go"``), while unambiguous
clubs drop it (``"palmeiras"``).

Date strings in ISO (``2023-09-24``), Brazilian (``29/03/2003``) and
ISO-with-time (``2012-05-19 18:30:00``) formats are all parsed to
:class:`datetime.date` objects by :func:`parse_date`.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

BRAZILIAN_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

_PAREN_RE = re.compile(r"\([^)]*\)")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9 ]+")
_CLUB_SUFFIX_TOKENS = {"fc", "ec", "sc", "cf", "ac", "cb"}


def strip_accents(text: str) -> str:
    """Return *text* with combining diacritical marks removed (ASCII folded)."""
    if not text:
        return ""
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if not unicodedata.combining(ch)
    )


def _generic(name: str) -> str:
    """Reduce *name* to its pre-alias generic form (state tokens kept)."""
    if not name:
        return ""
    s = str(name).strip()
    s = _PAREN_RE.sub("", s)
    s = strip_accents(s)
    s = s.lower()
    s = _NON_ALNUM_RE.sub(" ", s)
    s = " ".join(t for t in s.split() if t not in _CLUB_SUFFIX_TOKENS)
    return s


_CLUBS: dict[str, tuple[str, tuple[str, ...]]] = {
    "flamengo": ("Flamengo", ("flamengo", "flamengo rj")),
    "fluminense": ("Fluminense", ("fluminense", "fluminense rj")),
    "vasco da gama": ("Vasco da Gama",
                      ("vasco", "vasco da gama", "vasco da gama rj", "vasco rj")),
    "botafogo": ("Botafogo",
                 ("botafogo", "botafogo rj", "botafogo fr", "botafogo fr rj")),
    "corinthians": ("Corinthians",
                   ("corinthians", "corinthians sp")),
    "palmeiras": ("Palmeiras", ("palmeiras", "palmeiras sp")),
    "sao paulo": ("São Paulo", ("sao paulo", "sao paulo sp", "sao paulo fc")),
    "santos": ("Santos", ("santos", "santos sp", "santos fc")),
    "atletico mg": ("Atlético Mineiro",
                    ("atletico mg", "atletico mineiro", "atletico mineiro mg",
                     "clube atletico mineiro", "athletic club mg", "atletico")),
    "cruzeiro": ("Cruzeiro",
                 ("cruzeiro", "cruzeiro mg", "cruzeiro esporte clube")),
    "america mg": ("América-MG",
                   ("america mg", "america mineiro", "america mineiro mg",
                    "america fc minas gerais", "america")),
    "atletico go": ("Atlético Goianiense",
                    ("atletico go", "atletico goianiense", "atletico goiania",
                     "goianiense goias", "ac goianiense goias")),
    "goias": ("Goiás", ("goias", "goias go", "goias ec", "goias esporte clube")),
    "gremio": ("Grêmio", ("gremio", "gremio rs", "gremio rs 1")),
    "internacional": ("Internacional",
                      ("internacional", "internacional rs", "sc internacional",
                       "inter")),
    "juventude": ("Juventude",
                  ("juventude", "juventude rs", "ec juventude")),
    "sport": ("Sport",
              ("sport", "sport pe", "sport recife", "sport club do recife",
               "sport club", "sport recife pe")),
    "nautico": ("Náutico",
                ("nautico", "nautico pe", "nautico capibaribe")),
    "santa cruz": ("Santa Cruz",
                   ("santa cruz", "santa cruz pe", "santa cruz fc")),
    "bahia": ("Bahia",
              ("bahia", "bahia ba", "ec bahia", "esporte clube bahia",
               "bahia ec", "bahia ef")),
    "vitoria": ("Vitória",
                ("vitoria", "vitoria ba", "ec vitoria", "vitoria ec",
                 "esporte clube vitoria")),
    "fortaleza": ("Fortaleza",
                  ("fortaleza", "fortaleza ce", "fortaleza ec", "fortaleza fc")),
    "ceara": ("Ceará",
              ("ceara", "ceara ce", "ceara sc", "ceara sporting club",
               "ceara sporting")),
    "chapecoense": ("Chapecoense", ("chapecoense", "chapecoense sc")),
    "avai": ("Avaí", ("avai", "avai sc")),
    "figueirense": ("Figueirense", ("figueirense", "figueirense sc")),
    "coritiba": ("Coritiba", ("coritiba", "coritiba pr", "coritiba fc")),
    "athletico pr": ("Athletico Paranaense",
                     ("athletico pr", "athletico paranaense",
                      "atletico paranaense", "athletico paranaense pr",
                      "atletico paranaense pr", "atletico pr",
                      "ca parana", "cap", "athletico")),
    "parana": ("Paraná", ("parana", "parana pr", "parana clube")),
    "ponte preta": ("Ponte Preta",
                    ("ponte preta", "ponte preta sp", "aa ponte preta")),
    "bragantino": ("Bragantino",
                   ("bragantino", "bragantino sp", "red bull bragantino",
                    "red bull bragantino sp", "rb bragantino")),
    "guarani": ("Guarani", ("guarani", "guarani sp")),
    "csa": ("CSA", ("csa", "csa al")),
    "crb": ("CRB", ("crb", "crb al")),
    "cuiaba": ("Cuiabá", ("cuiaba", "cuiaba mt", "cuiaba ec")),
    "sao bento": ("São Bento", ("sao bento", "sao bento sp")),
    "criciuma": ("Criciúma", ("criciuma", "criciuma sc")),
    "portuguesa": ("Portuguesa",
                   ("portuguesa", "portuguesa sp", "portuguesa desportos",
                    "paulista portuguesa")),
    "bangu": ("Bangu", ("bangu", "bangu rj")),
    "joinville": ("Joinville", ("joinville", "joinville sc")),
    "londrina": ("Londrina", ("londrina", "londrina pr")),
    "vila nova": ("Vila Nova",
                  ("vila nova", "vila nova go", "vila nova goiania")),
    "operario": ("Operário",
                 ("operario", "operario pr",
                  "operario ferroviario esporte c",
                  "operario ferroviario")),
    "america rj": ("América-RJ",
                   ("america rj", "america rj 1", "americano rj")),
    "america rn": ("América-RN",
                   ("america rn", "america fc natal", "america rn 1")),
    "sao jose": ("São José", ("sao jose", "sao jose sp", "sao jose rs")),
}


def _build_alias_tables():
    aliases: dict[str, str] = {}
    display: dict[str, str] = {}
    for canonical, (disp, variants) in _CLUBS.items():
        display[canonical] = disp
        for v in variants:
            aliases[v] = canonical
    return aliases, display


ALIASES, CLUB_DISPLAY = _build_alias_tables()


def normalize_team_name(name: str | None) -> str:
    """Return the canonical key for *name*.

    Generic reduction (state tokens kept, accents stripped, club tokens removed,
    dash -> space) followed by an alias lookup.  Unknown clubs fall back to
    their generic form, which is stable for consistent within-file naming.
    """
    generic = _generic(name)
    if not generic:
        return ""
    return ALIASES.get(generic, generic)


def display_team_name(name: str | None) -> str:
    """Return a human-readable team name, using the curated display form when
    the club is known and otherwise a cleaned (suffix-stripped) raw name."""
    if not name:
        return ""
    canonical = normalize_team_name(name)
    if canonical in CLUB_DISPLAY:
        return CLUB_DISPLAY[canonical]
    s = str(name).strip()
    s = _PAREN_RE.sub("", s).strip()
    s = re.sub(r"\s*-\s*[A-Z]{2,3}$", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s or str(name).strip()


def normalize_competition(name: str | None) -> str:
    """Canonical key for a competition name (accent-stripped + lowercased)."""
    if not name:
        return ""
    return _NON_ALNUM_RE.sub(" ", strip_accents(str(name)).lower()).strip()


def competition_matches(query: str | None, competition: str) -> bool:
    """Return True when *query* matches *competition* (accent-blind).

    Matching is substring-based after normalisation, so ``"Brasileirão"`` and
    ``"serie a"`` both match ``"Brasileirão Serie A"`` while ``"Brasileirão"``
    matches every Brasileirão series (A, B and C).  Empty / ``None`` queries match
    everything so callers can treat the argument as optional.  A small synonym
    table handles ``"copa brasil"`` / ``"brazilian cup"`` -> ``"copa do brasil"``.
    """
    if not query:
        return True
    q = normalize_competition(query)
    c = normalize_competition(competition)
    if q in c:
        return True
    synonyms = {
        "copa do brasil": ("copa brasil", "brazilian cup", "copa cup"),
        "copa libertadores": ("libertadores cup", "libertadores"),
    }
    for canonical, alts in synonyms.items():
        cn = normalize_competition(canonical)
        if (q == cn or q in alts) and (c == cn or cn in c):
            return True
    return False


_ISO_RE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
_DMY_RE = re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})")


def parse_date(value):
    """Parse a date string from any of the supported source formats.

    Supports ISO (``2023-09-24``), ISO with time (``2012-05-19 18:30:00``) and
    Brazilian (``29/03/2003``) formats.  Returns a :class:`datetime.date` (time
    component dropped) or ``None`` when the value is empty or unparseable.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    head = re.split(r"[ T]", s, 1)[0]
    m = _ISO_RE.fullmatch(head)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    m = _DMY_RE.fullmatch(head)
    if m:
        try:
            return date(int(m[3]), int(m[2]), int(m[1]))
        except ValueError:
            return None
    return None
