"""Load the six Kaggle CSV files into one unified knowledge graph.

Sources and how they are combined:

1. ``Brasileirao_Matches.csv``      -> Brasileirão Serie A, 2012-2022
2. ``novo_campeonato_brasileiro.csv`` -> Brasileirão Serie A, 2003-2019
   (duplicate 2012-2019 fixtures are dropped; the two files agree on every
   overlapping score and round)
3. ``BR-Football-Dataset.csv``      -> extended stats (corners/shots/attacks)
   for Serie A (2014-2023), Serie B, Serie C and Copa do Brasil (2014-2023).
   For Serie A and the Copa its rows either enrich an already-loaded fixture
   with stats, fill in the score of a fixture recorded as unplayed, or add a
   fixture the primary files do not cover (notably 2022 late rounds and the
   2023 season).
4. ``Brazilian_Cup_Matches.csv``    -> Copa do Brasil, 2012-2021 (rounds).
5. ``Libertadores_Matches.csv``     -> Copa Libertadores, 2013-2022 (stages).
6. ``fifa_data.csv``                -> 18,207 players with ratings.

Team identities from all files are folded into one registry
(:mod:`brazilian_soccer.normalize`) so "Palmeiras-SP", "Palmeiras - SP" and
"Palmeiras" are the same entity.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .competitions import COMPETITIONS
from .models import Match, MatchStats, Player, TeamRef
from .normalize import TeamRegistry, parse_date, parse_time, to_int

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

# Raw spellings that only occur in the Libertadores file.
LIBERTADORES_NAME_FIXES = {
    "Athletico": "Athletico-PR",   # bare spelling of Atlético Paranaense
}

# Libertadores stage labels prettified.
LIB_STAGES = {
    "group stage": "Group Stage",
    "round of 16": "Round of 16",
    "quarterfinals": "Quarterfinals",
    "semifinals": "Semifinals",
    "final": "Final",
}

BRF_TOURNAMENT_MAP = {
    "Serie A": "brasileirao",
    "Serie B": "serie_b",
    "Serie C": "serie_c",
    "Copa do Brasil": "copa_do_brasil",
}

# Known non-football junk rows in the extended-stats file (there is at least
# one: a "Serie B" fixture between two clubs that do not exist).
BRF_JUNK_ROWS = {
    ("Serie B", "2022-09-18", "GE Bage", "Monsoon FC"),
}

# Small curated notes for results the datasets cannot express, surfaced by
# the service layer with a clear "outside the dataset" marker.
CURATED_NOTES: dict[tuple[str, int], str] = {
    ("libertadores", 2021): (
        "The 2021 final is missing from the dataset (semifinals only: "
        "Palmeiras x Atlético-MG and Flamengo x Barcelona-EQU). "
        "Outside the dataset: Palmeiras beat Flamengo 2-1 aet in the final."
    ),
    ("libertadores", 2022): (
        "The 2022 final (Flamengo x Athletico-PR) appears in the dataset "
        "without a score. Outside the dataset: Flamengo won 1-0 aet."
    ),
}

FIFA_UNLICENSED_NOTE = (
    "The FIFA dataset (FIFA 19 era) does not include every Brazilian club "
    "because of licensing: Flamengo, Palmeiras, Corinthians, São Paulo and "
    "Vasco are absent. Covered Brazilian clubs include Santos, Grêmio, "
    "Atlético Mineiro, Cruzeiro, Fluminense, Internacional, Botafogo, Bahia, "
    "Athletico Paranaense, Sport, Ceará, Chapecoense, América (MG), Paraná "
    "and Vitória."
)


def _read(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class SoccerData:
    """The in-memory knowledge graph: matches, players and team registry."""

    def __init__(self, data_dir: Path | str = DATA_DIR) -> None:
        self.data_dir = Path(data_dir)
        self.registry = TeamRegistry()
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self.notes = CURATED_NOTES
        self._league_fixtures: dict[tuple[str, int, str, str], Match] = {}
        self._cup_fixtures: dict[tuple[int, str, str], list[Match]] = defaultdict(list)
        self._team_matches: dict[str, list[Match]] = defaultdict(list)
        self._club_key_cache: dict[str, str] = {}

        self._register_all_teams()
        self._build_matches()
        self._stamp_copa_finals()
        self.registry.finalize_displays()
        self._refresh_display_names()
        self._load_players()
        for match in self.matches:
            self._team_matches[match.home.key].append(match)
            self._team_matches[match.away.key].append(match)

    def _refresh_display_names(self) -> None:
        """Point every match's TeamRefs at the finalized display names."""
        for match in self.matches:
            match.home = TeamRef(match.home.key, self.registry.display(match.home.key))
            match.away = TeamRef(match.away.key, self.registry.display(match.away.key))

    def _stamp_copa_finals(self) -> None:
        """Label Copa do Brasil final matches with stage='Final'.

        The cup file numbers rounds (1..8) instead of naming them, and the
        number of rounds changed across editions, so the final is the
        highest round with played matches - except for 2021-2023, where the
        file stops at the round of 16 and the final is inferred from the
        last recorded matches of the season (a two-legged tie between the
        same two clubs).
        """
        comp_matches = [
            m for m in self.matches if m.competition == "copa_do_brasil" and m.season
        ]
        for season in sorted({m.season for m in comp_matches}):
            season_matches = [m for m in comp_matches if m.season == season]
            round_numbers = []
            for match in season_matches:
                if match.round_label and match.round_label.startswith("Round"):
                    tail = match.round_label.split()[-1]
                    if tail.isdigit() and match.played:
                        round_numbers.append(int(tail))
            if round_numbers and max(round_numbers) >= 5:
                final_round = f"Round {max(round_numbers)}"
                for match in season_matches:
                    if match.round_label == final_round:
                        match.stage = "Final"
                continue
            played = sorted(
                (m for m in season_matches if m.played and m.date),
                key=lambda m: m.date,
            )
            if len(played) >= 2:
                tail = played[-2:]
                teams = {
                    tail[0].home.key, tail[0].away.key,
                    tail[1].home.key, tail[1].away.key,
                }
                if len(teams) == 2:
                    for match in tail:
                        match.stage = "Final"

    # ------------------------------------------------------------------
    # Phase 1 - team registration (suffixed sources first)
    # ------------------------------------------------------------------

    def _file(self, name: str) -> Path:
        return self.data_dir / name

    def _register_all_teams(self) -> None:
        reg = self.registry

        for row in _read(self._file("Brasileirao_Matches.csv")):
            reg.register(row["home_team"])
            reg.register(row["away_team"])

        for row in _read(self._file("novo_campeonato_brasileiro.csv")):
            reg.register(row["Equipe_mandante"], state_hint=row["Mandante_UF"])
            reg.register(row["Equipe_visitante"], state_hint=row["Visitante_UF"])

        for row in _read(self._file("Brazilian_Cup_Matches.csv")):
            reg.register(row["home_team"])
            reg.register(row["away_team"])

        for row in _read(self._file("Libertadores_Matches.csv")):
            home = LIBERTADORES_NAME_FIXES.get(row["home_team"], row["home_team"])
            away = LIBERTADORES_NAME_FIXES.get(row["away_team"], row["away_team"])
            reg.register(home)
            reg.register(away)

        for row in _read(self._file("BR-Football-Dataset.csv")):
            # Suffixed spellings ("Botafogo RJ") count toward dominance;
            # stateless ones resolve through alias/unique/dominance without
            # inflating appearance counts.
            reg.register(row["home"], count_appearance=False)
            reg.register(row["away"], count_appearance=False)

    # ------------------------------------------------------------------
    # Phase 2 - match construction and cross-file merging
    # ------------------------------------------------------------------

    def _ref(self, raw: str, state_hint: str | None = None) -> TeamRef:
        key = self.registry.register(
            raw, state_hint=state_hint, count_appearance=False
        )
        return TeamRef(key=key, display=self.registry.display(key))

    def _add(self, match: Match) -> Match:
        self.matches.append(match)
        if match.competition in ("brasileirao", "serie_b", "serie_c") and match.season:
            self._league_fixtures[self._league_key(match)] = match
        elif match.competition == "copa_do_brasil" and match.season:
            self._cup_fixtures[
                (match.season, match.home.key, match.away.key)
            ].append(match)
        return match

    @staticmethod
    def _league_key(match: Match):
        """Fixture identity within a league season.

        Serie A is a pure double round-robin: one fixture per ordered pair,
        so the pair alone identifies it (sources may disagree on dates).
        Serie B/C data comes from a single source that also contains group
        stages, where the same ordered pair legitimately meets twice in one
        season, so the date is part of the key there.
        """
        if match.competition == "brasileirao":
            return (match.competition, match.season, match.home.key, match.away.key)
        return (
            match.competition,
            match.season,
            match.home.key,
            match.away.key,
            match.date,
        )

    @staticmethod
    def _brf_season(comp_id: str, when) -> int | None:
        """Infer the season of a BR-Football row from its date.

        Brazilian leagues run April-December, so January/February league
        matches belong to the previous season (the COVID-delayed 2020
        Serie A/B/C ran into Jan/Feb 2021). The 2020 Copa do Brasil
        similarly finished in March/April 2021.
        """
        if when is None:
            return None
        year = when.year
        if comp_id in ("brasileirao", "serie_b", "serie_c"):
            return year - 1 if when.month <= 2 else year
        if year == 2021 and when.month <= 4:
            return 2020
        return year

    def _build_matches(self) -> None:
        self._build_brasileirao()
        self._build_historical_brasileirao()
        # Seasons the primary files cover completely: extended-file rows for
        # these can only enrich existing fixtures, never add new ones (the
        # one-off extra rows in that file are source noise).
        self._primary_league_seasons = {
            key[1] for key in self._league_fixtures if key[0] == "brasileirao"
        }
        self._build_copa_do_brasil()
        self._build_libertadores()
        self._build_extended_stats()

    def _build_brasileirao(self) -> None:
        comp = COMPETITIONS["brasileirao"]
        for row in _read(self._file("Brasileirao_Matches.csv")):
            when = parse_date(row["datetime"])
            self._add(
                Match(
                    competition="brasileirao",
                    competition_display=comp,
                    season=to_int(row["season"]),
                    date=when,
                    time=parse_time(row["datetime"]),
                    home=self._ref(row["home_team"]),
                    away=self._ref(row["away_team"]),
                    home_goals=to_int(row["home_goal"]),
                    away_goals=to_int(row["away_goal"]),
                    round_label=f"Round {row['round']}" if row["round"] else None,
                    source="Brasileirao_Matches.csv",
                )
            )

    def _build_historical_brasileirao(self) -> None:
        comp = COMPETITIONS["brasileirao"]
        for row in _read(self._file("novo_campeonato_brasileiro.csv")):
            season = to_int(row["Ano"])
            home = self._ref(row["Equipe_mandante"], row["Mandante_UF"])
            away = self._ref(row["Equipe_visitante"], row["Visitante_UF"])
            if season and ("brasileirao", season, home.key, away.key) in self._league_fixtures:
                continue  # already covered by the 2012+ file (identical data)
            self._add(
                Match(
                    competition="brasileirao",
                    competition_display=comp,
                    season=season,
                    date=parse_date(row["Data"]),
                    time=None,
                    home=home,
                    away=away,
                    home_goals=to_int(row["Gols_mandante"]),
                    away_goals=to_int(row["Gols_visitante"]),
                    round_label=f"Round {row['Rodada']}" if row["Rodada"] else None,
                    venue=row["Arena"] or None,
                    source="novo_campeonato_brasileiro.csv",
                )
            )

    def _build_copa_do_brasil(self) -> None:
        comp = COMPETITIONS["copa_do_brasil"]
        for row in _read(self._file("Brazilian_Cup_Matches.csv")):
            when = parse_date(row["datetime"])
            round_label = f"Round {row['round']}" if row["round"] else None
            self._add(
                Match(
                    competition="copa_do_brasil",
                    competition_display=comp,
                    season=to_int(row["season"]),
                    date=when,
                    time=parse_time(row["datetime"]),
                    home=self._ref(row["home_team"]),
                    away=self._ref(row["away_team"]),
                    home_goals=to_int(row["home_goal"]),
                    away_goals=to_int(row["away_goal"]),
                    round_label=round_label,
                    source="Brazilian_Cup_Matches.csv",
                )
            )

    def _build_libertadores(self) -> None:
        comp = COMPETITIONS["libertadores"]
        for row in _read(self._file("Libertadores_Matches.csv")):
            season = to_int(row["season"])
            stage = LIB_STAGES.get(
                (row["stage"] or "").strip().lower(), row["stage"] or None
            )
            # The 2022 final row ships with season/date/scores as NA; both
            # semifinal participants point to the 2022 campaign.
            unplayed_final_note = (
                season is None and stage == "Final"
            )
            if unplayed_final_note:
                season = 2022
            home_raw = LIBERTADORES_NAME_FIXES.get(row["home_team"], row["home_team"])
            away_raw = LIBERTADORES_NAME_FIXES.get(row["away_team"], row["away_team"])
            self._add(
                Match(
                    competition="libertadores",
                    competition_display=comp,
                    season=season,
                    date=parse_date(row["datetime"]),
                    time=parse_time(row["datetime"]),
                    home=self._ref(home_raw),
                    away=self._ref(away_raw),
                    home_goals=to_int(row["home_goal"]),
                    away_goals=to_int(row["away_goal"]),
                    stage=stage,
                    source="Libertadores_Matches.csv",
                )
            )

    def _build_extended_stats(self) -> None:
        for row in _read(self._file("BR-Football-Dataset.csv")):
            comp_id = BRF_TOURNAMENT_MAP.get(row["tournament"])
            if comp_id is None:
                continue
            if (row["tournament"], row["date"], row["home"], row["away"]) in BRF_JUNK_ROWS:
                continue
            when = parse_date(row["date"])
            season = self._brf_season(comp_id, when)
            if season is None:
                continue
            kick_off = parse_time(row.get("time"))
            home = self._ref(row["home"])
            away = self._ref(row["away"])
            stats = MatchStats(
                home_corners=to_int(row.get("home_corner")),
                away_corners=to_int(row.get("away_corner")),
                home_shots=to_int(row.get("home_shots")),
                away_shots=to_int(row.get("away_shots")),
                home_attacks=to_int(row.get("home_attack")),
                away_attacks=to_int(row.get("away_attack")),
            )
            hg, ag = to_int(row["home_goal"]), to_int(row["away_goal"])
            self._merge_extended(comp_id, season, when, home, away, hg, ag, stats, kick_off)

    def _merge_extended(
        self, comp_id, season, when, home, away, hg, ag, stats, kick_off=None
    ) -> None:
        if comp_id in ("brasileirao", "serie_b", "serie_c"):
            if comp_id == "brasileirao":
                existing = self._league_fixtures.get(
                    (comp_id, season, home.key, away.key)
                )
                if existing is not None:
                    self._enrich(existing, when, hg, ag, stats)
                    return
                if season in self._primary_league_seasons:
                    return  # primary file already covers this season fully
            else:
                existing = self._league_fixtures.get(
                    (comp_id, season, home.key, away.key, when)
                )
                if existing is not None:
                    self._enrich(existing, when, hg, ag, stats)
                    return
            self._add(
                Match(
                    competition=comp_id,
                    competition_display=COMPETITIONS[comp_id],
                    season=season,
                    date=when,
                    time=kick_off,
                    home=home,
                    away=away,
                    home_goals=hg,
                    away_goals=ag,
                    stats=stats,
                    source="BR-Football-Dataset.csv",
                )
            )
            return

        # Copa do Brasil: the primary file may hold both legs under separate
        # home/away orders; enrich a played match with matching score, else
        # fill an unplayed one, else create a new fixture.
        candidates = self._cup_fixtures.get((season, home.key, away.key), [])
        played = [m for m in candidates if m.played]
        if played:
            self._enrich(self._pick_stats_target(played, hg, ag, when), when, hg, ag, stats)
            return
        unplayed = [m for m in candidates if not m.played]
        if unplayed:
            target = unplayed[0]
            target.home_goals, target.away_goals = hg, ag
            if target.date is None:
                target.date = when
            self._enrich(target, when, hg, ag, stats)
            return
        self._add(
            Match(
                competition=comp_id,
                competition_display=COMPETITIONS[comp_id],
                season=season,
                date=when,
                time=kick_off,
                home=home,
                away=away,
                home_goals=hg,
                away_goals=ag,
                stats=stats,
                source="BR-Football-Dataset.csv",
            )
        )

    @staticmethod
    def _pick_stats_target(played, hg, ag, when) -> Match:
        same_score = [m for m in played if (m.home_goals, m.away_goals) == (hg, ag)]
        if same_score:
            return same_score[0]
        return min(played, key=lambda m: abs((m.date or when).toordinal() - when.toordinal()))

    @staticmethod
    def _enrich(match: Match, when, hg, ag, stats: MatchStats) -> None:
        if not match.played and hg is not None and ag is not None:
            match.home_goals, match.away_goals = hg, ag
            if match.date is None:
                match.date = when
        if match.stats is None:
            match.stats = stats

    # ------------------------------------------------------------------
    # Phase 3 - players
    # ------------------------------------------------------------------

    def _load_players(self) -> None:
        for row in _read(self._file("fifa_data.csv")):
            club = (row.get("Club") or "").strip() or None
            self.players.append(
                Player(
                    player_id=to_int(row.get("ID")) or 0,
                    name=row.get("Name") or "",
                    age=to_int(row.get("Age")),
                    nationality=row.get("Nationality") or "",
                    overall=to_int(row.get("Overall")) or 0,
                    potential=to_int(row.get("Potential")) or 0,
                    club=club,
                    position=(row.get("Position") or "").strip() or None,
                    jersey=to_int(row.get("Jersey Number")),
                    preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
                    value=(row.get("Value") or "").strip() or None,
                    wage=(row.get("Wage") or "").strip() or None,
                    height=(row.get("Height") or "").strip() or None,
                    weight=(row.get("Weight") or "").strip() or None,
                )
            )

    # ------------------------------------------------------------------
    # Lookup helpers used by the service layer
    # ------------------------------------------------------------------

    def club_team_key(self, club_name: str | None) -> str | None:
        """Map a FIFA club name to a canonical team key, if it is a
        Brazilian club present in the match data."""
        if not club_name:
            return None
        cached = self._club_key_cache.get(club_name)
        if cached is not None:
            return cached or None
        resolution = self.registry.resolve(club_name)
        key = None
        if resolution.matched and resolution.key:
            team = self.registry.teams.get(resolution.key)
            if team and team.state and not team.country:
                key = resolution.key
        self._club_key_cache[club_name] = key or ""
        return key

    def matches_for_team(self, team_key: str) -> list[Match]:
        return self._team_matches.get(team_key, [])

    def seasons_for(self, competition: str) -> list[int]:
        seasons = {
            m.season for m in self.matches if m.competition == competition and m.season
        }
        return sorted(seasons)

    def summary(self) -> str:
        lines = [f"Teams: {len(self.registry.teams)}", f"Players: {len(self.players)}"]
        for comp_id, display in COMPETITIONS.items():
            matches = [m for m in self.matches if m.competition == comp_id]
            seasons = self.seasons_for(comp_id)
            span = f"{seasons[0]}-{seasons[-1]}" if seasons else "-"
            played = sum(1 for m in matches if m.played)
            lines.append(
                f"{display}: {len(matches)} matches ({played} played), seasons {span}"
            )
        return "\n".join(lines)
