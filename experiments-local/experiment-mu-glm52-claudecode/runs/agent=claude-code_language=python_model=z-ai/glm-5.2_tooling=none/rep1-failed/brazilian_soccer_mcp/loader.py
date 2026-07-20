"""CSV loader that projects every source file into the shared models.

Context
-------
Six Kaggle CSV files live under ``data/kaggle/`` and each uses its own
column names, team-name conventions and date formats (see
``brazilian-soccer-mcp-guide.md``).  Rather than scatter that knowledge
across the query layer, this module owns the mapping from raw rows to the
uniform :class:`~brazilian_soccer_mcp.models.MatchRecord` /
:class:`~brazilian_soccer_mcp.models.PlayerRecord` dataclasses.

The loader also populates a shared :class:`TeamNameNormalizer` so that
"Palmeiras-SP", "Palmeiras" and "palmeiras" all resolve to one canonical
display name for downstream queries.

All file reads use UTF-8 and the Brazilian (``latin-1`` fall-back) encoding
issues are handled by passing ``encoding="utf-8"`` with
``encoding_errors="replace"`` so accented club names survive even if a file
contains a stray byte.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .models import MatchRecord, PlayerRecord
from .normalize import TeamNameNormalizer, parse_date, to_int

# Canonical competition labels used across the server.  These are stable
# identifiers exposed to the LLM via the ``list_competitions`` tool.
COMP_BRASILEIRAO = "Brasileirão Série A"
COMP_COPA_DO_BRASIL = "Copa do Brasil"
COMP_LIBERTADORES = "Copa Libertadores"
COMP_SERIE_B = "Série B"
COMP_SERIE_C = "Série C"
COMP_HISTORIC_BRASILEIRAO = "Brasileirão Série A (histórico 2003-2019)"


DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "kaggle",
)


def _read_csv(path: str) -> pd.DataFrame:
    """Read a CSV as UTF-8 with replacement on bad bytes."""

    return pd.read_csv(path, encoding="utf-8", encoding_errors="replace")


def _safe_int(value, default=None) -> Optional[int]:
    return to_int(value) or default


def _load_brasileirao(path: str, normalizer: TeamNameNormalizer) -> list[MatchRecord]:
    df = _read_csv(path)
    records: list[MatchRecord] = []
    for row in df.itertuples(index=False):
        home = normalizer.register(row.home_team)
        away = normalizer.register(row.away_team)
        records.append(
            MatchRecord(
                date=parse_date(row.datetime),
                season=to_int(getattr(row, "season")),
                competition=COMP_BRASILEIRAO,
                home_team=home,
                away_team=away,
                home_goal=to_int(row.home_goal),
                away_goal=to_int(row.away_goal),
                round=str(getattr(row, "round")) if pd.notna(getattr(row, "round")) else None,
                home_state=str(row.home_team_state) if pd.notna(row.home_team_state) else None,
                away_state=str(row.away_team_state) if pd.notna(row.away_team_state) else None,
                source="Brasileirao_Matches.csv",
            )
        )
    return records


def _load_copa_brasil(path: str, normalizer: TeamNameNormalizer) -> list[MatchRecord]:
    df = _read_csv(path)
    records: list[MatchRecord] = []
    for row in df.itertuples(index=False):
        home = normalizer.register(row.home_team)
        away = normalizer.register(row.away_team)
        records.append(
            MatchRecord(
                date=parse_date(row.datetime),
                season=to_int(getattr(row, "season")),
                competition=COMP_COPA_DO_BRASIL,
                home_team=home,
                away_team=away,
                home_goal=to_int(row.home_goal),
                away_goal=to_int(row.away_goal),
                round=str(getattr(row, "round")) if pd.notna(getattr(row, "round")) else None,
                source="Brazilian_Cup_Matches.csv",
            )
        )
    return records


def _load_libertadores(path: str, normalizer: TeamNameNormalizer) -> list[MatchRecord]:
    df = _read_csv(path)
    records: list[MatchRecord] = []
    for row in df.itertuples(index=False):
        home = normalizer.register(row.home_team)
        away = normalizer.register(row.away_team)
        records.append(
            MatchRecord(
                date=parse_date(row.datetime),
                season=to_int(getattr(row, "season")),
                competition=COMP_LIBERTADORES,
                home_team=home,
                away_team=away,
                home_goal=to_int(row.home_goal),
                away_goal=to_int(row.away_goal),
                stage=str(row.stage) if pd.notna(row.stage) else None,
                source="Libertadores_Matches.csv",
            )
        )
    return records


def _load_br_football(path: str, normalizer: TeamNameNormalizer) -> list[MatchRecord]:
    df = _read_csv(path)
    # Map the free-text ``tournament`` column to canonical competition labels.
    tourney_map = {
        "Serie A": COMP_BRASILEIRAO,
        "Serie B": COMP_SERIE_B,
        "Serie C": COMP_SERIE_C,
        "Copa do Brasil": COMP_COPA_DO_BRASIL,
    }
    records: list[MatchRecord] = []
    for row in df.itertuples(index=False):
        home = normalizer.register(row.home)
        away = normalizer.register(row.away)
        tournament = str(row.tournament) if pd.notna(row.tournament) else "Unknown"
        competition = tourney_map.get(tournament, tournament)
        records.append(
            MatchRecord(
                date=parse_date(row.date),
                season=parse_date(row.date).year if parse_date(row.date) else None,
                competition=competition,
                home_team=home,
                away_team=away,
                home_goal=to_int(row.home_goal),
                away_goal=to_int(row.away_goal),
                home_corners=float(row.home_corner) if pd.notna(row.home_corner) else None,
                away_corners=float(row.away_corner) if pd.notna(row.away_corner) else None,
                home_shots=float(row.home_shots) if pd.notna(row.home_shots) else None,
                away_shots=float(row.away_shots) if pd.notna(row.away_shots) else None,
                home_attacks=float(row.home_attack) if pd.notna(row.home_attack) else None,
                away_attacks=float(row.away_attack) if pd.notna(row.away_attack) else None,
                total_corners=float(row.total_corners) if pd.notna(row.total_corners) else None,
                source="BR-Football-Dataset.csv",
            )
        )
    return records


def _load_historic(path: str, normalizer: TeamNameNormalizer) -> list[MatchRecord]:
    df = _read_csv(path)
    records: list[MatchRecord] = []
    for row in df.itertuples(index=False):
        home = normalizer.register(row.Equipe_mandante)
        away = normalizer.register(row.Equipe_visitante)
        records.append(
            MatchRecord(
                date=parse_date(row.Data),
                season=to_int(row.Ano),
                # The historical 2003-2019 dataset is the same Brasileirão
                # Série A competition; merging it into the canonical label
                # lets cross-file deduplication collapse the 2012-2019
                # overlap with the modern file below.
                competition=COMP_BRASILEIRAO,
                home_team=home,
                away_team=away,
                home_goal=to_int(row.Gols_mandante),
                away_goal=to_int(row.Gols_visitante),
                round=str(row.Rodada) if pd.notna(row.Rodada) else None,
                home_state=str(row.Mandante_UF) if pd.notna(row.Mandante_UF) else None,
                away_state=str(row.Visitante_UF) if pd.notna(row.Visitante_UF) else None,
                venue=str(row.Arena) if pd.notna(row.Arena) else None,
                source="novo_campeonato_brasileiro.csv",
            )
        )
    return records


def _load_fifa(path: str) -> list[PlayerRecord]:
    df = _read_csv(path)
    # The file has a leading unnamed index column ("BOM" header quirk); drop it.
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])
    records: list[PlayerRecord] = []
    for row in df.itertuples(index=False):
        records.append(
            PlayerRecord(
                id=int(row.ID) if pd.notna(row.ID) else -1,
                name=str(row.Name),
                age=to_int(row.Age),
                nationality=str(row.Nationality) if pd.notna(row.Nationality) else "",
                overall=int(row.Overall) if pd.notna(row.Overall) else 0,
                potential=int(row.Potential) if pd.notna(row.Potential) else 0,
                club=str(row.Club) if pd.notna(row.Club) else "",
                position=str(row.Position) if pd.notna(row.Position) else "",
                jersey_number=to_int(getattr(row, "Jerney_Number", getattr(row, "Jersey_Number", None))),
                height=str(row.Height) if pd.notna(row.Height) else None,
                weight=str(row.Weight) if pd.notna(row.Weight) else None,
                preferred_foot=str(getattr(row, "Preferred_Foot", "")) if pd.notna(getattr(row, "Preferred_Foot", "")) else None,
                crossing=to_int(getattr(row, "Crossing", None)),
                finishing=to_int(getattr(row, "Finishing", None)),
                dribbling=to_int(getattr(row, "Dribbling", None)),
                short_passing=to_int(getattr(row, "ShortPassing", None)),
                long_shots=to_int(getattr(row, "LongShots", None)),
                sprint_speed=to_int(getattr(row, "SprintSpeed", None)),
                standing_tackle=to_int(getattr(row, "StandingTackle", None)),
                gk_reflexes=to_int(getattr(row, "GKReflexes", None)),
            )
        )
    return records


@dataclass
class Dataset:
    """In-memory knowledge graph of all loaded data."""

    matches: list[MatchRecord]
    players: list[PlayerRecord]
    normalizer: TeamNameNormalizer
    data_dir: str

    # Convenience accessors -------------------------------------------------

    def teams_for_competition(self, competition: str) -> list[str]:
        teams: set[str] = set()
        for m in self.matches:
            if m.competition == competition:
                teams.add(m.home_team)
                teams.add(m.away_team)
        return sorted(teams)

    def seasons_for_competition(self, competition: str) -> list[int]:
        seasons = {
            m.season for m in self.matches if m.competition == competition and m.season is not None
        }
        return sorted(seasons)

    def competitions(self) -> list[str]:
        return sorted({m.competition for m in self.matches})


def _merge_matches(raw_matches: list[MatchRecord]) -> list[MatchRecord]:
    """Deduplicate and merge match records across source files.

    The five match files overlap:

    * ``BR-Football-Dataset.csv`` re-exports many Série A / Copa do Brasil
      fixtures that already appear in the primary match files, but its
      dates are consistently offset by ±1 day (a play-date / timezone
      quirk), so exact-date dedup misses them.
    * The historical 2003-2019 Brasileirão overlaps the modern file for
      2012-2019 (these share exact dates and merge cleanly).

    The merge identity is ``(competition, season, home_team, away_team,
    home_goal, away_goal)`` with a **±2 day date tolerance** to absorb the
    BR-Football offset.  For each unique match we keep the first
    non-``None`` value of every field in *source-priority order* (primary
    match files first, ``BR-Football-Dataset`` last so its
    corner/shot/attack statistics are grafted onto the primary record
    without overriding round/stage/venue).
    """

    from datetime import timedelta

    from .normalize import team_match_key

    # Source priority: lower = preferred for descriptive fields.
    priority = {
        "Brasileirao_Matches.csv": 0,
        "Brazilian_Cup_Matches.csv": 0,
        "Libertadores_Matches.csv": 0,
        "novo_campeonato_brasileiro.csv": 1,
        "BR-Football-Dataset.csv": 2,
    }
    raw_matches = sorted(raw_matches, key=lambda m: priority.get(m.source, 9))

    # Index keyed by (competition, season, home, away, score) -> list of
    # (date, MatchRecord).  Looking up the bucket then scanning for a date
    # within ±2 days lets the BR-Football offset merge cleanly.
    index: dict[tuple, list[tuple] | None] = {}
    # Preserve insertion order of canonical records for deterministic output.
    ordered: list[MatchRecord] = []

    def _bucket(m: MatchRecord) -> tuple:
        return (
            m.competition,
            m.season,
            team_match_key(m.home_team),
            team_match_key(m.away_team),
            m.home_goal,
            m.away_goal,
        )

    def _combine(existing: MatchRecord, m: MatchRecord) -> MatchRecord:
        return MatchRecord(
            date=existing.date or m.date,
            season=existing.season or m.season,
            competition=existing.competition or m.competition,
            home_team=existing.home_team,
            away_team=existing.away_team,
            home_goal=existing.home_goal,
            away_goal=existing.away_goal,
            round=existing.round or m.round,
            stage=existing.stage or m.stage,
            home_state=existing.home_state or m.home_state,
            away_state=existing.away_state or m.away_state,
            venue=existing.venue or m.venue,
            home_corners=existing.home_corners or m.home_corners,
            away_corners=existing.away_corners or m.away_corners,
            home_shots=existing.home_shots or m.home_shots,
            away_shots=existing.away_shots or m.away_shots,
            home_attacks=existing.home_attacks or m.home_attacks,
            away_attacks=existing.away_attacks or m.away_attacks,
            total_corners=existing.total_corners or m.total_corners,
            source=existing.source,
        )

    for m in raw_matches:
        if m.date is None or m.home_goal is None or m.away_goal is None:
            ordered.append(m)
            continue
        bucket = _bucket(m)
        entries = index.get(bucket)
        partner = None
        if entries is not None:
            for d, rec in entries:
                if abs((m.date - d).days) <= 2:
                    partner = rec
                    break
        if partner is None:
            index.setdefault(bucket, []).append((m.date, m))
            ordered.append(m)
            continue
        merged_rec = _combine(partner, m)
        # Replace the partner in place (keep its index slot).
        idx = ordered.index(partner)
        ordered[idx] = merged_rec
        entries = index[bucket]
        for i, (d, rec) in enumerate(entries):
            if rec is partner:
                entries[i] = (d, merged_rec)
                break
    return ordered


def load_dataset(data_dir: Optional[str] = None) -> Dataset:
    """Load all six CSV files into a :class:`Dataset` knowledge graph.

    Parameters
    ----------
    data_dir:
        Directory containing the Kaggle CSVs.  Defaults to the
        ``data/kaggle`` folder at the repository root.
    """

    data_dir = data_dir or DEFAULT_DATA_DIR
    normalizer = TeamNameNormalizer()

    matches: list[MatchRecord] = []
    matches += _load_brasileirao(os.path.join(data_dir, "Brasileirao_Matches.csv"), normalizer)
    matches += _load_copa_brasil(os.path.join(data_dir, "Brazilian_Cup_Matches.csv"), normalizer)
    matches += _load_libertadores(os.path.join(data_dir, "Libertadores_Matches.csv"), normalizer)
    matches += _load_br_football(os.path.join(data_dir, "BR-Football-Dataset.csv"), normalizer)
    matches += _load_historic(os.path.join(data_dir, "novo_campeonato_brasileiro.csv"), normalizer)

    # Collapse cross-file duplicates (BR-Football re-exports Série A / Copa
    # do Brasil rows; the historical 2003-2019 file overlaps the modern one
    # for 2012-2019) so standings and head-to-head counts are not inflated.
    matches = _merge_matches(matches)

    players = _load_fifa(os.path.join(data_dir, "fifa_data.csv"))

    return Dataset(
        matches=matches,
        players=players,
        normalizer=normalizer,
        data_dir=data_dir,
    )
