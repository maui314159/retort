"""Dataset loading and unification.

CONTEXT
-------
Six CSV files live under ``data/kaggle/`` and are loaded here into a
single :class:`Data` object.  Match files differ in schema, language and
date format, so each is parsed by a dedicated loader and then projected
onto a *common match schema* stored in ``Data.matches``:

    source        : origin file tag
    date          : parsed datetime (NaT if unknown)
    competition   : canonical competition label
    home, away    : display team names (suffix/notes stripped, accents kept)
    home_key, away_key : canonical team ids (state-retaining, alias-resolved)
    home_goals, away_goals : int (None for unplayed matches)
    season        : int year
    round         : round number / label (nullable)
    stage         : cup stage (nullable)
    arena         : stadium (nullable)
    home_corners, away_corners, home_shots, away_shots : extended stats
                                                       (nullable, from
                                                       BR-Football only)

This unified frame powers every match/team/competition/statistical query.
The FIFA player table is kept separately in ``Data.players``.

Team-name normalisation is the trickiest part: short names like
"Atlético" are shared by clubs from different states, so canonical keys
*retain* the state token and an alias map (built once from all raw
names) reconciles the various spellings -- see :mod:`.normalize`.
"""

from __future__ import annotations

import os
import unicodedata
from functools import lru_cache
from typing import Optional

import pandas as pd

from .normalize import (
    build_alias_map,
    canonical_key,
    display_name,
    parse_date,
    resolve_team_key,
)

# Default location of the bundled datasets (relative to repo root).
DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "kaggle",
)

# Canonical competition labels.
BRASILEIRAO_A = "Brasileirão Serie A"
BRASILEIRAO_B = "Brasileirão Serie B"
BRASILEIRAO_C = "Brasileirão Serie C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

_BR_FOOTBALL_TOURNAMENT_MAP = {
    "Serie A": BRASILEIRAO_A,
    "Serie B": BRASILEIRAO_B,
    "Serie C": BRASILEIRAO_C,
    "Copa do Brasil": COPA_DO_BRASIL,
}


def _to_int(value) -> Optional[int]:
    """Coerce a goal value (float/str/int) to int, or None if missing."""
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        f = float(value)
        if pd.isna(f):
            return None
        return int(f)
    except (TypeError, ValueError):
        return None


def _to_year(value) -> Optional[int]:
    """Coerce a season value to int year, or None if missing."""
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        f = float(value)
        if pd.isna(f):
            return None
        return int(f)
    except (TypeError, ValueError):
        return None


def _has_accent(name: str) -> int:
    return int(any(unicodedata.combining(ch)
                   for ch in unicodedata.normalize("NFKD", name)))


class Data:
    """Container for the loaded and unified datasets."""

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR):
        self.data_dir = data_dir
        # Build the team alias map first by scanning every raw team name.
        self.alias_map = build_alias_map(self._all_raw_team_names())
        self.players = self._load_players()
        self.matches = self._load_matches()
        self.team_display = self._build_team_display()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def resolve_team(self, name) -> str:
        """Resolve a user-typed or raw team name to its canonical id."""
        return resolve_team_key(self.alias_map, name)

    def team_name(self, key) -> str:
        """Return the preferred display name for a canonical team id."""
        from .normalize import DISPLAY_OVERRIDES, titlecase_name
        return (DISPLAY_OVERRIDES.get(key)
                or self.team_display.get(key)
                or titlecase_name(display_name(key)))

    # ------------------------------------------------------------------
    # Raw name collection (for alias-map construction)
    # ------------------------------------------------------------------
    def _all_raw_team_names(self) -> list[str]:
        names: list[str] = []
        sources = [
            ("Brasileirao_Matches.csv", ["home_team", "away_team"]),
            ("Brazilian_Cup_Matches.csv", ["home_team", "away_team"]),
            ("Libertadores_Matches.csv", ["home_team", "away_team"]),
            ("BR-Football-Dataset.csv", ["home", "away"]),
            ("novo_campeonato_brasileiro.csv",
             ["Equipe_mandante", "Equipe_visitante"]),
        ]
        for fname, cols in sources:
            path = os.path.join(self.data_dir, fname)
            if not os.path.exists(path):
                continue
            try:
                df = pd.read_csv(path, usecols=cols, nrows=1)
            except ValueError:
                continue
            df = pd.read_csv(path, usecols=cols)
            for col in cols:
                names.extend(str(v) for v in df[col].dropna().tolist())
        return names

    # ------------------------------------------------------------------
    # Individual loaders
    # ------------------------------------------------------------------
    def _load_players(self) -> pd.DataFrame:
        path = os.path.join(self.data_dir, "fifa_data.csv")
        df = pd.read_csv(path, encoding="utf-8-sig")
        # Drop the unnamed leading index column (header is empty string).
        df = df.drop(columns=[c for c in df.columns if str(c) == ""])
        df["Name"] = df["Name"].fillna("").astype(str)
        df["Club"] = df["Club"].fillna("").astype(str)
        df["Nationality"] = df["Nationality"].fillna("").astype(str)
        df["Position"] = df["Position"].fillna("").astype(str)
        for col in ("Overall", "Potential", "Age", "Jersey Number"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        # Resolve club to a canonical team id so player queries can join
        # with match data for Brazilian clubs.
        df["club_key"] = df["Club"].map(self.resolve_team)
        return df

    def _load_matches(self) -> pd.DataFrame:
        frames = [
            self._load_brasileirao(),
            self._load_cup(),
            self._load_libertadores(),
            self._load_br_football(),
            self._load_historical(),
        ]
        df = pd.concat(frames, ignore_index=True)
        df["home_goals"] = pd.to_numeric(df["home_goals"], errors="coerce")
        df["away_goals"] = pd.to_numeric(df["away_goals"], errors="coerce")
        df["season"] = pd.to_numeric(df["season"], errors="coerce")
        df = self._dedupe(df)
        df = df.sort_values("date", ascending=False, kind="mergesort",
                            na_position="last").reset_index(drop=True)
        return df

    def _dedupe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Collapse the same match filed by multiple sources into one row.

        The five match files overlap heavily (e.g. a 2019 Brasileirão
        match appears in Brasileirao_Matches, BR-Football and the
        historical archive), and sources sometimes disagree on the
        kick-off date by a day.  In these competitions the ordered
        (home, away) pairing is unique per season+competition, so we
        collapse on (season, competition, home_key, away_key), preferring
        the dedicated source (richer round/stage metadata) while merging
        in extended corner/shot stats from BR-Football.
        """
        df = df.copy()
        key_cols = ["season", "competition", "home_key", "away_key"]

        # Extended-stats lookup from BR-Football rows, keyed by pairing.
        stats: dict[tuple, tuple] = {}
        br = df[df["source"] == "BR-Football-Dataset"]
        for _, r in br.iterrows():
            k = (r["season"], r["competition"], r["home_key"], r["away_key"])
            stats[k] = (r["home_corners"], r["away_corners"],
                        r["home_shots"], r["away_shots"])

        # Source priority: dedicated files (round/stage) before the
        # extended-stats file before the historical archive.
        priority = {
            "Brasileirao_Matches": 0,
            "Brazilian_Cup_Matches": 0,
            "Libertadores_Matches": 0,
            "BR-Football-Dataset": 1,
            "novo_campeonato_brasileiro": 2,
        }
        df["_pri"] = df["source"].map(priority).fillna(9).astype(int)
        df = df.sort_values(key_cols + ["_pri"], kind="mergesort",
                            na_position="last")
        kept = df.drop_duplicates(subset=key_cols, keep="first").copy()

        # Backfill extended stats where the kept row is missing them.
        for idx, r in kept.iterrows():
            k = (r["season"], r["competition"], r["home_key"], r["away_key"])
            st = stats.get(k)
            if st and pd.isna(r["home_corners"]):
                kept.at[idx, "home_corners"] = st[0]
                kept.at[idx, "away_corners"] = st[1]
                kept.at[idx, "home_shots"] = st[2]
                kept.at[idx, "away_shots"] = st[3]

        return kept.drop(columns=["_pri"])

    def _common_row(self, source, competition, home, away, home_goals,
                    away_goals, season, date, round_=None, stage=None,
                    arena=None, home_corners=None, away_corners=None,
                    home_shots=None, away_shots=None) -> dict:
        return {
            "source": source,
            "date": date,
            "competition": competition,
            "home": display_name(home) if home is not None else "",
            "away": display_name(away) if away is not None else "",
            "home_key": self.resolve_team(home),
            "away_key": self.resolve_team(away),
            "home_goals": _to_int(home_goals),
            "away_goals": _to_int(away_goals),
            "season": _to_year(season),
            "round": round_,
            "stage": stage,
            "arena": arena,
            "home_corners": _to_int(home_corners),
            "away_corners": _to_int(away_corners),
            "home_shots": _to_int(home_shots),
            "away_shots": _to_int(away_shots),
        }

    def _load_brasileirao(self) -> pd.DataFrame:
        path = os.path.join(self.data_dir, "Brasileirao_Matches.csv")
        raw = pd.read_csv(path)
        rows = [
            self._common_row(
                source="Brasileirao_Matches",
                competition=BRASILEIRAO_A,
                home=r["home_team"],
                away=r["away_team"],
                home_goals=r["home_goal"],
                away_goals=r["away_goal"],
                season=r["season"],
                date=parse_date(r["datetime"]),
                round_=int(r["round"]) if pd.notna(r["round"]) else None,
            )
            for _, r in raw.iterrows()
        ]
        return pd.DataFrame(rows)

    def _load_cup(self) -> pd.DataFrame:
        path = os.path.join(self.data_dir, "Brazilian_Cup_Matches.csv")
        raw = pd.read_csv(path)
        rows = [
            self._common_row(
                source="Brazilian_Cup_Matches",
                competition=COPA_DO_BRASIL,
                home=r["home_team"],
                away=r["away_team"],
                home_goals=r["home_goal"],
                away_goals=r["away_goal"],
                season=r["season"],
                date=parse_date(r["datetime"]),
                round_=str(r["round"]),
            )
            for _, r in raw.iterrows()
        ]
        return pd.DataFrame(rows)

    def _load_libertadores(self) -> pd.DataFrame:
        path = os.path.join(self.data_dir, "Libertadores_Matches.csv")
        raw = pd.read_csv(path)
        rows = [
            self._common_row(
                source="Libertadores_Matches",
                competition=LIBERTADORES,
                home=r["home_team"],
                away=r["away_team"],
                home_goals=r["home_goal"],
                away_goals=r["away_goal"],
                season=r["season"],
                date=parse_date(r["datetime"]),
                stage=str(r["stage"]) if pd.notna(r["stage"]) else None,
            )
            for _, r in raw.iterrows()
        ]
        return pd.DataFrame(rows)

    def _load_br_football(self) -> pd.DataFrame:
        path = os.path.join(self.data_dir, "BR-Football-Dataset.csv")
        raw = pd.read_csv(path)
        rows = []
        for _, r in raw.iterrows():
            comp = _BR_FOOTBALL_TOURNAMENT_MAP.get(
                str(r["tournament"]).strip(),
                str(r["tournament"]).strip(),
            )
            match_date = parse_date(r["date"])
            rows.append(self._common_row(
                source="BR-Football-Dataset",
                competition=comp,
                home=r["home"],
                away=r["away"],
                home_goals=r["home_goal"],
                away_goals=r["away_goal"],
                season=match_date.year if match_date else None,
                date=match_date,
                home_corners=r.get("home_corner"),
                away_corners=r.get("away_corner"),
                home_shots=r.get("home_shots"),
                away_shots=r.get("away_shots"),
            ))
        return pd.DataFrame(rows)

    def _load_historical(self) -> pd.DataFrame:
        path = os.path.join(self.data_dir, "novo_campeonato_brasileiro.csv")
        raw = pd.read_csv(path)
        rows = [
            self._common_row(
                source="novo_campeonato_brasileiro",
                competition=BRASILEIRAO_A,
                home=r["Equipe_mandante"],
                away=r["Equipe_visitante"],
                home_goals=r["Gols_mandante"],
                away_goals=r["Gols_visitante"],
                season=r["Ano"],
                date=parse_date(r["Data"]),
                round_=int(r["Rodada"]) if pd.notna(r["Rodada"]) else None,
                arena=str(r["Arena"]) if pd.notna(r["Arena"]) else None,
            )
            for _, r in raw.iterrows()
        ]
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    def _build_team_display(self) -> dict[str, str]:
        """Map canonical team id -> preferred display name.

        Among all spellings observed for a given id, prefer an accented
        one (``São Paulo`` over ``Sao Paulo``), tie-broken by frequency.
        Falls back to :func:`display_name` of the id itself.
        """
        pairs = pd.DataFrame({
            "key": pd.concat([self.matches["home_key"], self.matches["away_key"]],
                             ignore_index=True),
            "name": pd.concat([self.matches["home"], self.matches["away"]],
                              ignore_index=True),
        })
        pairs = pairs[pairs["key"] != ""]
        out: dict[str, str] = {}
        if pairs.empty:
            return out
        for key, group in pairs.groupby("key"):
            counts = group["name"].value_counts()
            best = max(counts.items(),
                       key=lambda kv: (_has_accent(kv[0]), kv[1]))
            out[key] = best[0]
        return out


@lru_cache(maxsize=4)
def get_data(data_dir: str = DEFAULT_DATA_DIR) -> Data:
    """Return a process-wide cached :class:`Data` instance."""
    return Data(data_dir=data_dir)
