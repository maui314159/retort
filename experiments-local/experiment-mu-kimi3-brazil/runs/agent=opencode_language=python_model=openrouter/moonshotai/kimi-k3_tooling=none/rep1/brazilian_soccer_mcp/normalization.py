"""Name and date normalization helpers.

The source datasets use inconsistent conventions for the same real-world
teams (``Palmeiras-SP`` vs ``Palmeiras`` vs ``Palmeiras SP``) and several
date formats (ISO, ISO with time, Brazilian DD/MM/YYYY).

Matching strategy: the *state/country suffix is retained* in the lookup key
by default, because many Brazilian clubs share a base name (``Botafogo RJ``
vs ``Botafogo PB``, ``Atletico - ES`` vs ``Atletico - PR``, ``Fluminense
PI`` vs ``Fluminense RJ``).  An explicit alias table then merges the known
spelling variants of each notable club into one canonical key.  Unknown
suffixed names stay distinct, which errs on the safe side.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

__all__ = [
    "clean_team_name",
    "team_key",
    "canonical_display",
    "strip_accents",
    "text_key",
    "parse_date",
    "CANONICAL_DISPLAY",
]

_PARENS_RE = re.compile(r"\s*\([^)]*\)")
_PARENS_COUNTRY_RE = re.compile(r"\s*\(([A-Z]{2,4})\)")
_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]")
# Trailing state/country code, dash- or space-separated: "-SP", " - RJ", " RJ".
_STATE_SUFFIX_RE = re.compile(r"^(?P<base>.*?)\s*[-–]?\s+(?P<uf>[A-Z]{2,3})$")
_DASH_SUFFIX_RE = re.compile(r"\s*[-–]\s*(?P<uf>[A-Z]{2,3})\s*$")


def strip_accents(value: str) -> str:
    """Return *value* with diacritics removed (``São Paulo`` -> ``Sao Paulo``)."""
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _alnum(value: str) -> str:
    return _NON_ALNUM_RE.sub("", strip_accents(value).lower())


# ---------------------------------------------------------------------------
# Alias tables
#
# Keys are accent-stripped lowercase alphanumerics of the *full* team name
# (state suffix retained).  Values are canonical keys.  Only well-known
# variants are merged; everything else keeps its full key.
# ---------------------------------------------------------------------------

def _build_aliases() -> dict[str, str]:
    table: dict[str, str] = {}

    def add(canonical: str, *variants: str) -> None:
        for variant in variants:
            table[_alnum(variant)] = canonical

    add("flamengo", "Flamengo", "Flamengo-RJ", "Flamengo RJ")
    add("fluminense", "Fluminense", "Fluminense-RJ", "Fluminense RJ")
    add("botafogo", "Botafogo", "Botafogo-RJ", "Botafogo RJ")
    add("vasco", "Vasco", "Vasco da Gama", "Vasco-RJ", "Vasco Da Gama RJ")
    add("palmeiras", "Palmeiras", "Palmeiras-SP", "Palmeiras SP")
    add("corinthians", "Corinthians", "Corinthians-SP", "Corinthians SP")
    add("saopaulo", "São Paulo", "Sao Paulo", "São Paulo-SP", "Sao Paulo SP")
    add("santos", "Santos", "Santos-SP", "Santos SP")
    add("gremio", "Grêmio", "Gremio", "Grêmio-RS", "Gremio RS")
    add("internacional", "Internacional", "Internacional-RS", "Internacional RS")
    add(
        "atleticomineiro",
        "Atlético Mineiro", "Atletico Mineiro", "Atlético-MG", "Atletico-MG",
        "Atletico MG", "Atlético Mineiro - MG",
    )
    add(
        "athleticoparanaense",
        "Athletico Paranaense", "Atlético Paranaense", "Atletico Paranaense",
        "Athletico", "Atletico",  # bare forms used in some files
        "Atletico-PR", "Athletico-PR", "Atlético-PR", "Atletico PR",
        "Athletico Paranaense - PR", "Atlético Paranaense - PR",
    )
    add(
        "atleticogoianiense",
        "Atlético Goianiense", "Atletico Goianiense",
        "Atlético-GO", "Atletico-GO", "Atletico GO", "Atlético GO",
    )
    add("cruzeiro", "Cruzeiro", "Cruzeiro-MG", "Cruzeiro MG")
    add("bahia", "Bahia", "Bahia-BA", "Bahia BA")
    add(
        "sportrecife",
        "Sport", "Sport-PE", "Sport Recife", "Sport Recife-PE",
        "Sport Club do Recife",
    )
    add(
        "americamineiro",
        "América Mineiro", "America Mineiro", "América-MG", "America-MG",
        "America MG", "América - MG", "America - MG", "América", "America",
    )
    add(
        "americanatal",
        "América de Natal", "América-RN", "America-RN", "America RN",
        "América - RN", "America FC Natal", "América de Natal - RN",
    )
    add("coritiba", "Coritiba", "Coritiba-PR", "Coritiba PR")
    add("ceara", "Ceará", "Ceara", "Ceará-CE", "Ceara-CE", "Ceará Sporting Club")
    add(
        "fortaleza",
        "Fortaleza", "Fortaleza-CE", "Fortaleza CE", "Fortaleza EC",
        "Fortaleza FC", "Fortaleza Esporte Clube",
    )
    add("vitoria", "Vitória", "Vitoria", "Vitória-BA", "Vitoria BA", "Vitoria EC")
    add("chapecoense", "Chapecoense", "Chapecoense-SC", "Chapecoense SC")
    add("avai", "Avaí", "Avai", "Avaí-SC", "Avai-SC", "Avai SC")
    add("figueirense", "Figueirense", "Figueirense-SC", "Figueirense SC")
    add("criciuma", "Criciúma", "Criciuma", "Criciúma-SC", "Criciuma-SC")
    add("juventude", "Juventude", "Juventude-RS", "Juventude RS")
    add("goias", "Goiás", "Goias", "Goiás-GO", "Goias-GO", "Goias GO")
    add("cuiaba", "Cuiabá", "Cuiaba", "Cuiabá-MT", "Cuiaba-MT", "Cuiaba MT")
    add("csa", "CSA", "Csa-AL", "CSA-AL", "CSA AL")
    add("pontepreta", "Ponte Preta", "Ponte Preta-SP", "Ponte Preta SP")
    add("parana", "Paraná", "Parana", "Paraná-PR", "Parana-PR", "Paraná Clube")
    add("nautico", "Náutico", "Nautico", "Náutico-PE", "Nautico-PE", "Nautico PE")
    add("guarani", "Guarani", "Guarani-SP", "Guarani SP")
    add("portuguesa", "Portuguesa", "Portuguesa-SP", "Portuguesa SP")
    add(
        "bragantino",
        "Bragantino", "Bragantino-SP", "Bragantino SP",
        "Red Bull Bragantino", "Red Bull Bragantino-SP",
    )
    add("madureira", "Madureira", "Madureira-RJ", "Madureira RJ", "Madureira EC")
    add(
        "boavistarj",
        "Boavista-RJ", "Boavista RJ", "Boavista Sport Club",
        "Boavista Sport Club - RJ",
    )
    add("operarioms", "Operário-MS", "Operario-MS", "Operario MS", "Operario FC MS")
    add("abc", "ABC", "ABC-RN", "ABC RN", "A.b.c. - RN", "Abc - RN")
    add("asaal", "ASA", "Asa-AL", "Asa - AL", "ASA AL", "A.s.a. - AL")
    add("trem", "Trem", "Trem-AP", "Trem AP")
    add("saojosers", "São José-RS", "Sao Jose RS", "Sao Jose - POA", "São José - RS")
    add("caxias", "Caxias", "Caxias-RS", "Caxias RS")
    add(
        "duquedecaxias",
        "Duque de Caxias", "Duque De Caxias RJ", "Duque de Caxias FC",
        "Duque de Caxias-RJ",
    )
    add("barcelona", "Barcelona-EQU", "Barcelona SC", "Barcelona-Ecuador")
    add("santacruz", "Santa Cruz", "Santa Cruz-PE", "Santa Cruz PE")
    # "EC <Name>" spellings used by the BR-Football file for major clubs.
    add("bahia", "EC Bahia", "Esporte Clube Bahia")
    add("vitoria", "EC Vitoria", "EC Vitória", "Esporte Clube Vitória")
    add("juventude", "EC Juventude", "Esporte Clube Juventude")
    # Small clubs with divergent spellings across files.
    add("confianca", "Confiança", "Confianca", "Confianca SE", "AD Confianca",
        "Confiança-SE")
    add("altos", "Altos", "Altos-PI", "Altos - PI", "AE Altos")
    return table


_ALIASES = _build_aliases()

# Preferred display names for canonical keys.
CANONICAL_DISPLAY: dict[str, str] = {
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "botafogo": "Botafogo",
    "vasco": "Vasco da Gama",
    "palmeiras": "Palmeiras",
    "corinthians": "Corinthians",
    "saopaulo": "São Paulo",
    "santos": "Santos",
    "gremio": "Grêmio",
    "internacional": "Internacional",
    "atleticomineiro": "Atlético Mineiro",
    "athleticoparanaense": "Athletico Paranaense",
    "atleticogoianiense": "Atlético Goianiense",
    "cruzeiro": "Cruzeiro",
    "bahia": "Bahia",
    "sportrecife": "Sport Recife",
    "americamineiro": "América Mineiro",
    "americanatal": "América de Natal",
    "coritiba": "Coritiba",
    "ceara": "Ceará",
    "fortaleza": "Fortaleza",
    "vitoria": "Vitória",
    "chapecoense": "Chapecoense",
    "avai": "Avaí",
    "figueirense": "Figueirense",
    "criciuma": "Criciúma",
    "juventude": "Juventude",
    "goias": "Goiás",
    "cuiaba": "Cuiabá",
    "csa": "CSA",
    "pontepreta": "Ponte Preta",
    "parana": "Paraná",
    "nautico": "Náutico",
    "guarani": "Guarani",
    "portuguesa": "Portuguesa",
    "bragantino": "Bragantino",
    "madureira": "Madureira",
    "boavistarj": "Boavista",
    "operarioms": "Operário (MS)",
    "abc": "ABC",
    "asaal": "ASA",
    "trem": "Trem",
    "saojosers": "São José (RS)",
    "caxias": "Caxias",
    "duquedecaxias": "Duque de Caxias",
    "barcelona": "Barcelona SC",
    "santacruz": "Santa Cruz",
}


def _strip_parens(text: str) -> str:
    # Country codes in parentheses disambiguate clubs (``Nacional (PAR)`` vs
    # ``Nacional (URU)``) — promote them to a suffix instead of dropping them.
    text = _PARENS_COUNTRY_RE.sub(r" \1", text)
    return _WHITESPACE_RE.sub(" ", _PARENS_RE.sub(" ", text)).strip()


def _normalize_dash_suffix(text: str) -> str:
    """Unify ``Boavista - RJ`` -> ``Boavista RJ`` (dash -> space)."""
    match = _DASH_SUFFIX_RE.search(text)
    if match:
        return text[: match.start()].strip() + " " + match.group("uf").upper()
    return text


def clean_team_name(raw: object) -> str:
    """Human-readable team name with dataset noise removed.

    Removes parenthetical notes and normalizes dash-separated state suffixes
    to space-separated ones.  The suffix itself is *kept* for display because
    it disambiguates same-named clubs (``Botafogo SP`` vs ``Botafogo RJ``).
    """
    text = unicodedata.normalize("NFC", str(raw if raw is not None else "")).strip()
    text = _strip_parens(text)
    return _normalize_dash_suffix(text)


def team_key(raw: object) -> str:
    """Canonical matching key for a team name in any supported variation."""
    text = _strip_parens(unicodedata.normalize("NFC", str(raw if raw is not None else "")).strip())
    text = _normalize_dash_suffix(text)
    full = _alnum(text)
    if not full:
        return ""
    aliased = _ALIASES.get(full)
    if aliased is not None:
        return aliased
    return full


def canonical_display(key: str, fallback: str) -> str:
    """Preferred display name for a canonical *key* (aliases resolved)."""
    return CANONICAL_DISPLAY.get(key, fallback)


def text_key(raw: object) -> str:
    """Accent-insensitive lowercase key for free-text matching (clubs, names)."""
    return strip_accents(str(raw if raw is not None else "")).lower()


def parse_date(value: object) -> date | None:
    """Parse the date formats used across the datasets.

    Supported: ISO ``2023-09-24``, ISO with time ``2012-05-19 18:30:00`` and
    Brazilian ``29/03/2003``.  Returns ``None`` for unparseable input.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
