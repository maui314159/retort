"""Team name normalization and canonicalization.

The six source datasets use wildly different naming conventions for the same
clubs:

- state suffix attached by hyphen: "Palmeiras-SP", "Grêmio-RS"
- state suffix attached by space: "America MG", "Gremio RS"
- spaced suffix with dash: "América - MG" (Copa do Brasil file)
- bare names: "Palmeiras", "Grêmio"
- official full names: "Sport Club Corinthians Paulista"
- foreign clubs with country tags: "Nacional (URU)", "Barcelona-EQU"

This module folds every variant onto a stable canonical id of the form
``base-uf`` (e.g. ``palmeiras-sp``), ``base-country`` (e.g. ``nacional-uru``)
or plain ``base`` (e.g. ``boca juniors``) so that queries match regardless of
the variant used.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict

BRAZILIAN_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

COUNTRY_CODES = {
    "ARG", "BOL", "CHI", "COL", "ECU", "EQU", "PAR", "PER", "URU", "VEN",
    "MEX", "USA", "JPN", "KOR", "CRC", "HON", "GUA", "SLV", "PAN", "CAN",
}

STATE_NAME_WORDS = {
    "rio grande do sul": "RS",
    "rio de janeiro": "RJ",
    "minas gerais": "MG",
    "espirito santo": "ES",
    "mato grosso do sul": "MS",
    "mato grosso": "MT",
}

STATE_ADJECTIVES = {
    "paulista": "SP", "carioca": "RJ", "mineiro": "MG", "paranaense": "PR",
    "gaucho": "RS", "baiano": "BA", "cearense": "CE", "goiano": "GO",
    "pernambucano": "PE", "potiguar": "RN", "amazonense": "AM",
    "matogrossense": "MT", "paraense": "PA", "piauiense": "PI",
    "alagoano": "AL", "sergipano": "SE", "paraibano": "PB", "capixaba": "ES",
    "catarinense": "SC", "maranhense": "MA", "rondoniense": "RO",
    "acreano": "AC", "tocantinense": "TO", "brasiliense": "DF",
    "sulmatogrossense": "MS",
}

LEGAL_WORDS = {
    "club", "clube", "esporte", "regatas", "futebol", "athletic", "fc", "ec",
    "sc", "ac", "cr", "fr", "fbpa", "bbc", "bbc",
}

SPELLING_FOLDS = {
    "athletico": "atletico",
    "athletico paranaense": "atletico paranaense",
}

TEAM_ALIASES: dict[str, tuple[str, str]] = {
    "sport club corinthians paulista": ("corinthians", "SP"),
    "corinthians paulista": ("corinthians", "SP"),
    "sport club do recife": ("sport", "PE"),
    "sport recife": ("sport", "PE"),
    "clube de regatas vasco da gama": ("vasco", "RJ"),
    "vasco da gama": ("vasco", "RJ"),
    "clube de regatas do flamengo": ("flamengo", "RJ"),
    "atletico mineiro": ("atletico", "MG"),
    "clube atletico mineiro": ("atletico", "MG"),
    "atletico paranaense": ("atletico", "PR"),
    "america fc minas gerais": ("america", "MG"),
    "america fc natal": ("america", "RN"),
    "america futebol clube natal": ("america", "RN"),
    "america de natal": ("america", "RN"),
    "ceara sporting club": ("ceara", "CE"),
    "santos fc": ("santos", "SP"),
    "gremio fbpa": ("gremio", "RS"),
    "gremio foot ball porto alegrense": ("gremio", "RS"),
    "botafogo de futebol e regatas": ("botafogo", "RJ"),
    "botafogo fr": ("botafogo", "RJ"),
    "sao paulo fc": ("sao paulo", "SP"),
    "sao paulo futebol clube": ("sao paulo", "SP"),
    "sc internacional": ("internacional", "RS"),
    "internacional de porto alegre": ("internacional", "RS"),
    "parana clube": ("parana", "PR"),
    "esporte clube vitoria": ("vitoria", "BA"),
    "goias esporte clube": ("goias", "GO"),
    "fortaleza ec": ("fortaleza", "CE"),
    "fortaleza esporte clube": ("fortaleza", "CE"),
    "coritiba foot ball club": ("coritiba", "PR"),
    "coritiba fc": ("coritiba", "PR"),
    "avai fc": ("avai", "SC"),
    "criciuma ec": ("criciuma", "SC"),
    "associacao chapecoense de futebol": ("chapecoense", "SC"),
    "chapecoense fc": ("chapecoense", "SC"),
    "cruzeiro esporte clube": ("cruzeiro", "MG"),
    "esporte clube bahia": ("bahia", "BA"),
    "bahia fc": ("bahia", "BA"),
    "associacao desportiva atletico paranaense": ("atletico", "PR"),
    "ponte preta fc": ("ponte preta", "SP"),
    "associacao atletica ponte preta": ("ponte preta", "SP"),
    "nautico capibaribe": ("nautico", "PE"),
    "clube nautico capibaribe": ("nautico", "PE"),
    "santa cruz fc": ("santa cruz", "PE"),
    "santa cruz futebol clube": ("santa cruz", "PE"),
    "red bull brasil": ("bragantino", "SP"),
    "red bull bragantino": ("bragantino", "SP"),
    "rb bragantino": ("bragantino", "SP"),
    "atletico goianiense": ("atletico", "GO"),
    "atletico clube goianiense": ("atletico", "GO"),
    "guarani fc": ("guarani", "SP"),
    "figueirense fc": ("figueirense", "SC"),
    "associacao portuguesa de desportos": ("portuguesa", "SP"),
    "flamengo do piaui": ("flamengo", "PI"),
    "guarani de juazeiro": ("guarani", "CE"),
    "vitoria f c": ("vitoria", "ES"),
    "vitoria es": ("vitoria", "ES"),
    "club america": ("club america", ""),
    "boavista sport": ("boavista", "RJ"),
    "boavista sc saquarema": ("boavista", "RJ"),
}

PREFERRED_DISPLAYS: dict[str, str] = {
    "ceara-ce": "Ceará",
    "avai-sc": "Avaí",
    "cuiaba-mt": "Cuiabá",
    "goias-go": "Goiás",
    "vitoria-ba": "Vitória-BA",
    "america-mg": "América-MG",
    "america-rn": "América-RN",
    "atletico-mg": "Atlético-MG",
    "atletico-go": "Atlético-GO",
    "parana-pr": "Paraná",
    "santa cruz-pe": "Santa Cruz",
    "sao paulo-sp": "São Paulo",
    "gremio-rs": "Grêmio",
    "coritiba-pr": "Coritiba",
    "fortaleza-ce": "Fortaleza",
    "bahia-ba": "Bahia",
    "vitoria-es": "Vitória-ES",
}

DEFAULT_UF: dict[str, str] = {
    "atletico": "PR",
    "america": "MG",
    "santos": "SP",
    "botafogo": "RJ",
    "vitoria": "BA",
    "juventude": "RS",
    "nautico": "PE",
    "nacional": "AM",
    "guarani": "SP",
    "parana": "PR",
    "internacional": "RS",
    "gremio": "RS",
    "bahia": "BA",
    "sport": "PE",
    "coritiba": "PR",
    "ceara": "CE",
    "fortaleza": "CE",
    "goias": "GO",
    "figueirense": "SC",
    "chapecoense": "SC",
    "avai": "SC",
    "criciuma": "SC",
    "portuguesa": "SP",
    "ponte preta": "SP",
    "flamengo": "RJ",
    "fluminense": "RJ",
    "vasco": "RJ",
    "corinthians": "SP",
    "palmeiras": "SP",
    "sao paulo": "SP",
    "cruzeiro": "MG",
    "santa cruz": "PE",
    "bragantino": "SP",
    "atletico goianiense": "GO",
    "cuiaba": "MT",
    "atletico goianiense go": "GO",
}


def strip_accents(text: str) -> str:
    """Remove diacritics: 'São Paulo' -> 'Sao Paulo', 'Grêmio' -> 'Gremio'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    """Lowercase and strip accents, preserving only alphanumerics and spaces."""
    folded = strip_accents(text).lower()
    return re.sub(r"\s+", " ", folded).strip()


def _extract_country_tag(text: str) -> tuple[str | None, str]:
    """Pull a trailing '(URU)' style country tag out of a raw team name."""
    match = re.search(r"\(\s*([A-Za-z]{2,4})\s*\)\s*$", text)
    if match and match.group(1).upper() in COUNTRY_CODES:
        code = match.group(1).upper()
        stripped = (text[: match.start()] + text[match.end():]).strip()
        return code, stripped
    for code in COUNTRY_CODES:
        suffix = f"-{code.lower()}"
        if text.endswith(suffix):
            return code, text[: -len(suffix)].strip()
    return None, text


def _strip_parens(text: str) -> str:
    return re.sub(r"\([^)]*\)", " ", text)


def _extract_uf(tokens: list[str]) -> tuple[str | None, list[str]]:
    if len(tokens) > 1 and tokens[-1].upper() in BRAZILIAN_UFS and len(tokens[-1]) == 2:
        return tokens[-1].upper(), tokens[:-1]
    return None, tokens


def _extract_state_words(tokens: list[str]) -> tuple[str | None, list[str]]:
    for phrase, uf in sorted(STATE_NAME_WORDS.items(), key=lambda kv: -len(kv[0])):
        words = phrase.split()
        if len(tokens) > len(words) and tokens[-len(words):] == words:
            return uf, tokens[: -len(words)]
    for phrase, uf in sorted(STATE_NAME_WORDS.items(), key=lambda kv: -len(kv[0])):
        if len(tokens) > 1 and " ".join(tokens) == phrase:
            return uf, []
    return None, tokens


def _drop_legal_words(tokens: list[str]) -> list[str]:
    kept = [t for t in tokens if t not in LEGAL_WORDS]
    return kept or tokens


def _fold_spelling(tokens: list[str]) -> list[str]:
    return [SPELLING_FOLDS.get(t, t) for t in tokens]


def parse_team_name(raw: str) -> tuple[str, str | None, str | None]:
    """Break a raw team name into ``(base, uf, country)``.

    ``uf`` is a Brazilian state abbreviation, ``country`` a 3-letter code for
    foreign clubs; both may be None. The pipeline strips state/country
    suffixes and parentheses, applies the alias table (full names such as
    'Sport Club Corinthians Paulista' or 'Vasco da Gama - RJ'), drops
    legal-entity words ('FC', 'EC', 'Clube', ...) and folds spelling
    variants ('Athletico' -> 'Atletico').
    """
    lowered = normalize_text(raw)
    if not lowered:
        return "", None, None
    full_key = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", lowered)).strip()
    if full_key in TEAM_ALIASES:
        base, uf = TEAM_ALIASES[full_key]
        return base, uf, None
    country, lowered = _extract_country_tag(lowered)
    lowered = _strip_parens(lowered)
    tokens = re.split(r"[\s\-]+", lowered)
    tokens = [t for t in tokens if t]
    uf, tokens = _extract_uf(tokens)
    if uf is None and country is None:
        uf, tokens = _extract_state_words(tokens)
    alias = TEAM_ALIASES.get(" ".join(tokens))
    if alias:
        base, alias_uf = alias
        return base, uf or alias_uf, country
    tokens = _drop_legal_words(tokens)
    tokens = _fold_spelling(tokens)
    alias = TEAM_ALIASES.get(" ".join(tokens))
    if alias:
        base, alias_uf = alias
        return base, uf or alias_uf, country
    base = " ".join(tokens).strip()
    return base, uf, country


def canonical_id(base: str, uf: str | None, country: str | None) -> str:
    """Compose the canonical team id from parsed parts."""
    base = base.strip()
    if country:
        return f"{base}-{country.lower()}"
    if uf:
        return f"{base}-{uf.lower()}"
    return base


class TeamRegistry:
    """Registry of every team name observed in the datasets.

    Observations feed a base-name -> state counter used to resolve bare
    names such as "Palmeiras" to the club's canonical id.
    """

    def __init__(self) -> None:
        self._raw_counts: Counter[str] = Counter()
        self._base_ufs: dict[str, Counter[str]] = defaultdict(Counter)
        self._canonical_raws: dict[str, Counter[str]] = defaultdict(Counter)
        self._displays: dict[str, str] = {}

    def observe(self, raw: str, count: int = 1) -> None:
        raw = raw.strip()
        if not raw:
            return
        self._raw_counts[raw] += count
        base, uf, country = parse_team_name(raw)
        if not base:
            return
        cid = self._canonical_id_for(base, uf, country)
        self._base_ufs[base][(uf or country or "").upper()] += count
        self._canonical_raws[cid][raw] += count

    def _canonical_id_for(self, base: str, uf: str | None, country: str | None) -> str:
        if country:
            return canonical_id(base, None, country)
        if uf:
            return canonical_id(base, uf, None)
        resolved = self._resolve_uf(base)
        return canonical_id(base, resolved, None)

    def _resolve_uf(self, base: str) -> str | None:
        pinned = DEFAULT_UF.get(base)
        if pinned:
            return pinned
        ufs = self._base_ufs.get(base)
        if not ufs:
            return None
        distinct = {u for u in ufs if u}
        if len(distinct) == 1:
            return next(iter(distinct))
        return None

    def resolve(self, raw: str) -> str | None:
        """Resolve any team name variant to its canonical id.

        Returns None when nothing about the name is known to the registry.
        """
        raw = raw.strip()
        if not raw:
            return None
        base, uf, country = parse_team_name(raw)
        if not base:
            return None
        if uf or country:
            return canonical_id(base, uf, country)
        resolved = self._resolve_uf(base)
        if resolved:
            return canonical_id(base, resolved, None)
        if base in self._base_ufs:
            return base
        return None

    def finalize(self) -> None:
        """Precompute display names for every canonical id."""
        for cid, raws in self._canonical_raws.items():
            base = cid.rsplit("-", 1)[0] if "-" in cid else cid
            clean = [
                (raw, count)
                for raw, count in raws.items()
                if self._is_clean_display(raw, base)
            ]
            if clean and not self._base_is_ambiguous(cid):
                display = sorted(clean, key=lambda pair: (-pair[1], len(pair[0]), pair[0]))[0][0]
            else:
                display = sorted(raws.items(), key=lambda pair: (-pair[1], len(pair[0]), pair[0]))[0][0]
            display = re.sub(r"[-\s]\s*([A-Za-z]{2,3})$", r"-\1", display)
            self._displays[cid] = PREFERRED_DISPLAYS.get(cid, display)

    @staticmethod
    def _is_clean_display(raw: str, base: str) -> bool:
        """True when the raw name is exactly the bare base, no legal words."""
        return normalize_text(raw) == base and base != ""

    def _base_is_ambiguous(self, cid: str) -> bool:
        """True when a base name is shared by clubs of different states.

        A club holding >= 80% of a base's observations is considered the
        dominant club and keeps the clean unsuffixed display (e.g. 'Santos');
        minor sharers show the state suffix (e.g. 'Santos-AP').
        """
        base = cid.rsplit("-", 1)[0] if "-" in cid else cid
        ufs = self._base_ufs.get(base)
        if not ufs:
            return False
        counts = {u: c for u, c in ufs.items() if u}
        if len(counts) <= 1:
            return False
        total = sum(counts.values())
        if not total:
            return False
        top = max(counts.values())
        return top / total < 0.8

    def display(self, cid: str) -> str:
        """Human-friendly display name for a canonical id."""
        return self._displays.get(cid, cid.replace("-", " ").title())

    def is_known(self, cid: str) -> bool:
        return cid in self._canonical_raws

    def known_canonicals(self) -> list[str]:
        return sorted(self._canonical_raws)

    def aliases_of(self, cid: str) -> list[str]:
        return [raw for raw, _ in self._canonical_raws.get(cid, Counter()).most_common()]

    def suggest(self, query: str, limit: int = 8) -> list[str]:
        """Return canonical ids matching a (possibly misspelled) team name.

        Exact and substring matches score highest; if none are found, a
        difflib pass catches close typos such as 'Palmeirass'.
        """
        needle = normalize_text(query)
        if not needle:
            return []
        needle = re.sub(r"[\s\-]+", " ", needle)
        scored: list[tuple[int, str]] = []
        for cid, raws in self._canonical_raws.items():
            best = 0
            for raw in raws:
                hay = normalize_text(raw)
                if needle == hay:
                    best = max(best, 100)
                elif hay.startswith(needle):
                    best = max(best, 50)
                elif f" {needle}" in f" {hay}":
                    best = max(best, 25)
                elif needle in hay:
                    best = max(best, 10)
            if best:
                scored.append((best, cid))
        if not scored:
            return self._fuzzy_suggest(needle, limit)
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return [cid for _, cid in scored[:limit]]

    def _fuzzy_suggest(self, needle: str, limit: int) -> list[str]:
        import difflib

        candidates: dict[str, str] = {}
        for cid, raws in self._canonical_raws.items():
            for raw in raws:
                candidates[normalize_text(raw)] = cid
        close = difflib.get_close_matches(needle, candidates.keys(), n=limit, cutoff=0.75)
        seen: list[str] = []
        for name in close:
            cid = candidates[name]
            if cid not in seen:
                seen.append(cid)
        return seen[:limit]
