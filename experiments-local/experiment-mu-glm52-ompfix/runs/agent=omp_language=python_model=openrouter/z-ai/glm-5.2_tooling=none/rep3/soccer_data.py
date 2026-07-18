"""
soccer_data.py
==============

Data-access layer for the Brazilian Soccer MCP server.

Context block
-------------
This module is the single source of truth for loading, normalizing and
querying the six Kaggle CSV datasets that ship with the repository:

    data/kaggle/Brasileirao_Matches.csv        (Brasileirao Serie A)
    data/kaggle/Brazilian_Cup_Matches.csv      (Copa do Brasil)
    data/kaggle/Libertadores_Matches.csv       (Copa Libertadores)
    data/kaggle/BR-Football-Dataset.csv        (extended match stats)
    data/kaggle/novo_campeonato_brasileiro.csv (Brasileirao 2003-2019)
    data/kaggle/fifa_data.csv                  (FIFA player database)

It exposes a :class:`SoccerStore` that holds a unified ``matches`` DataFrame
(one row per match across every source) plus the FIFA player table, and a set
of pure, side-effect-free query methods that the MCP server (in
``mcp_server.py``) wraps as tools.

Design notes
------------
* Team names from different files use different conventions
  ("Palmeiras-SP", "América - MG", "Sport Club Corinthians Paulista", ...).
  :func:`normalize_team` strips state suffixes, parenthetical notes and
  accents to produce a stable key used for matching and head-to-head.
* Dates appear both as ISO (``2012-05-19 18:30:00``) and Brazilian
  (``29/03/2003``); :func:`parse_date` handles both.
* Goals are coerced to integers; rows with unparseable scores are dropped.
* The store is cached as a module-level singleton so the MCP server loads
  the CSVs once on startup and subsequent tool calls are sub-millisecond.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable

import pandas as pd

# ---------------------------------------------------------------------------
# Constants / paths
# ---------------------------------------------------------------------------

# Resolve the data directory relative to this file so the store works no matter
# what the current working directory of the MCP server process is.
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")

FILES = {
    "brasileirao": "Brasileirao_Matches.csv",
    "cup": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "br_football": "BR-Football-Dataset.csv",
    "novo": "novo_campeonato_brasileiro.csv",
    "fifa": "fifa_data.csv",
}

# Brazilian state abbreviations used as team suffixes across several files.
STATE_SUFFIX_RE = re.compile(r"\s*-\s*[A-Za-z]{2}\s*$")

# A small curated set of well-known Brazilian club derbies (normalized keys
# on both sides). Used by the ``derbies`` query. Keys are normalized team names.
DERBIES = [
    ("flamengo", "fluminense", "Fla-Flu"),
    ("vasco", "flamengo", "Clássico dos Milhões"),
    ("vasco", "botafogo", "Clássico da Amizade"),
    ("palmeiras", "corinthians", "Derby Paulista"),
    ("sao paulo", "corinthians", "Majestoso"),
    ("palmeiras", "sao paulo", "Choque-Rei"),
    ("santos", "sao paulo", "San-São"),
    ("gremio", "internacional", "Grenal"),
    ("cruzeiro", "atletico", "Clássico Mineiro"),
    ("bahia", "vitoria", "Ba-Vi"),
    ("coritiba", "athletico", "Atletiba"),
    ("ceara", "fortaleza", "Clássico do Nordeste"),
]
# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _strip_accents(text: str) -> str:
    """Return ``text`` with diacritics removed (NFKD decomposition)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_team(name: Any) -> str:
    """Normalize a team name to a canonical, disambiguated key.

    Brazilian club names appear with many variants across the source files:
    state suffixes (``"Palmeiras-SP"``), bare names (``"Palmeiras"``) and full
    names (``"Atletico Mineiro"``). Naïvely stripping the state suffix would
    merge distinct clubs — e.g. ``"Atlético-MG"`` and ``"Atlético-GO"`` — so
    this function resolves every variant through :data:`CANONICAL_ALIASES`
    to a stable canonical key that keeps the state code only when it is needed
    to disambiguate.

    >>> normalize_team("Palmeiras-SP")
    'palmeiras'
    >>> normalize_team("América - MG")
    'america mg'
    >>> normalize_team("Atletico Mineiro")
    'atletico mg'
    """
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    raw = _norm_raw(name)
    if raw in CANONICAL_ALIASES:
        return CANONICAL_ALIASES[raw]
    # Fallback: keep the state suffix as part of the key when present (so
    # "atlético-go" stays distinct from "atlético-mg"); otherwise strip it.
    bare = STATE_SUFFIX_RE.sub("", str(name).strip())
    bare = _norm_raw(bare)
    return bare


def _norm_raw(name: Any) -> str:
    """Lowercase, accent-stripped form that PRESERVES the state suffix and
    collapses separators to spaces. Used as the lookup key into
    :data:`CANONICAL_ALIASES`."""
    s = str(name).strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = _strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def display_team(name: Any) -> str:
    """Return a clean display name: strip parentheticals and surrounding
    whitespace, keep accents and the state suffix."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    s = str(name).strip()
    s = re.sub(r"\([^)]*\)", "", s)
    return s.strip()


def team_display(key: str, fallback: str = "") -> str:
    """Return the canonical display name for a canonical team key."""
    return TEAM_DISPLAY.get(key, fallback or key)


# Canonical team registry ---------------------------------------------------
# Each canonical key maps to itself; every known variant (suffixed, bare,
# full-name, alternate spelling) is an alias pointing at a canonical key. The
# state code is retained in the canonical key only when two real clubs share a
# base name (Atlético, América, Botafogo, ...).
CANONICAL_ALIASES: dict[str, str] = {}
TEAM_DISPLAY: dict[str, str] = {}


def _register(canonical: str, display: str, *aliases: str) -> None:
    TEAM_DISPLAY[canonical] = display
    CANONICAL_ALIASES[canonical] = canonical
    for a in aliases:
        CANONICAL_ALIASES[_norm_raw(a)] = canonical


# Major Brazilian clubs. Order does not matter; all known variants are listed.
_register("flamengo", "Flamengo", "Flamengo", "Flamengo-RJ", "Flamengo - RJ", "Flamengo - PI")
# Flamengo-PI is a distinct small club; keep it separate.
CANONICAL_ALIASES.pop(_norm_raw("Flamengo - PI"), None)
_register("flamengo pi", "Flamengo-PI", "Flamengo do Piaui - PI", "Flamengo - PI", "Flamengo-PI")
_register("fluminense", "Fluminense", "Fluminense", "Fluminense-RJ", "Fluminense - RJ")
_register("fluminense pi", "Fluminense-PI", "Fluminense PI", "Fluminense - PI")
_register("vasco", "Vasco", "Vasco", "Vasco da Gama", "Vasco da Gama-RJ", "Vasco da Gama - RJ", "Vasco da Gama RJ")
_register("botafogo", "Botafogo", "Botafogo", "Botafogo-RJ", "Botafogo - RJ", "Botafogo RJ")
_register("botafogo pb", "Botafogo-PB", "Botafogo-PB", "Botafogo - PB", "Botafogo PB")
_register("botafogo sp", "Botafogo-SP", "Botafogo-SP", "Botafogo SP")
_register("palmeiras", "Palmeiras", "Palmeiras", "Palmeiras-SP", "Palmeiras - SP")
_register("corinthians", "Corinthians", "Corinthians", "Corinthians-SP", "Corinthians - SP")
_register("sao paulo", "São Paulo", "São Paulo", "Sao Paulo", "São Paulo-SP", "Sao Paulo-SP", "Sao Paulo - SP", "Sao Paulo SP")
_register("santos", "Santos", "Santos", "Santos-SP", "Santos - SP", "Santos SP")
_register("santos ap", "Santos-AP", "Santos-AP", "Santos AP", "Santos - AP")
_register("gremio", "Grêmio", "Grêmio", "Gremio", "Grêmio-RS", "Gremio-RS", "Grêmio - RS", "Gremio RS")
_register("internacional", "Internacional", "Internacional", "Internacional-RS", "Internacional - RS", "Internacional RS")
_register("internacional sc", "Internacional-SC", "Internacional-SC", "Internacional SC", "Internacional - SC", "EC Internacional SC")
_register("cruzeiro", "Cruzeiro", "Cruzeiro", "Cruzeiro-MG", "Cruzeiro - MG")
_register("atletico mg", "Atlético-MG", "Atlético-MG", "Atletico-MG", "Atlético Mineiro", "Atletico Mineiro", "Atlético Mineiro - MG", "Atletico Mineiro - MG")
_register("atletico go", "Atlético-GO", "Atlético-GO", "Atletico-GO", "Atlético Goianiense", "Atletico Goianiense", "Atlético-GO")
_register("atletico pr", "Athletico-PR", "Athletico-PR", "Atlético-PR", "Atletico-PR", "Athletico Paranaense", "Atletico Paranaense", "Athletico", "Athletico Paranaense - PR", "Atletico Paranaense - PR", "Athletico-PR")
_register("america mg", "América-MG", "América-MG", "America-MG", "América Mineiro", "America MG", "América - MG", "America - MG")
_register("america rn", "América-RN", "América-RN", "America-RN", "América de Natal", "America de Natal", "America FC Natal", "América - RN", "America - RN")
_register("coritiba", "Coritiba", "Coritiba", "Coritiba-PR", "Coritiba - PR", "Coritiba PR")
_register("bahia", "Bahia", "Bahia", "Bahia-BA", "Bahia - BA", "EC Bahia")
_register("vitoria", "Vitória", "Vitória", "Vitoria", "Vitória-BA", "Vitoria-BA", "Vitória - BA", "Vitoria - BA", "EC Vitória", "Vitoria EC")
_register("vitoria es", "Vitória-ES", "Vitória-ES", "Vitoria ES", "Vitória - ES", "Vitoria - ES", "Vitória F.C. - ES")
_register("fortaleza", "Fortaleza", "Fortaleza", "Fortaleza-CE", "Fortaleza - CE", "Fortaleza EC", "Fortaleza FC")
_register("ceara", "Ceará", "Ceará", "Ceara", "Ceará-CE", "Ceara-CE", "Ceará - CE", "Ceara - CE")
_register("sport", "Sport", "Sport", "Sport-PE", "Sport - PE", "Sport Recife")
_register("goias", "Goiás", "Goiás", "Goias", "Goiás-GO", "Goias-GO")
_register("chapecoense", "Chapecoense", "Chapecoense", "Chapecoense-SC")
_register("avai", "Avaí", "Avaí", "Avai", "Avaí-SC")
_register("figueirense", "Figueirense", "Figueirense", "Figueirense-SC")
_register("ponte preta", "Ponte Preta", "Ponte Preta", "Ponte Preta-SP")
_register("portuguesa", "Portuguesa", "Portuguesa", "Portuguesa Desportos", "Portuguesa-SP")
_register("guarani", "Guarani", "Guarani", "Guarani-SP")
_register("juventude", "Juventude", "Juventude", "Juventude-RS")
_register("criciuma", "Criciúma", "Criciúma", "Criciuma", "Criciúma-SC")
_register("atletico nacional", "Atlético Nacional", "Atlético Nacional", "Atletico Nacional")  # COL (foreign)


def normalize_comp(name: Any) -> str:
    """Normalize a *competition* name for matching.

    Unlike :func:`normalize_team`, parenthetical content is PRESERVED so that
    distinct datasets stay distinct — e.g. ``"Brasileirão"`` and
    ``"Brasileirão (2003-2019)"`` normalize to different keys. Only accents
    and case are removed.
    """
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    s = _strip_accents(str(name).strip()).lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def parse_date(value: Any) -> "pd.Timestamp | type(pd.NaT)":
    """Parse a date that may be ISO (with optional time) or Brazilian DD/MM/YYYY."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    if isinstance(value, pd.Timestamp):
        return value
    s = str(value).strip()
    if not s:
        return pd.NaT
    # Brazilian DD/MM/YYYY (the historical 2003-2019 dataset uses this format).
    if re.match(r"\d{1,2}/\d{1,2}/\d{4}", s):
        return pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    # Everything else is ISO (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS).
    return pd.to_datetime(s, errors="coerce")
def _to_int(value: Any) -> int | None:
    """Coerce a goal value to a non-negative int, or ``None`` if unparseable."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f or f < 0:  # NaN or negative
        return None
    return int(f)


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

@dataclass
class _MatchColumns:
    """Mapping from a source file to the columns needed for the unified table."""

    date: str
    home: str
    away: str
    home_goal: str
    away_goal: str
    season: str | None = None
    stage: str | None = None
    competition: str = ""


class SoccerStore:
    """Holds the unified match table + FIFA players and answers queries.

    The store is intentionally lightweight: every public method returns plain
    Python data (dicts / lists / strings) so it can be unit-tested without
    pandas knowledge bleeding into the MCP tool layer.
    """

    def __init__(self, data_dir: str = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.matches: pd.DataFrame = self._load_matches()
        self.players: pd.DataFrame = self._load_players()
        # Pre-compute a goal-difference magnitude column for biggest-wins.
        self.matches["goal_diff"] = (
            self.matches["home_goal"].fillna(0) - self.matches["away_goal"].fillna(0)
        ).abs()

    # -- loading -----------------------------------------------------------

    def _load_matches(self) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []

        # 1. Brasileirao Serie A
        df = pd.read_csv(self._path("brasileirao"))
        frames.append(
            self._to_unified(
                df,
                competition="Brasileirão",
                date="datetime",
                home="home_team",
                away="away_team",
                home_goal="home_goal",
                away_goal="away_goal",
                season="season",
                stage="round",
            )
        )

        # 2. Copa do Brasil
        df = pd.read_csv(self._path("cup"))
        frames.append(
            self._to_unified(
                df,
                competition="Copa do Brasil",
                date="datetime",
                home="home_team",
                away="away_team",
                home_goal="home_goal",
                away_goal="away_goal",
                season="season",
                stage="round",
            )
        )

        # 3. Copa Libertadores
        df = pd.read_csv(self._path("libertadores"))
        frames.append(
            self._to_unified(
                df,
                competition="Copa Libertadores",
                date="datetime",
                home="home_team",
                away="away_team",
                home_goal="home_goal",
                away_goal="away_goal",
                season="season",
                stage="stage",
            )
        )

        # 4. BR-Football extended stats (tournament column carries competition)
        df = pd.read_csv(self._path("br_football"))
        frames.append(
            self._to_unified(
                df,
                competition=None,  # take from 'tournament' column
                date="date",
                home="home",
                away="away",
                home_goal="home_goal",
                away_goal="away_goal",
                season=None,
                stage=None,
            )
        )

        # 5. Historical Brasileirão 2003-2019
        df = pd.read_csv(self._path("novo"))
        frames.append(
            self._to_unified(
                df,
                competition="Brasileirão (2003-2019)",
                date="Data",
                home="Equipe_mandante",
                away="Equipe_visitante",
                home_goal="Gols_mandante",
                away_goal="Gols_visitante",
                season="Ano",
                stage="Rodada",
            )
        )

        out = pd.concat(frames, ignore_index=True, sort=False)
        return out

    def _path(self, key: str) -> str:
        return os.path.join(self.data_dir, FILES[key])

    @staticmethod
    def _to_unified(
        df: pd.DataFrame,
        *,
        competition: str | None,
        date: str,
        home: str,
        away: str,
        home_goal: str,
        away_goal: str,
        season: str | None,
        stage: str | None,
    ) -> pd.DataFrame:
        """Project a source DataFrame onto the unified match schema."""
        rows: list[dict[str, Any]] = []
        for _, r in df.iterrows():
            hg = _to_int(r.get(home_goal))
            ag = _to_int(r.get(away_goal))
            d = parse_date(r.get(date))
            comp = competition if competition is not None else str(r.get("tournament", ""))
            seas = r.get(season) if season else None
            seas = int(seas) if seas is not None and not pd.isna(seas) else None
            stg = r.get(stage) if stage else None
            stg = "" if stg is None or (isinstance(stg, float) and pd.isna(stg)) else str(stg)
            # Derive season from the match date when the source has no season
            # column (e.g. BR-Football-Dataset.csv) so season filters work there.
            if seas is None and pd.notna(d):
                seas = int(d.year)
            rows.append(
                {
                    "date": d,
                    "home": display_team(r.get(home)),
                    "home_key": normalize_team(r.get(home)),
                    "away": display_team(r.get(away)),
                    "away_key": normalize_team(r.get(away)),
                    "home_goal": hg,
                    "away_goal": ag,
                    "competition": comp,
                    "season": seas,
                    "stage": stg,
                }
            )
        return pd.DataFrame(rows)

    def _load_players(self) -> pd.DataFrame:
        df = pd.read_csv(self._path("fifa"))
        # The CSV has an unnamed index column; drop it if present.
        df = df.loc[:, [c for c in df.columns if not c.lower().startswith("unnamed")]]
        return df

    # -- internal filtering ----------------------------------------------

    def _filter(
        self,
        *,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        m = self.matches
        if team:
            tk = normalize_team(team)
            if opponent:
                ok = normalize_team(opponent)
                mask = ((m["home_key"] == tk) & (m["away_key"] == ok)) | (
                    (m["home_key"] == ok) & (m["away_key"] == tk)
                )
            else:
                mask = (m["home_key"] == tk) | (m["away_key"] == tk)
            m = m[mask]
        if competition:
            ck = normalize_comp(competition)
            comp_mask = m["competition"].apply(lambda c: normalize_comp(c) == ck if isinstance(c, str) else False)
            m = m[comp_mask]
        if season is not None:
            m = m[m["season"] == season]
        if start:
            sd = parse_date(start)
            m = m[m["date"] >= sd]
        if end:
            ed = parse_date(end)
            m = m[m["date"] <= ed]
        # Only keep rows that have a valid score (drop fixtures without result).
        m = m[m["home_goal"].notna() & m["away_goal"].notna()]
        return m.sort_values("date").reset_index(drop=True)

    # -- public query API --------------------------------------------------

    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        start: str | None = None,
        end: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return a list of match dicts matching the given criteria."""
        m = self._filter(
            team=team, opponent=opponent, competition=competition,
            season=season, start=start, end=end,
        )
        out: list[dict[str, Any]] = []
        for _, r in m.head(limit).iterrows():
            out.append(self._row_to_match(r))
        return out

    @staticmethod
    def _row_to_match(r: pd.Series) -> dict[str, Any]:
        return {
            "date": r["date"].strftime("%Y-%m-%d") if pd.notna(r["date"]) else "",
            "home": team_display(r["home_key"], r["home"]),
            "away": team_display(r["away_key"], r["away"]),
            "home_goal": int(r["home_goal"]) if pd.notna(r["home_goal"]) else None,
            "away_goal": int(r["away_goal"]) if pd.notna(r["away_goal"]) else None,
            "competition": r["competition"],
            "season": int(r["season"]) if pd.notna(r["season"]) else None,
            "stage": r["stage"],
        }

    def last_match(self, team: str, opponent: str | None = None) -> dict[str, Any] | None:
        m = self._filter(team=team, opponent=opponent)
        if m.empty:
            return None
        return self._row_to_match(m.iloc[-1])

    def head_to_head(self, team_a: str, team_b: str) -> dict[str, Any]:
        m = self._filter(team=team_a, opponent=team_b)
        a_key = normalize_team(team_a)
        a_win = b_win = draws = 0
        a_gf = a_ga = 0
        matches: list[dict[str, Any]] = []
        for _, r in m.iterrows():
            hg, ag = r["home_goal"], r["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            hg, ag = int(hg), int(ag)
            home_is_a = r["home_key"] == a_key
            # winner relative to A
            if hg > ag:
                if home_is_a:
                    a_win += 1
                    a_gf += hg; a_ga += ag
                else:
                    b_win += 1
                    a_gf += ag; a_ga += hg
            elif ag > hg:
                if home_is_a:
                    b_win += 1
                    a_gf += hg; a_ga += ag
                else:
                    a_win += 1
                    a_gf += ag; a_ga += hg
            else:
                draws += 1
                a_gf += hg; a_ga += ag
            matches.append(self._row_to_match(r))
        return {
            "team_a": team_a, "team_b": team_b,
            "matches": matches,
            "team_a_wins": a_win, "team_b_wins": b_win, "draws": draws,
            "team_a_goals": a_gf, "team_b_goals": a_ga,
            "total": len(matches),
        }

    def team_stats(
        self,
        team: str,
        competition: str | None = None,
        season: int | None = None,
        venue: str | None = None,  # "home", "away", or None (both)
    ) -> dict[str, Any]:
        m = self._filter(team=team, competition=competition, season=season)
        tk = normalize_team(team)
        wins = draws = losses = 0
        gf = ga = 0
        played = 0
        for _, r in m.iterrows():
            hg, ag = r["home_goal"], r["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            is_home = r["home_key"] == tk
            if venue == "home" and not is_home:
                continue
            if venue == "away" and is_home:
                continue
            played += 1
            our = int(hg) if is_home else int(ag)
            opp = int(ag) if is_home else int(hg)
            gf += our; ga += opp
            if our > opp:
                wins += 1
            elif our < opp:
                losses += 1
            else:
                draws += 1
        win_rate = round(wins / played * 100, 1) if played else 0.0
        return {
            "team": team_display(normalize_team(team), team), "competition": competition, "season": season, "venue": venue,
            "played": played, "wins": wins, "draws": draws, "losses": losses,
            "goals_for": gf, "goals_against": ga, "win_rate": win_rate,
        }

    def team_competitions(self, team: str) -> dict[str, Any]:
        m = self._filter(team=team)
        comps = (
            m.groupby("competition").size().sort_values(ascending=False)
            if not m.empty else pd.Series(dtype=int)
        )
        return {
            "team": team_display(normalize_team(team), team),
            "competitions": [
                {"competition": c, "matches": int(n)} for c, n in comps.items()
            ],
        }

    def standings(self, competition: str, season: int) -> dict[str, Any]:
        """Compute a standings table (points) for a competition+season.

        Uses 3 points for a win, 1 for a draw. Only matches with valid scores
        and a recognizable team (non-empty key) are counted.
        """
        m = self._filter(competition=competition, season=season)
        teams: dict[str, dict[str, int]] = {}
        for _, r in m.iterrows():
            hg, ag = r["home_goal"], r["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            hg, ag = int(hg), int(ag)
            for key, gf, ga in (
                (r["home_key"], hg, ag),
                (r["away_key"], ag, hg),
            ):
                if not key:
                    continue
                t = teams.setdefault(key, {"name": team_display(key, key), "played": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0, "pts": 0})
                t["played"] += 1; t["gf"] += gf; t["ga"] += ga
                if gf > ga:
                    t["wins"] += 1; t["pts"] += 3
                elif gf == ga:
                    t["draws"] += 1; t["pts"] += 1
                else:
                    t["losses"] += 1
        table = sorted(teams.values(), key=lambda t: (-t["pts"], -t["wins"], -(t["gf"] - t["ga"]), -t["gf"], t["name"]))
        for i, t in enumerate(table, 1):
            t["position"] = i
        return {"competition": competition, "season": season, "table": table}

    def biggest_wins(
        self,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        m = self._filter(competition=competition, season=season)
        if m.empty:
            return {"wins": []}
        top = m.sort_values("goal_diff", ascending=False).head(limit)
        return {
            "wins": [
                {
                    "date": r["date"].strftime("%Y-%m-%d") if pd.notna(r["date"]) else "",
                    "home": team_display(r["home_key"], r["home"]), "away": team_display(r["away_key"], r["away"]),
                    "home_goal": int(r["home_goal"]), "away_goal": int(r["away_goal"]),
                    "competition": r["competition"], "season": int(r["season"]) if pd.notna(r["season"]) else None,
                }
                for _, r in top.iterrows()
            ]
        }

    def average_goals(
        self, competition: str | None = None, season: int | None = None
    ) -> dict[str, Any]:
        m = self._filter(competition=competition, season=season)
        if m.empty:
            return {"matches": 0, "average_goals": 0.0, "home_win_rate": 0.0}
        total_goals = int((m["home_goal"].fillna(0) + m["away_goal"].fillna(0)).sum())
        home_wins = int((m["home_goal"] > m["away_goal"]).sum())
        return {
            "matches": len(m),
            "average_goals": round(total_goals / len(m), 2),
            "home_win_rate": round(home_wins / len(m) * 100, 1),
        }

    def best_record(
        self,
        venue: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        metric: str = "win_rate",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Rank teams by win-rate across the given filter."""
        m = self._filter(competition=competition, season=season)
        stats: dict[str, dict[str, Any]] = {}
        for _, r in m.iterrows():
            hg, ag = r["home_goal"], r["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            for key, is_home in (
                (r["home_key"], True),
                (r["away_key"], False),
            ):
                if not key:
                    continue
                if venue == "home" and not is_home:
                    continue
                if venue == "away" and is_home:
                    continue
                t = stats.setdefault(key, {"name": team_display(key, key), "played": 0, "wins": 0, "draws": 0, "losses": 0})
                t["played"] += 1
                our = int(hg) if is_home else int(ag)
                opp = int(ag) if is_home else int(hg)
                if our > opp: t["wins"] += 1
                elif our < opp: t["losses"] += 1
                else: t["draws"] += 1
        rows = []
        for k, t in stats.items():
            wr = round(t["wins"] / t["played"] * 100, 1) if t["played"] else 0.0
            rows.append({**t, "win_rate": wr})
        rows.sort(key=lambda x: -x["win_rate"])
        # Require at least a few matches to be meaningful.
        rows = [r for r in rows if r["played"] >= 5]
        return {"metric": metric, "venue": venue, "teams": rows[:limit]}

    # -- player queries ----------------------------------------------------

    def player_search(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 20,
        sort_by: str = "Overall",
        desc: bool = True,
    ) -> list[dict[str, Any]]:
        df = self.players
        if name:
            nk = normalize_team(name)  # reuse accent-stripping
            df = df[df["Name"].apply(lambda n: nk in normalize_team(n))]
        if nationality:
            nk = normalize_team(nationality)
            df = df[df["Nationality"].apply(lambda n: nk == normalize_team(n))]
        if club:
            ck = normalize_team(club)
            df = df[df["Club"].apply(lambda c: ck in normalize_team(c) if isinstance(c, str) else False)]
        if position:
            pk = position.upper().strip()
            df = df[df["Position"].astype(str).str.upper() == pk]
        if min_overall is not None:
            df = df[df["Overall"].astype(float) >= min_overall]
        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=not desc)
        out = []
        for _, r in df.head(limit).iterrows():
            out.append(self._player_row(r))
        return out

    @staticmethod
    def _player_row(r: pd.Series) -> dict[str, Any]:
        def _get(col: str) -> Any:
            v = r.get(col)
            if isinstance(v, float) and pd.isna(v):
                return None
            return v
        return {
            "id": _get("ID"),
            "name": _get("Name"),
            "age": _get("Age"),
            "nationality": _get("Nationality"),
            "overall": _get("Overall"),
            "potential": _get("Potential"),
            "club": _get("Club"),
            "position": _get("Position"),
            "jersey_number": _get("Jersey Number"),
            "height": _get("Height"),
            "weight": _get("Weight"),
        }

    def top_players(
        self,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        return self.player_search(
            nationality=nationality, club=club, position=position,
            limit=limit, sort_by="Overall", desc=True,
        )

    def brazilians_at_brazilian_clubs(self, limit: int = 25) -> list[dict[str, Any]]:
        """Brazilian players whose club is a known Brazilian club.

        A club is considered Brazilian if its normalized name matches one of
        the teams that appears in the match datasets (heuristic).
        """
        known = set(self.matches["home_key"]) | set(self.matches["away_key"])
        known.discard("")
        df = self.players
        df = df[df["Nationality"].astype(str).apply(lambda n: normalize_team(n) == "brazil")]
        df = df[df["Club"].apply(lambda c: normalize_team(c) in known if isinstance(c, str) else False)]
        df = df.sort_values("Overall", ascending=False)
        out = []
        for _, r in df.head(limit).iterrows():
            out.append(self._player_row(r))
        return out

    def derbies(self, season: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Find matches between known rival pairs."""
        results: list[dict[str, Any]] = []
        for a, b, label in DERBIES:
            m = self._filter(team=a, opponent=b, season=season)
            for _, r in m.head(limit).iterrows():
                rm = self._row_to_match(r)
                rm["derby"] = label
                results.append(rm)
        return results

    # -- introspection -----------------------------------------------------

    def list_competitions(self) -> list[str]:
        return sorted(self.matches["competition"].dropna().unique().tolist())

    def list_seasons(self, competition: str | None = None) -> list[int]:
        m = self.matches
        if competition:
            ck = normalize_comp(competition)
            m = m[m["competition"].apply(lambda c: normalize_comp(c) == ck if isinstance(c, str) else False)]
        return sorted([int(s) for s in m["season"].dropna().unique()])


# ---------------------------------------------------------------------------
# Module-level cached singleton
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_store() -> SoccerStore:
    """Return a process-wide cached :class:`SoccerStore`."""
    return SoccerStore()
