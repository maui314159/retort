"""Normalization utilities for Brazilian soccer data.

The six provided datasets spell club names in wildly different ways:

* ``"Palmeiras-SP"`` / ``"Palmeiras"`` / ``"palmeiras"``
* ``"Athletico Paranaense - PR"`` / ``"Atlético-PR"`` / ``"Athletico"``
* ``"América FC (Minas Gerais)"`` / ``"America - MG"``
* ``"Nacional (URU)"`` / ``"Nacional-URU"``

and dates in at least three formats (ISO, ISO+time, Brazilian DD/MM/YYYY).

This module turns every raw team name into a single *canonical key* so that
matches, players and queries can be joined reliably:

* Brazilian clubs use ``base-uf`` keys (``flamengo-rj``, ``atletico-mg``),
  where the UF comes from an explicit suffix in the data or from the
  built-in alias table below.
* International clubs keep their CONMEBOL country code when present
  (``nacional-uru``, ``barcelona-equ``) or fall back to the bare base
  (``boca juniors``).

It also provides multi-format date parsing, safe integer parsing for goal
columns (``"-"``/``"NA"`` appear in the Libertadores file), competition name
aliases, and the catalog of classic Brazilian derbies.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

UFS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
}

COUNTRY_CODES = {
    "ARG", "BOL", "CHI", "COL", "EQU", "MEX", "PAR", "PER", "URU", "VEN",
    "USA", "JPN", "KSA",
}

BASE_ALIASES: dict[str, tuple[str, str | None]] = {
    "flamengo": ("flamengo", "rj"),
    "fluminense": ("fluminense", "rj"),
    "vasco": ("vasco", "rj"),
    "vasco da gama": ("vasco", "rj"),
    "botafogo": ("botafogo", "rj"),
    "botafogo fr": ("botafogo", "rj"),
    "corinthians": ("corinthians", "sp"),
    "sc corinthians paulista": ("corinthians", "sp"),
    "sport club corinthians paulista": ("corinthians", "sp"),
    "palmeiras": ("palmeiras", "sp"),
    "se palmeiras": ("palmeiras", "sp"),
    "palmeiras sp": ("palmeiras", "sp"),
    "sao paulo": ("sao paulo", "sp"),
    "sao paulo fc": ("sao paulo", "sp"),
    "santos": ("santos", "sp"),
    "santos fc": ("santos", "sp"),
    "atletico mineiro": ("atletico", "mg"),
    "atlético mineiro": ("atletico", "mg"),
    "cruzeiro": ("cruzeiro", "mg"),
    "cruzeiro ec": ("cruzeiro", "mg"),
    "america fc": ("america", "mg"),
    "america mineiro": ("america", "mg"),
    "america mg": ("america", "mg"),
    "america de belo horizonte": ("america", "mg"),
    "america fc natal": ("america", "rn"),
    "atletico paranaense": ("atletico", "pr"),
    "athletico paranaense": ("atletico", "pr"),
    "athletico": ("atletico", "pr"),
    "club atletico paranaense": ("atletico", "pr"),
    "atletico goianiense": ("atletico", "go"),
    "atletico acreano": ("atletico", "ac"),
    "atletico alagoinhas": ("atletico", "ba"),
    "atletico cearense": ("atletico cearense", "ce"),
    "fc atletico cearense": ("atletico cearense", "ce"),
    "gremio": ("gremio", "rs"),
    "internacional": ("internacional", "rs"),
    "internacional sc": ("internacional", "rs"),
    "gremio fbpa": ("gremio", "rs"),
    "sport": ("sport", "pe"),
    "sport club do recife": ("sport", "pe"),
    "sport do recife": ("sport", "pe"),
    "sport recife": ("sport", "pe"),
    "santa cruz": ("santa cruz", "pe"),
    "santa cruz fc": ("santa cruz", "pe"),
    "nautico": ("nautico", "pe"),
    "nautico capibaribe": ("nautico", "pe"),
    "bahia": ("bahia", "ba"),
    "ec bahia": ("bahia", "ba"),
    "esporte clube bahia": ("bahia", "ba"),
    "vitoria": ("vitoria", "ba"),
    "ec vitoria": ("vitoria", "ba"),
    "vitoria ec": ("vitoria", "ba"),
    "esporte clube vitoria": ("vitoria", "ba"),
    "vitoria f c": ("vitoria", "es"),
    "vitoria fc": ("vitoria", "es"),
    "fortaleza": ("fortaleza", "ce"),
    "fortaleza ec": ("fortaleza", "ce"),
    "fortaleza fc": ("fortaleza", "ce"),
    "ceara": ("ceara", "ce"),
    "ceara sporting club": ("ceara", "ce"),
    "ceara sc": ("ceara", "ce"),
    "goias": ("goias", "go"),
    "goias ec": ("goias", "go"),
    "avai": ("avai", "sc"),
    "avai fc": ("avai", "sc"),
    "chapecoense": ("chapecoense", "sc"),
    "figueirense": ("figueirense", "sc"),
    "criciuma": ("criciuma", "sc"),
    "criciuma ec": ("criciuma", "sc"),
    "joinville": ("joinville", "sc"),
    "parana": ("parana", "pr"),
    "parana clube": ("parana", "pr"),
    "ca parana": ("parana", "pr"),
    "coritiba": ("coritiba", "pr"),
    "coritiba fc": ("coritiba", "pr"),
    "ponte preta": ("ponte preta", "sp"),
    "aa ponte preta": ("ponte preta", "sp"),
    "portuguesa": ("portuguesa", "sp"),
    "portuguesa sp": ("portuguesa", "sp"),
    "juventude": ("juventude", "rs"),
    "ec juventude": ("juventude", "rs"),
    "cuiaba": ("cuiaba", "mt"),
    "cuiaba ec": ("cuiaba", "mt"),
    "red bull bragantino": ("red bull bragantino", "sp"),
    "bragantino": ("red bull bragantino", "sp"),
    "csa": ("csa", "al"),
    "cs alagoano": ("csa", "al"),
    "centro sportivo alagoano": ("csa", "al"),
    "guarani": ("guarani", "sp"),
    "guarani fc": ("guarani", "sp"),
    "brasiliense": ("brasiliense", "df"),
    "ipatinga": ("ipatinga", "mg"),
    "barueri": ("barueri", "sp"),
    "gremio prudente": ("gremio prudente", "sp"),
    "america de natal": ("america", "rn"),
    "america rn": ("america", "rn"),
    "abc": ("abc", "rn"),
    "atletico madrid": ("atletico madrid", None),
    "athletico paranaense - pr": ("atletico", "pr"),
    "flamengo do piaui": ("flamengo", "pi"),
    "sao jose poa": ("sao jose", "rs"),
    "remo": ("remo", "pa"),
    "clube do remo": ("remo", "pa"),
    "paysandu": ("paysandu", "pa"),
    "tuna luso": ("tuna luso", "pa"),
    "portuguesa desportos": ("portuguesa", "sp"),
    "ferroviario": ("ferroviario", "ce"),
    "caxias": ("caxias", "rs"),
    "ser caxias": ("caxias", "rs"),
    "brasilia fc": ("brasilia", "df"),
    "vila nova": ("vila nova", "go"),
    "crb": ("crb", "al"),
    "asa": ("asa", "al"),
    "a s a": ("asa", "al"),
    "confianca": ("confianca", "se"),
    "ad confianca": ("confianca", "se"),
    "sampaio correa": ("sampaio correa", "ma"),
    "novorizontino": ("gremio novorizontino", "sp"),
    "gremio novorizontino": ("gremio novorizontino", "sp"),
    "ituano": ("ituano", "sp"),
    "santo andre": ("santo andre", "sp"),
    "sao caetano": ("sao caetano", "sp"),
    "mirassol": ("mirassol", "sp"),
    "oeste": ("oeste", "sp"),
    "londrina": ("londrina", "pr"),
    "maringa": ("maringa", "pr"),
    "cianorte": ("cianorte", "pr"),
    "tombense": ("tombense", "mg"),
    "tupi": ("tupi", "mg"),
    "uberlandia": ("uberlandia", "mg"),
    "boa": ("boa", "mg"),
    "anapolina": ("anapolina", "go"),
    "crac": ("crac", "go"),
    "goianesia": ("goianesia", "go"),
    "gama": ("gama", "df"),
    "se gama": ("gama", "df"),
    "bangu": ("bangu", "rj"),
    "nova iguacu": ("nova iguacu", "rj"),
    "volta redonda": ("volta redonda", "rj"),
    "madureira ec": ("madureira", "rj"),
    "boavista": ("boavista", "rj"),
    "boavista sport club": ("boavista", "rj"),
    "boavista sc saquarema": ("boavista", "rj"),
    "cabofriense": ("cabofriense", "rj"),
    "duque de caxias fc": ("duque de caxias", "rj"),
    "americano": ("americano", "rj"),
    "salgueiro": ("salgueiro", "pe"),
    "juazeirense": ("juazeirense", "ba"),
    "bahia de feira": ("bahia de feira", "ba"),
    "imperatriz": ("imperatriz", "ma"),
    "moto clube": ("moto club", "ma"),
    "moto club de sao luis": ("moto club", "ma"),
    "amazonas": ("amazonas", "am"),
    "manaus": ("manaus", "am"),
    "abc fc": ("abc", "rn"),
    "river": ("river", "pi"),
    "retro fc brasil": ("retro", "pe"),
    "guarany de sobral": ("guarany", "ce"),
    "afogados da ingazeira fc": ("afogados", "pe"),
    "esportivo bento goncalves": ("esportivo", "rs"),
    "ceo varzeagrandense": ("operario", "mt"),
    "peixe da amazonia": ("santos", "ap"),
    "brasil de pelotas": ("brasil", "rs"),
    "uniao": ("uniao de rondonopolis", "mt"),
    "inter de limeira": ("inter de limeira", "sp"),
    "sao bento": ("sao bento", "sp"),
    "sao bernardo": ("sao bernardo", "sp"),
    "sao jose rs": ("sao jose", "rs"),
    "macae": ("macae", "rj"),
    "macae esporte fc": ("macae", "rj"),
    "guaratingueta": ("guaratingueta", "sp"),
    "sao luiz": ("sao luiz", "rs"),
    "juventude ma": ("juventude", "ma"),
}

DISPLAY_NAMES: dict[str, str] = {
    "flamengo-rj": "Flamengo",
    "fluminense-rj": "Fluminense",
    "vasco-rj": "Vasco da Gama",
    "botafogo-rj": "Botafogo",
    "corinthians-sp": "Corinthians",
    "palmeiras-sp": "Palmeiras",
    "sao paulo-sp": "São Paulo",
    "santos-sp": "Santos",
    "atletico-mg": "Atlético Mineiro",
    "cruzeiro-mg": "Cruzeiro",
    "america-mg": "América Mineiro",
    "atletico-pr": "Athletico Paranaense",
    "gremio-rs": "Grêmio",
    "internacional-rs": "Internacional",
    "sport-pe": "Sport Recife",
    "santa cruz-pe": "Santa Cruz",
    "nautico-pe": "Náutico",
    "bahia-ba": "Bahia",
    "vitoria-ba": "Vitória",
    "fortaleza-ce": "Fortaleza",
    "ceara-ce": "Ceará",
    "goias-go": "Goiás",
    "avai-sc": "Avaí",
    "chapecoense-sc": "Chapecoense",
    "figueirense-sc": "Figueirense",
    "criciuma-sc": "Criciúma",
    "joinville-sc": "Joinville",
    "parana-pr": "Paraná",
    "coritiba-pr": "Coritiba",
    "ponte preta-sp": "Ponte Preta",
    "portuguesa-sp": "Portuguesa",
    "juventude-rs": "Juventude",
    "cuiaba-mt": "Cuiabá",
    "red bull bragantino-sp": "Red Bull Bragantino",
    "csa-al": "CSA",
    "guarani-sp": "Guarani",
    "brasiliense-df": "Brasiliense",
    "ipatinga-mg": "Ipatinga",
    "baruleri-sp": "Barueri",
    "barueri-sp": "Barueri",
    "gremio prudente-sp": "Grêmio Prudente",
    "america-rn": "América-RN",
    "abc-rn": "ABC",
    "brasil-rs": "Brasil de Pelotas",
}

COMPETITIONS = {
    "brasileirao serie a": "Brasileirão Série A",
    "serie a": "Brasileirão Série A",
    "brasileirao": "Brasileirão Série A",
    "brasileirão": "Brasileirão Série A",
    "campeonato brasileiro": "Brasileirão Série A",
    "campeonato brasileiro serie a": "Brasileirão Série A",
    "serie b": "Brasileirão Série B",
    "brasileirao serie b": "Brasileirão Série B",
    "serie c": "Brasileirão Série C",
    "brasileirao serie c": "Brasileirão Série C",
    "copa do brasil": "Copa do Brasil",
    "brazilian cup": "Copa do Brasil",
    "copa libertadores": "Copa Libertadores",
    "libertadores": "Copa Libertadores",
    "copa libertadores da america": "Copa Libertadores",
}

DERBY_PAIRS: list[tuple[str, str, str]] = [
    ("flamengo-rj", "fluminense-rj", "Fla-Flu"),
    ("flamengo-rj", "vasco-rj", "Clássico dos Milhões"),
    ("botafogo-rj", "fluminense-rj", "Clássico Vovô"),
    ("botafogo-rj", "vasco-rj", "Clássico dos Rivais"),
    ("corinthians-sp", "palmeiras-sp", "Derby Paulista"),
    ("corinthians-sp", "sao paulo-sp", "Majestoso"),
    ("palmeiras-sp", "sao paulo-sp", "Choque-Rei"),
    ("corinthians-sp", "santos-sp", "Clássico Alvinegro"),
    ("sao paulo-sp", "santos-sp", "Clássico San-São"),
    ("gremio-rs", "internacional-rs", "Gre-Nal"),
    ("atletico-mg", "cruzeiro-mg", "Clássico Mineiro"),
    ("bahia-ba", "vitoria-ba", "Ba-Vi"),
    ("atletico-pr", "coritiba-pr", "Atle-Tiba"),
    ("sport-pe", "nautico-pe", "Clássico dos Clássicos"),
    ("sport-pe", "santa cruz-pe", "Clássico das Multidões"),
    ("ceara-ce", "fortaleza-ce", "Clássico-Rei"),
]

_PARENTHESES_RE = re.compile(r"\(([^)]*)\)")
_TRAILING_DASH_RE = re.compile(r"\s*[-–]\s*([a-z]{2,3})\s*$")
_TRAILING_WORD_RE = re.compile(r"\s+([a-z]{2,3})\s*$")
_NON_ALPHA_RE = re.compile(r"[^a-z0-9\s]")


def strip_accents(text: str) -> str:
    """Return *text* with accents removed (NFD decomposition)."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _clean_base(text: str) -> str:
    """Lowercase, de-accent, strip punctuation and collapse whitespace."""
    text = strip_accents(text).lower().strip()
    text = _NON_ALPHA_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = text.split(" ")
    if len(tokens) > 1 and all(len(t) == 1 for t in tokens):
        text = "".join(tokens)
    return text


def canonical_team_key(raw_name: str) -> str:
    """Convert any raw team spelling into the canonical team key."""
    if not raw_name or not raw_name.strip():
        return ""
    cleaned = strip_accents(raw_name).lower().strip()

    country: str | None = None
    for inside in _PARENTHESES_RE.findall(cleaned):
        token = inside.strip().strip(".")
        if token.upper() in COUNTRY_CODES:
            country = token.upper()
    cleaned = _PARENTHESES_RE.sub(" ", cleaned)

    base = cleaned.strip()
    uf: str | None = None

    dash_match = _TRAILING_DASH_RE.search(base)
    if dash_match:
        suffix = dash_match.group(1).upper()
        if suffix in UFS:
            uf = suffix
            base = base[: dash_match.start()].strip()
        elif suffix in COUNTRY_CODES:
            country = suffix
            base = base[: dash_match.start()].strip()
    if uf is None:
        word_match = _TRAILING_WORD_RE.search(base)
        if word_match and word_match.group(1).upper() in UFS:
            uf = word_match.group(1).upper()
            base = base[: word_match.start()].strip()

    base = _clean_base(base)
    if not base:
        return ""

    if base in BASE_ALIASES:
        canonical_base, default_uf = BASE_ALIASES[base]
        if uf and default_uf and uf.lower() != default_uf:
            pass
        else:
            base = canonical_base
            uf = uf or default_uf

    if uf:
        return f"{base}-{uf.lower()}"
    if country:
        return f"{base}-{country.lower()}"
    return base


def team_display_name(key: str) -> str:
    """Human-friendly display name for a canonical team key."""
    if key in DISPLAY_NAMES:
        return DISPLAY_NAMES[key]
    if "-" in key:
        base, suffix = key.rsplit("-", 1)
        pretty = " ".join(w.capitalize() for w in base.split())
        return f"{pretty} ({suffix.upper()})"
    return " ".join(w.capitalize() for w in key.split())


def resolve_competition(raw: str | None) -> str | None:
    """Map a user-provided competition string to a canonical competition."""
    if not raw:
        return None
    cleaned = _clean_base(raw).replace("  ", " ").strip()
    direct = COMPETITIONS.get(cleaned)
    if direct:
        return direct
    for alias, canonical in COMPETITIONS.items():
        if alias in cleaned or cleaned in alias:
            return canonical
    return None


def parse_date(raw: str | None) -> date | None:
    """Parse ISO, ISO+time and Brazilian (DD/MM/YYYY) date strings."""
    if not raw:
        return None
    text = raw.strip()
    if text in {"", "NA", "None", "-"}:
        return None
    text = text.split(" ")[0] if "T" not in text else text.split("T")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_int(raw) -> int | None:
    """Parse an integer that may arrive as int, '2', '-' or 'NA'."""
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    text = str(raw).strip()
    if text in {"", "NA", "-", "None"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def normalize_round(competition: str, raw: str | None) -> str | None:
    """Human-friendly round label; maps Copa do Brasil numeric rounds."""
    value = parse_int(raw)
    if value is None:
        return str(raw).strip() if raw else None
    if competition == "Copa do Brasil":
        names = {
            5: "Round of 16",
            6: "Quarterfinal",
            7: "Semifinal",
            8: "Final",
        }
        return names.get(value, f"Round {value}")
    return f"Round {value}"
