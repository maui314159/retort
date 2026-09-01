"""
Team-name normalization and canonical club-identity registry.

Context (Why): TASK.md "Data Quality Notes" warns that the six datasets use
inconsistent team naming:
    * with state suffix:            "Palmeiras-SP", "Flamengo - RJ"
    * without suffix:               "Palmeiras", "Flamengo"
    * full official names:          "Sport Club Corinthians Paulista",
                                    "Atlético Mineiro", "EC Bahia"
    * accented vs plain:            "Goiás" vs "Goias", "Avaí" vs "Avai"
    * parenthetical notes:          "Boavista Sport Club (antigo ...)" or
                                    foreign markers "Nacional (URU)"
A naive "strip the state suffix" approach is WRONG here: several base names
are shared by genuinely different clubs (Atlético-MG vs Atlético-PR vs
Atlético-GO; Flamengo-RJ vs tiny Flamengo-PI; Botafogo-RJ vs Botafogo-SP;
Santos-SP vs Santos-AP; America-RN vs America-MG). Club identity therefore
must keep the state suffix exactly when the base name is ambiguous.

What (algorithm, see ``TeamRegistry``):
    1. ``parse_name`` cleans a raw string: drops parenthetical notes,
       extracts a trailing Brazilian state ("-SP" / " SP") or a foreign
       marker ("-EQU", "(URU)"), strips accents, lowercases, removes
       trailing filler tokens ("FC", "EC", "Clube", ...) and finally applies
       a curated alias table ("Atletico Mineiro" -> base "atletico" + MG).
    2. During loading, every raw name yields a provisional id
       (``base-state`` / ``base`` / ``base-foreign``).
    3. ``finalize()`` inspects ALL registered names: a base that carries two
       or more different Brazilian states is *ambiguous*, so suffixed ids
       stay distinct and bare occurrences remap to the club's default state
       (curated override or the most frequent one). Unambiguous bases drop
       their suffix ("Corinthians-SP" -> "corinthians"). Foreign-marked ids
       never merge with bare ones ("Barcelona-EQU" stays distinct from FIFA's
       "FC Barcelona" -> "barcelona") because they are different clubs.
    4. ``resolve()`` maps arbitrary user/LLM input onto a canonical team,
       with substring fallback and candidate suggestions when ambiguous.

Test: tests/test_normalizer.py (BDD scenarios for every naming pattern above).
Spec reference: TASK.md "Data Quality Notes" -> "Team Name Variations",
"Character Encoding"; success criterion "Handles team name variations
correctly".
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from difflib import get_close_matches
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# 27 Brazilian federative-unit abbreviations (26 states + DF).
BRAZILIAN_STATES: frozenset[str] = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)

# Trailing tokens that are club-legal-form filler, not identity. Stripped
# iteratively from the end of a base name, but only while something remains.
# NOTE: "sport" must NOT be here - "Sport" (Recife) IS the club's name.
FILLER_TOKENS: frozenset[str] = frozenset(
    "fc ec sc ac ca clube club esporte esportes futebol futebool sporting".split()
)

# Full-name aliases applied AFTER accent-stripping, lowercasing and filler
# removal. Value = (base, optional forced state).
ALIASES: dict[str, tuple[str, Optional[str]]] = {
    # Same club, different spellings across the datasets
    "atletico mineiro": ("atletico", "mg"),
    "clube atletico mineiro": ("atletico", "mg"),
    "atletico paranaense": ("atletico", "pr"),
    "athletico paranaense": ("atletico", "pr"),
    "athletico": ("atletico", "pr"),          # FIFA-era spelling, always the PR club
    "atletico goianiense": ("atletico", "go"),
    "america mineiro": ("america", "mg"),
    "vasco da gama": ("vasco", None),
    "sport club do recife": ("sport", None),
    "sport recife": ("sport", None),
    "botafogo de futebol e regatas": ("botafogo", "rj"),
    "clube de regatas do flamengo": ("flamengo", "rj"),
    "gremio foot ball porto alegrense": ("gremio", None),
    "gremio fbpa": ("gremio", None),
    "red bull bragantino": ("bragantino", "sp"),
    "rb bragantino": ("bragantino", "sp"),
    "operario ferroviario": ("operario", "ms"),
    "sport club corinthians paulista": ("corinthians", None),
    "sport club corinthins paulista": ("corinthians", None),  # typo seen in the wild
    "sao paulo futebol clube": ("sao paulo", None),
    "associacao chapecoense de futebol": ("chapecoense", None),
    "esporte clube vitoria": ("vitoria", None),
    "esporte clube bahia": ("bahia", None),
    "clube atletico paranaense": ("atletico", "pr"),
    "clube atletico goianiense": ("atletico", "go"),
}

# Default state for a BARE occurrence of an ambiguous base name. Only used
# when the bare form itself is queried/registered; frequency fallback covers
# the rest, this table guards against ties/misleads.
DEFAULT_STATES: dict[str, str] = {
    "flamengo": "rj",
    "santos": "sp",
    "botafogo": "rj",
    "internacional": "rs",
    "america": "mg",
    "atletico": "mg",
    "guarani": "sp",
    "bragantino": "sp",
    "operario": "ms",
    "santa cruz": "pe",
    "nautico": "pe",
    "juventude": "rs",
    "vitoria": "ba",
    "comercial": "ms",
    "rio branco": "ac",
    "sao raimundo": "rr",
    "ypiranga": "rs",
}

# Curated display names for clubs users will most often ask about.
# Keys are canonical ids; accented Portuguese where appropriate.
DISPLAY_NAMES: dict[str, str] = {
    "flamengo-rj": "Flamengo",
    "fluminense-rj": "Fluminense",
    "vasco": "Vasco da Gama",
    "botafogo-rj": "Botafogo",
    "botafogo-sp": "Botafogo-SP",
    "corinthians": "Corinthians",
    "palmeiras": "Palmeiras",
    "sao paulo": "São Paulo",
    "santos-sp": "Santos",
    "gremio": "Grêmio",
    "internacional-rs": "Internacional",
    "atletico-mg": "Atlético Mineiro",
    "atletico-pr": "Athletico Paranaense",
    "atletico-go": "Atlético Goianiense",
    "cruzeiro": "Cruzeiro",
    "bahia": "Bahia",
    "vitoria": "Vitória",
    "sport": "Sport Recife",
    "ceara": "Ceará",
    "fortaleza": "Fortaleza",
    "goias": "Goiás",
    "coritiba": "Coritiba",
    "avai": "Avaí",
    "chapecoense": "Chapecoense",
    "figueirense": "Figueirense",
    "criciuma": "Criciúma",
    "paysandu": "Paysandu",
    "remo": "Remo",
    "america-mg": "América Mineiro",
    "america-rn": "América (RN)",
    "nautico-pe": "Náutico",
    "santa cruz-pe": "Santa Cruz",
    "juventude-rs": "Juventude",
    "guarani-sp": "Guarani",
    "bragantino-sp": "RB Bragantino",
    "ponte preta": "Ponte Preta",
    "parana": "Paraná",
    "csa": "CSA",
    "cuiaba": "Cuiabá",
    "cuiaba-mt": "Cuiabá",
    "athletic": "Athletic Club",
    "crb": "CRB",
    "abc": "ABC",
}

# Famous derby pairs (canonical ids) used by the derbies query.
# Only pairs that actually meet in the loaded match data are reported.
# NOTE: ids of ambiguous bases keep their state (fluminense-rj, not
# fluminense) - see the TeamRegistry docstring.
DERBIES: list[tuple[str, str, str]] = [
    ("flamengo-rj", "fluminense-rj", "Fla-Flu"),
    ("flamengo-rj", "vasco", "Clássico dos Milhões"),
    ("flamengo-rj", "botafogo-rj", "Clássico da Rivalidade"),
    ("vasco", "botafogo-rj", "Clássico dos Campeões Estaduais"),
    ("fluminense-rj", "botafogo-rj", "Clássico Vovô"),
    ("corinthians", "sao paulo", "Majestoso"),
    ("corinthians", "palmeiras", "Derby Paulista"),
    ("palmeiras", "sao paulo", "Choque-Rei"),
    ("gremio", "internacional-rs", "Grenal"),
    ("atletico-mg", "cruzeiro", "Clássico Mineiro"),
    ("bahia", "vitoria", "Ba-Vi"),
    ("sport", "nautico-pe", "Clássico dos Clássicos"),
    ("sport", "santa cruz-pe", "Clássico das Multidões"),
    ("atletico-pr", "coritiba", "Clássico Paranaense (At-Ti)"),
    ("avai", "figueirense", "Clássico de Florianópolis"),
    ("ceara", "fortaleza", "Clássico-Rei"),
    ("paysandu", "remo", "Re-Pa"),
    ("atletico-go", "goias", "Clássico Goiano"),
]

# Regexes ------------------------------------------------------------------

# trailing "-XX" or " XX" two-letter suffix (e.g. "Palmeiras-SP", "América - MG")
_STATE_DASH_RE = re.compile(r"\s*[-–]\s*([A-Z]{2})$")
_STATE_SPACE_RE = re.compile(r"\s+([A-Z]{2})$")
# trailing "-XXX" foreign marker (e.g. "Barcelona-EQU", "Olimpia-PAR")
_FOREIGN_DASH_RE = re.compile(r"\s*[-–]\s*([A-Z]{3,4})$")
# parenthetical foreign marker (e.g. "Nacional (URU)")
_PAREN_FOREIGN_RE = re.compile(r"\(\s*([A-Z]{2,4})\s*\)\s*$")
# any other parenthetical content (notes like "(antigo Esporte Clube Barreira)")
_PAREN_ANY_RE = re.compile(r"\(.*?\)")


def strip_accents(text: str) -> str:
    """Remove combining marks: 'São Paulo' -> 'Sao Paulo' (TASK.md encoding note)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


@dataclass(frozen=True)
class ParsedName:
    """Result of parsing one raw team string."""

    base: str                       # normalized, unaccented, filler-stripped
    state: Optional[str] = None     # Brazilian federative unit, lowercase
    foreign: Optional[str] = None   # foreign-country marker, lowercase


def _strip_edge_fillers(base: str) -> str:
    """Iteratively drop filler tokens from both ends while a stem remains.

    Trailing: "EC Bahia" never happens but "Bahia EC" does; leading: the
    datasets write both "EC Bahia" and "Bahia EC". "Sport" is NOT filler -
    it is Sport Recife's actual name.
    """
    tokens = base.split()
    while len(tokens) > 1 and (tokens[0] in FILLER_TOKENS or tokens[-1] in FILLER_TOKENS):
        if tokens[-1] in FILLER_TOKENS:
            tokens.pop()
        else:
            tokens.pop(0)
    return " ".join(tokens)


def parse_name(raw: str) -> ParsedName:
    """Parse one raw team name into (base, state|None, foreign|None)."""
    name = (raw or "").strip().strip('"').strip()
    foreign: Optional[str] = None

    # Parenthetical foreign marker, e.g. "Nacional (URU)"
    m = _PAREN_FOREIGN_RE.search(name)
    if m:
        foreign = m.group(1).lower()
        name = name[: m.start()].strip()

    # Drop any other parenthetical content (club history notes etc.)
    name = _PAREN_ANY_RE.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip(" -–")

    state: Optional[str] = None

    # Dash-form foreign marker, e.g. "Barcelona-EQU" / "Olimpia-PAR"
    m = _FOREIGN_DASH_RE.search(name)
    if m and m.group(1) not in BRAZILIAN_STATES:
        foreign = m.group(1).lower()
        name = name[: m.start()].strip()
    else:
        # Brazilian state suffix, dash ("Palmeiras-SP") or space ("Botafogo RJ")
        for regex in (_STATE_DASH_RE, _STATE_SPACE_RE):
            m = regex.search(name)
            if m and m.group(1) in BRAZILIAN_STATES:
                state = m.group(1).lower()
                name = name[: m.start()].strip()
                break

    base = strip_accents(name).lower()
    base = re.sub(r"[^a-z0-9 ]", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    base = _strip_edge_fillers(base)

    # Curated alias (may force a state, e.g. "Atletico Mineiro" -> MG)
    if base in ALIASES:
        new_base, forced_state = ALIASES[base]
        base = new_base
        if state is None and forced_state:
            state = forced_state

    return ParsedName(base=base or "?", state=state, foreign=foreign)


@dataclass
class TeamRef:
    """A resolved reference to a canonical team."""

    team_id: str
    display: str
    exact: bool = True
    alternatives: list[str] = field(default_factory=list)


class TeamRegistry:
    """Builds canonical club identities from every team name seen at load time.

    Usage:
        registry = TeamRegistry()
        provisional_id = registry.register("Palmeiras-SP")   # while loading
        ...
        id_map = registry.finalize()                          # after loading
        # remap provisional ids on stored entities via id_map
    """

    def __init__(self) -> None:
        # provisional-id -> {"display": str, "count": int}
        self._provisional: dict[str, dict] = {}
        # base -> {state or None -> provisional id}
        self._by_base: dict[str, dict[Optional[str], str]] = {}
        self._finalized = False
        # final state, filled by finalize()
        self.canonical_ids: set[str] = set()
        self._display: dict[str, str] = {}
        self._remap: dict[str, str] = {}
        self._ambiguous_bases: set[str] = set()

    # -- registration phase -------------------------------------------------

    def register(self, raw_name: str) -> str:
        """Record a raw team name (during loading); return a provisional id."""
        if not raw_name or not raw_name.strip():
            return "?"
        parsed = parse_name(raw_name)
        if parsed.foreign:
            pid = f"{parsed.base}-{parsed.foreign}"
        elif parsed.state:
            pid = f"{parsed.base}-{parsed.state}"
        else:
            pid = parsed.base

        entry = self._provisional.setdefault(pid, {"display": raw_name.strip(), "count": 0})
        entry["count"] += 1

        states = self._by_base.setdefault(parsed.base, {})
        states[parsed.state if not parsed.foreign else f"foreign:{parsed.foreign}"] = pid
        return pid

    # -- finalization phase -------------------------------------------------

    def finalize(self) -> dict[str, str]:
        """Resolve ambiguities; return provisional-id -> canonical-id map."""
        if self._finalized:
            return self._remap

        # Which bases are ambiguous (two or more distinct Brazilian states)?
        for base, states in self._by_base.items():
            brazilian_states = {s for s in states if s and not s.startswith("foreign:")}
            if len(brazilian_states) > 1:
                self._ambiguous_bases.add(base)

        remap: dict[str, str] = {}

        for base, states in self._by_base.items():
            ambiguous = base in self._ambiguous_bases
            bare_pid = states.get(None)

            if not ambiguous:
                # single Brazilian state (or none): strip the suffix
                canonical = base
                for state, pid in states.items():
                    if state and not state.startswith("foreign:"):
                        remap[pid] = canonical
                if bare_pid is not None:
                    remap[bare_pid] = canonical
            else:
                # keep each state-suffixed id distinct
                for state, pid in states.items():
                    if state and not state.startswith("foreign:"):
                        remap[pid] = f"{base}-{state}"
                # bare form -> default (curated, else most frequent state)
                if bare_pid is not None:
                    default = self._default_state_for(base)
                    remap[bare_pid] = f"{base}-{default}"

            # foreign-marked ids always keep their marker
            for state, pid in states.items():
                if state and state.startswith("foreign:"):
                    remap[pid] = pid  # already base-foreign

        # Canonical displays: curated first, else most frequent raw variant.
        self._display = {}
        counts: dict[str, Counter] = {}
        for pid, entry in self._provisional.items():
            canonical = remap.get(pid, pid)
            counts.setdefault(canonical, Counter())[entry["display"]] += entry["count"]

        for canonical, counter in counts.items():
            if canonical in DISPLAY_NAMES:
                self._display[canonical] = DISPLAY_NAMES[canonical]
            else:
                best_raw = counter.most_common(1)[0][0]
                self._display[canonical] = best_raw.title() if best_raw.isupper() else best_raw

        self.canonical_ids = set(self._display)
        self._remap = remap
        self._finalized = True
        return remap

    def _default_state_for(self, base: str) -> str:
        """Default state for a bare ambiguous base (e.g. bare 'Fluminense').

        Curated override first; otherwise the state whose suffixed form
        occurs most often in the data (Fluminense-RJ >> Fluminense-PI).
        Note: provisional ids are lowercase, so suffixes must be compared
        case-insensitively against the uppercase state codes.
        """
        if base in DEFAULT_STATES:
            return DEFAULT_STATES[base]
        state_counts: Counter = Counter()
        for pid, entry in self._provisional.items():
            if pid.startswith(base + "-"):
                suffix = pid.rsplit("-", 1)[1]
                if suffix.upper() in BRAZILIAN_STATES:
                    state_counts[suffix] += entry["count"]
        if state_counts:
            # deterministic: highest count, then alphabetical
            return sorted(state_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        # last resort: alphabetically first known Brazilian state
        states = sorted(
            s
            for s in self._by_base.get(base, {})
            if s and not s.startswith("foreign:")
        )
        if states:
            return states[0]
        raise KeyError(f"No state known for ambiguous base '{base}'")

    # -- query phase ---------------------------------------------------------

    def display(self, team_id: str) -> str:
        return self._display.get(team_id, team_id.title())

    def variants(self, team_id: str) -> list[str]:
        """Raw spellings seen in the datasets that map to this canonical id."""
        if not self._finalized:
            return []
        found: dict[str, None] = {}
        for pid, entry in self._provisional.items():
            if self._remap.get(pid, pid) == team_id:
                found[entry["display"]] = None
        return sorted(found)

    def all_teams(self) -> list[str]:
        return sorted(self.canonical_ids)

    def _canonical_from_parsed(self, parsed: ParsedName) -> Optional[str]:
        """Map a parsed name onto a canonical id using finalization rules."""
        if parsed.foreign:
            candidate = f"{parsed.base}-{parsed.foreign}"
            return candidate if candidate in self.canonical_ids else None

        base_states = {
            s
            for s in self._by_base.get(parsed.base, {})
            if s and not s.startswith("foreign:")
        }
        if parsed.base in self._ambiguous_bases:
            if parsed.state:
                candidate = f"{parsed.base}-{parsed.state}"
            else:
                candidate = f"{parsed.base}-{self._default_state_for(parsed.base)}"
            return candidate if candidate in self.canonical_ids else None

        if parsed.base in self.canonical_ids:
            return parsed.base
        # unambiguous base with explicit state -> suffix was stripped
        if f"{parsed.base}-{parsed.state}" in self.canonical_ids and len(base_states) > 1:
            return f"{parsed.base}-{parsed.state}"
        return None

    def resolve(self, query: str) -> TeamRef:
        """Resolve user/LLM team input to a canonical TeamRef.

        Exact parse first; then substring search over canonical ids, display
        names and raw variants; then fuzzy match as a last resort.
        """
        q = (query or "").strip()
        if not q:
            raise ValueError("Empty team query")

        parsed = parse_name(q)
        direct = self._canonical_from_parsed(parsed)
        if direct:
            return TeamRef(team_id=direct, display=self.display(direct))

        # substring / containment search over ids and display names
        needle = strip_accents(q).lower()
        matches: set[str] = set()
        for team_id in self.canonical_ids:
            if needle in team_id or needle in strip_accents(self.display(team_id)).lower():
                matches.add(team_id)
        if not matches:
            for pid in self._provisional:
                if needle in strip_accents(pid).lower():
                    matches.add(self._remap.get(pid, pid))
        if len(matches) == 1:
            team_id = matches.pop()
            return TeamRef(team_id=team_id, display=self.display(team_id), exact=False)
        if len(matches) > 1:
            ordered = sorted(matches)
            # Prefer the famous club when several share a base (e.g. bare
            # "flamengo" typed by a user almost surely means Flamengo-RJ).
            parsed_direct = (
                self._default_state_for(parsed.base)
                if parsed.base in self._ambiguous_bases
                else None
            )
            if parsed_direct:
                preferred = f"{parsed.base}-{parsed_direct}"
                if preferred in matches:
                    return TeamRef(
                        team_id=preferred,
                        display=self.display(preferred),
                        exact=False,
                        alternatives=[t for t in ordered if t != preferred][:6],
                    )
            return TeamRef(
                team_id=ordered[0],
                display=self.display(ordered[0]),
                exact=False,
                alternatives=ordered[1:7],
            )

        # fuzzy last resort
        close = get_close_matches(
            needle, [strip_accents(t).lower() for t in self.canonical_ids], n=1, cutoff=0.75
        )
        if close:
            for team_id in self.canonical_ids:
                if strip_accents(team_id) == close[0]:
                    return TeamRef(team_id=team_id, display=self.display(team_id), exact=False)

        raise LookupError(
            f"No team found matching '{query}'. "
            f"Try a name from the dataset (e.g. 'Flamengo', 'Palmeiras', 'Santos')."
        )
