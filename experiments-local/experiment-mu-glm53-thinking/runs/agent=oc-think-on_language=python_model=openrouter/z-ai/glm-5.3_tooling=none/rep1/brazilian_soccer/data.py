"""Loading and unification of the six Kaggle CSV datasets.

Source files (data/kaggle/):
- Brasileirao_Matches.csv      Brasileirão Série A 2012-2022 (round data)
- novo_campeonato_brasileiro.csv  Brasileirão Série A 2003-2019 (stadium data)
- Brazilian_Cup_Matches.csv    Copa do Brasil 2012-2021 (round data)
- Libertadores_Matches.csv      Copa Libertadores 2013-2022 (stage data)
- BR-Football-Dataset.csv       Série A/B/C + Copa do Brasil 2014-2023
                               (corners/shots/attacks statistics)
- fifa_data.csv                 18,207 players

The files overlap: the same fixture appears in several files with slightly
different team spellings and dates. To avoid double counting, every
(competition, season) is served from one *primary* source, chosen by the
SOURCE_PRIORITY order below (richest schedule/round data first). The
BR-Football records are additionally kept as an extended-statistics layer
and joined onto the primary matches.
"""

from __future__ import annotations

import csv
import datetime as dt
from collections import Counter, defaultdict
from pathlib import Path

from .dates import parse_date, parse_int, parse_money_eur
from .models import Match, MatchStats, Player
from .normalize import (
    TeamResolutionError,
    display_name,
    fold_text,
    similar_names,
    team_key,
)

KAGGLE_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

# First source with matches for a (competition, season) wins; later sources
# only fill seasons the earlier ones do not cover.
SOURCE_PRIORITY: dict[str, list[str]] = {
    SERIE_A: ["brasileirao_matches", "historico", "br_football"],
    SERIE_B: ["br_football"],
    SERIE_C: ["br_football"],
    COPA_DO_BRASIL: ["brazilian_cup", "br_football"],
    LIBERTADORES: ["libertadores"],
}

BR_FOOTBALL_COMPETITIONS = {
    "Serie A": SERIE_A,
    "Serie B": SERIE_B,
    "Serie C": SERIE_C,
    "Copa do Brasil": COPA_DO_BRASIL,
}

FIFA_SKILL_COLUMNS = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
    "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
    "Composure", "Marking", "StandingTackle", "SlidingTackle",
    "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
]

POSITION_GROUPS: dict[str, set[str]] = {
    "goalkeepers": {"GK"},
    "defenders": {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"},
    "midfielders": {
        "CM", "LCM", "RCM", "CDM", "LDM", "RDM", "LM", "RM", "CAM", "LAM", "RAM",
    },
    "forwards": {"ST", "LS", "RS", "LW", "RW", "LF", "RF", "CF"},
}


class TeamInfo:
    """Everything known about one canonical team across all files."""

    def __init__(self, key: str) -> None:
        self.key = key
        self.variants: Counter[str] = Counter()
        self.sources: set[str] = set()

    @property
    def display(self) -> str:
        return display_name(self.key, self.variants.most_common(1)[0][0])

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.display,
            "variants": [
                {"name": raw, "matches": count}
                for raw, count in self.variants.most_common()
            ],
            "sources": sorted(self.sources),
        }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class SoccerData:
    """In-memory knowledge base over the six datasets."""

    def __init__(self, kaggle_dir: str | Path = KAGGLE_DIR) -> None:
        self.data_dir = Path(kaggle_dir)
        self.teams: dict[str, TeamInfo] = {}
        self._team_matches: dict[str, list[Match]] = defaultdict(list)
        self.matches: list[Match] = []
        self.extended_stats_matches: list[Match] = []
        self.players: list[Player] = []
        self._players_by_folded_name: dict[str, Player] = {}
        self._load_all()

    # ------------------------------------------------------------------ load

    def _load_all(self) -> None:
        raw_by_source: dict[str, list[Match]] = defaultdict(list)
        for match in self._load_brasileirao_matches():
            raw_by_source["brasileirao_matches"].append(match)
        for match in self._load_historico():
            raw_by_source["historico"].append(match)
        for match in self._load_brazilian_cup():
            raw_by_source["brazilian_cup"].append(match)
        for match in self._load_libertadores():
            raw_by_source["libertadores"].append(match)
        for match in self._load_br_football():
            raw_by_source["br_football"].append(match)

        chosen = self._choose_primary_sources(raw_by_source)
        for match in chosen:
            self._add_match(match)

        self.extended_stats_matches = [
            m for m in raw_by_source["br_football"] if m.stats is not None
        ]
        self._attach_extended_stats()
        self.players = self._load_fifa_players()
        for player in self.players:
            folded = fold_text(player.name)
            if folded and folded not in self._players_by_folded_name:
                self._players_by_folded_name[folded] = player

    def _choose_primary_sources(
        self, raw_by_source: dict[str, list[Match]]
    ) -> list[Match]:
        """Serve each (competition, season) from its best-priority source only."""
        pools: dict[tuple[str, int | None], set[str]] = defaultdict(set)
        for source, matches in raw_by_source.items():
            for match in matches:
                pools[(match.competition, match.season)].add(source)
        primary_source: dict[tuple[str, int | None], set[str]] = {}
        for key, pool in pools.items():
            priority = SOURCE_PRIORITY.get(key[0], [])
            ranked = [s for s in priority if s in pool]
            primary_source[key] = set(ranked[:1]) if ranked else pool
        chosen: list[Match] = []
        for source, matches in raw_by_source.items():
            for match in matches:
                if source in primary_source[(match.competition, match.season)]:
                    chosen.append(match)
        chosen.sort(key=lambda m: (m.date or dt.date.min, m.competition))
        return chosen

    def _add_match(self, match: Match) -> None:
        self.matches.append(match)
        self._team_matches[match.home].append(match)
        self._team_matches[match.away].append(match)

    def _register_team(self, key: str, source: str, raw: str | None = None) -> None:
        info = self.teams.setdefault(key, TeamInfo(key))
        info.sources.add(source)
        if raw:
            info.variants[raw] += 1

    # -------------------------------------------------------------- loaders

    def _load_brasileirao_matches(self) -> list[Match]:
        rows = _read_csv(self.data_dir / "Brasileirao_Matches.csv")
        matches = []
        for row in rows:
            raw_home, raw_away = row["home_team"], row["away_team"]
            match = Match(
                competition=SERIE_A,
                season=parse_int(row.get("season")),
                home=team_key(raw_home),
                away=team_key(raw_away),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                date=parse_date(row.get("datetime")),
                time=str(row["datetime"]).split(" ")[1]
                if " " in str(row.get("datetime", ""))
                else None,
                round_number=parse_int(row.get("round")),
                source="Brasileirao_Matches.csv",
            )
            self._register_team(match.home, match.source, raw_home)
            self._register_team(match.away, match.source, raw_away)
            matches.append(match)
        return matches

    def _load_historico(self) -> list[Match]:
        rows = _read_csv(self.data_dir / "novo_campeonato_brasileiro.csv")
        matches = []
        for row in rows:
            raw_home, raw_away = row["Equipe_mandante"], row["Equipe_visitante"]
            match = Match(
                competition=SERIE_A,
                season=parse_int(row.get("Ano")),
                home=team_key(raw_home),
                away=team_key(raw_away),
                home_goals=parse_int(row.get("Gols_mandante")),
                away_goals=parse_int(row.get("Gols_visitante")),
                date=parse_date(row.get("Data")),
                round_number=parse_int(row.get("Rodada")),
                venue=row.get("Arena") or None,
                source="novo_campeonato_brasileiro.csv",
            )
            self._register_team(match.home, match.source, raw_home)
            self._register_team(match.away, match.source, raw_away)
            matches.append(match)
        return matches

    def _load_brazilian_cup(self) -> list[Match]:
        rows = _read_csv(self.data_dir / "Brazilian_Cup_Matches.csv")
        matches = []
        for row in rows:
            raw_home, raw_away = row["home_team"], row["away_team"]
            match = Match(
                competition=COPA_DO_BRASIL,
                season=parse_int(row.get("season")),
                home=team_key(raw_home),
                away=team_key(raw_away),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                date=parse_date(row.get("datetime")),
                time=str(row["datetime"]).split(" ")[1]
                if " " in str(row.get("datetime", ""))
                else None,
                round_number=parse_int(row.get("round")),
                source="Brazilian_Cup_Matches.csv",
            )
            self._register_team(match.home, match.source, raw_home)
            self._register_team(match.away, match.source, raw_away)
            matches.append(match)
        return matches

    def _load_libertadores(self) -> list[Match]:
        rows = _read_csv(self.data_dir / "Libertadores_Matches.csv")
        matches = []
        for row in rows:
            raw_home, raw_away = row["home_team"], row["away_team"]
            match = Match(
                competition=LIBERTADORES,
                season=parse_int(row.get("season")),
                home=team_key(raw_home),
                away=team_key(raw_away),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                date=parse_date(row.get("datetime")),
                time=str(row["datetime"]).split(" ")[1]
                if " " in str(row.get("datetime", ""))
                else None,
                stage=row.get("stage") or None,
                source="Libertadores_Matches.csv",
            )
            self._register_team(match.home, match.source, raw_home)
            self._register_team(match.away, match.source, raw_away)
            matches.append(match)
        return matches

    def _load_br_football(self) -> list[Match]:
        rows = _read_csv(self.data_dir / "BR-Football-Dataset.csv")
        matches = []
        for row in rows:
            raw_home, raw_away = row["home"], row["away"]
            stats = MatchStats(
                home_corners=parse_int(row.get("home_corner")),
                away_corners=parse_int(row.get("away_corner")),
                home_shots=parse_int(row.get("home_shots")),
                away_shots=parse_int(row.get("away_shots")),
                home_attacks=parse_int(row.get("home_attack")),
                away_attacks=parse_int(row.get("away_attack")),
                home_halftime=parse_int(row.get("ht_result")),
                away_halftime=parse_int(row.get("at_result")),
            )
            match = Match(
                competition=BR_FOOTBALL_COMPETITIONS.get(
                    row["tournament"], row["tournament"]
                ),
                season=parse_int((row.get("date") or "")[:4]),
                home=team_key(raw_home),
                away=team_key(raw_away),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                date=parse_date(row.get("date")),
                time=(row.get("time") or "").strip() or None,
                stats=stats,
                source="BR-Football-Dataset.csv",
            )
            self._register_team(match.home, match.source, raw_home)
            self._register_team(match.away, match.source, raw_away)
            matches.append(match)
        return matches

    def _load_fifa_players(self) -> list[Player]:
        rows = _read_csv(self.data_dir / "fifa_data.csv")
        players = []
        for row in rows:
            club = (row.get("Club") or "").strip() or None
            skills = {}
            for column in FIFA_SKILL_COLUMNS:
                value = parse_int(row.get(column))
                if value is not None:
                    skills[column] = value
            player = Player(
                player_id=parse_int(row.get("ID")) or 0,
                name=(row.get("Name") or "").strip(),
                age=parse_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip(),
                overall=parse_int(row.get("Overall")) or 0,
                potential=parse_int(row.get("Potential")) or 0,
                club=club,
                position=(row.get("Position") or "").strip() or None,
                jersey_number=parse_int(row.get("Jersey Number")),
                height=(row.get("Height") or "").strip() or None,
                weight=(row.get("Weight") or "").strip() or None,
                preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
                value_eur=parse_money_eur(row.get("Value")),
                skills=skills,
            )
            if player.name:
                players.append(player)
        return players

    # -------------------------------------------------------- stats joining

    def _attach_extended_stats(self) -> None:
        index: dict[tuple[str, int | None, str, str], list[Match]] = defaultdict(list)
        for match in self.matches:
            index[
                (match.competition, match.season, match.home, match.away)
            ].append(match)
        used: set[int] = set()
        for extended in self.extended_stats_matches:
            bucket = index.get(
                (extended.competition, extended.season, extended.home, extended.away)
            )
            if not bucket:
                continue
            candidates = [
                (abs((m.date - extended.date).days) if m.date and extended.date else 0, i, m)
                for i, m in enumerate(bucket)
                if id(m) not in used
            ]
            if not candidates:
                continue
            _, _, target = min(candidates, key=lambda c: (c[0], c[1]))
            target.stats = extended.stats
            used.add(id(target))

    # ------------------------------------------------------------ accessors

    def team_keys(self) -> list[str]:
        return sorted(self.teams)

    def resolve_team(self, name: str) -> str:
        """Resolve a user-supplied name to a canonical team key."""
        key = team_key(name)
        if key in self.teams:
            return key
        folded = fold_text(name)
        for team_key_, info in self.teams.items():
            if fold_text(info.display) == folded or fold_text(team_key_) == folded:
                return team_key_
        suggestions = similar_names(
            folded, [fold_text(i.display) for i in self.teams.values()]
        )
        raise TeamResolutionError(
            f"Team '{name}' not found in the datasets. "
            f"Similar names: {', '.join(suggestions) if suggestions else 'none found'}. "
            f"Use the resolve_team tool to explore known teams."
        )

    def matches_for_team(self, key: str) -> list[Match]:
        return self._team_matches.get(key, [])

    def player_by_name(self, name: str) -> Player | None:
        return self._players_by_folded_name.get(fold_text(name))

    def team_names(self) -> list[str]:
        return [self.teams[k].display for k in self.team_keys()]


_soccer_data: SoccerData | None = None


def get_soccer_data() -> SoccerData:
    """Process-wide singleton (server startup loads once, queries stay fast)."""
    global _soccer_data
    if _soccer_data is None:
        _soccer_data = SoccerData()
    return _soccer_data
