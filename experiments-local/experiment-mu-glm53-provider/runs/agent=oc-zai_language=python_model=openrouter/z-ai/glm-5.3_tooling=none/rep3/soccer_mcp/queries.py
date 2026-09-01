"""
soccer_mcp.queries -- the analytical query layer.

CONTEXT
-------
The MCP tools (``soccer_mcp.tools``) answer the natural-language question
categories required by the Brazilian Soccer MCP specification:

* Match queries    -- find matches by team, opponent, date range, competition,
                      season, stage ("Flamengo vs Fluminense", "Palmeiras
                      matches in 2023", "Copa do Brasil finals");
* Team queries     -- records, home/away splits, head-to-head, comparisons,
                      competitions a team appeared in;
* Player queries   -- name/nationality/club/position/rating filters over the
                      FIFA database, including cross-file club matching;
* Competition queries -- computed standings, champions, finals and knockout
                      brackets;
* Statistics       -- average goals, home/away win rates, biggest wins,
                      derby fixtures.

Every function here is a pure function of a loaded ``SoccerData`` and returns
plain Python structures, so the whole layer is testable without MCP.  The
``tools`` module adds name resolution and text formatting on top.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .data_loader import SoccerData
from .model import (
    FinalResult,
    KnockoutTie,
    Match,
    Player,
    SKILL_COLUMNS,
    StandingRow,
    TeamEntity,
    TeamRecord,
)
from .normalize import (
    COMPETITIONS,
    POSITION_GROUPS,
    parse_date_any,
    text_key,
)


class QueryError(Exception):
    """Raised when a query cannot be answered (unknown team, bad season...)."""

    def __init__(self, message: str, alternatives: list[TeamEntity] | None = None):
        super().__init__(message)
        self.alternatives = alternatives or []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def resolve_team(ds: SoccerData, name: str) -> TeamEntity:
    """Resolve a team name or raise ``QueryError`` with candidates."""
    resolution = ds.registry.resolve(name)
    if resolution.ok:
        return resolution.team
    raise QueryError(resolution.error or f"Could not resolve team '{name}'.", resolution.alternatives)


def resolve_competition(ds: SoccerData, competition: str | None) -> str:
    """Map free text to a competition id or raise ``QueryError``."""
    if competition is None:
        raise QueryError("A competition is required (e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores').")
    from .normalize import normalize_competition

    comp_id = normalize_competition(competition)
    if comp_id is None or comp_id not in COMPETITIONS:
        valid = ", ".join(c.display for c in COMPETITIONS.values())
        raise QueryError(f"Unknown competition '{competition}'. Available: {valid}.")
    return comp_id


def _team_filter_ids(ds: SoccerData, team: str | None) -> tuple[str | None, list[TeamEntity]]:
    """Resolve an optional team filter; returns (team_id, alternatives)."""
    if team is None:
        return None, []
    entity = resolve_team(ds, team)
    return entity.team_id, []


def _player_sort_key(player: Player):
    return (-player.overall, -(player.potential or 0), text_key(player.name))


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------


@dataclass
class MatchSearchResult:
    """Result bundle for match searches."""

    matches: list[Match]
    total: int
    team: TeamEntity | None = None
    opponent: TeamEntity | None = None
    competition: str | None = None
    season: str | None = None


def search_matches(
    ds: SoccerData,
    *,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: str | None = None,
    stage: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    source: str | None = None,
    limit: int | None = None,
) -> MatchSearchResult:
    """Search matches by team, opponent, competition, season, stage, dates."""
    comp_id = None
    if competition:
        comp_id = resolve_competition(ds, competition)
    team_entity = resolve_team(ds, team) if team else None
    opponent_entity = resolve_team(ds, opponent) if opponent else None
    parsed_from = parse_date_any(date_from) if date_from else None
    parsed_to = parse_date_any(date_to) if date_to else None
    if date_from and parsed_from is None:
        raise QueryError(f"Could not parse date_from '{date_from}'. Use YYYY-MM-DD or DD/MM/YYYY.")
    if date_to and parsed_to is None:
        raise QueryError(f"Could not parse date_to '{date_to}'. Use YYYY-MM-DD or DD/MM/YYYY.")

    matches = ds.iter_matches(
        competition=comp_id,
        season=str(season) if season else None,
        team=team_entity.team_id if team_entity else None,
        opponent=opponent_entity.team_id if opponent_entity else None,
        date_from=parsed_from,
        date_to=parsed_to,
        stage=stage,
        source=source,
    )
    total = len(matches)
    shown = matches if limit is None else matches[:limit]
    return MatchSearchResult(
        matches=shown,
        total=total,
        team=team_entity,
        opponent=opponent_entity,
        competition=comp_id,
        season=str(season) if season else None,
    )


def last_match(ds: SoccerData, team: str, opponent: str | None = None) -> Match | None:
    """Most recent match of a team (optionally against a given opponent)."""
    team_entity = resolve_team(ds, team)
    opponent_id = resolve_team(ds, opponent).team_id if opponent else None
    matches = ds.iter_matches(
        team=team_entity.team_id, opponent=opponent_id
    )
    if not matches:
        return None
    return max(matches, key=lambda m: (m.match_date is not None, m.match_date))


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------


@dataclass
class TeamStatsResult:
    """Aggregated record for one team across (filtered) matches."""

    team: TeamEntity
    overall: TeamRecord
    home: TeamRecord
    away: TeamRecord
    per_competition: list[tuple[str, TeamRecord]] = field(default_factory=list)
    competition: str | None = None
    season: str | None = None
    match_count: int = 0
    first_match: Match | None = None
    last: Match | None = None


def team_stats(
    ds: SoccerData,
    team: str,
    *,
    competition: str | None = None,
    season: str | None = None,
) -> TeamStatsResult:
    """Win/draw/loss and goal record for a team, with home/away split."""
    team_entity = resolve_team(ds, team)
    comp_id = None
    if competition:
        comp_id = resolve_competition(ds, competition)
    matches = ds.iter_matches(
        team=team_entity.team_id,
        competition=comp_id,
        season=str(season) if season else None,
    )
    overall = TeamRecord(team_id=team_entity.team_id)
    home = TeamRecord(team_id=team_entity.team_id)
    away = TeamRecord(team_id=team_entity.team_id)
    per_comp: dict[str, TeamRecord] = {}
    for match in matches:
        overall.add_match(match, team_entity.team_id)
        if match.home_team == team_entity.team_id:
            home.add_match(match, team_entity.team_id)
        else:
            away.add_match(match, team_entity.team_id)
        record = per_comp.setdefault(match.competition, TeamRecord(team_id=team_entity.team_id))
        record.add_match(match, team_entity.team_id)
    ordered = sorted(
        per_comp.items(), key=lambda kv: -kv[1].matches
    )
    return TeamStatsResult(
        team=team_entity,
        overall=overall,
        home=home,
        away=away,
        per_competition=ordered,
        competition=comp_id,
        season=str(season) if season else None,
        match_count=len(matches),
        first_match=matches[0] if matches else None,
        last=matches[-1] if matches else None,
    )


@dataclass
class HeadToHeadResult:
    """Head-to-head record between two teams."""

    team_a: TeamEntity
    team_b: TeamEntity
    matches: list[Match]
    wins_a: int = 0
    wins_b: int = 0
    draws: int = 0
    goals_a: int = 0
    goals_b: int = 0
    competition: str | None = None
    season: str | None = None


def head_to_head(
    ds: SoccerData,
    team_a: str,
    team_b: str,
    *,
    competition: str | None = None,
    season: str | None = None,
) -> HeadToHeadResult:
    """All matches between two teams plus the aggregate record."""
    entity_a = resolve_team(ds, team_a)
    entity_b = resolve_team(ds, team_b)
    if entity_a.team_id == entity_b.team_id:
        raise QueryError("Cannot compare a team with itself.")
    comp_id = None
    if competition:
        comp_id = resolve_competition(ds, competition)
    matches = ds.iter_matches(
        team=entity_a.team_id,
        opponent=entity_b.team_id,
        competition=comp_id,
        season=str(season) if season else None,
    )
    result = HeadToHeadResult(
        team_a=entity_a,
        team_b=entity_b,
        matches=matches,
        competition=comp_id,
        season=str(season) if season else None,
    )
    for match in matches:
        a_is_home = match.home_team == entity_a.team_id
        goals_a = match.home_goals if a_is_home else match.away_goals
        goals_b = match.away_goals if a_is_home else match.home_goals
        result.goals_a += goals_a
        result.goals_b += goals_b
        if goals_a > goals_b:
            result.wins_a += 1
        elif goals_a < goals_b:
            result.wins_b += 1
        else:
            result.draws += 1
    return result


def compare_teams(
    ds: SoccerData,
    team_a: str,
    team_b: str,
    *,
    competition: str | None = None,
    season: str | None = None,
) -> tuple[TeamStatsResult, TeamStatsResult, HeadToHeadResult]:
    """Side-by-side team records plus their head-to-head."""
    stats_a = team_stats(ds, team_a, competition=competition, season=season)
    stats_b = team_stats(ds, team_b, competition=competition, season=season)
    h2h = head_to_head(ds, team_a, team_b, competition=competition, season=season)
    return stats_a, stats_b, h2h


def team_competitions(ds: SoccerData, team: str) -> TeamEntity:
    """Entity view of a team (competitions, seasons, variants) for display."""
    return resolve_team(ds, team)


def best_records(
    ds: SoccerData,
    *,
    venue: str = "overall",
    competition: str | None = None,
    season: str | None = None,
    min_matches: int = 10,
    limit: int = 10,
) -> list[tuple[TeamRecord, TeamEntity]]:
    """Rank teams by win rate (overall/home/away) within filters."""
    if venue not in {"overall", "home", "away"}:
        raise QueryError("venue must be 'overall', 'home' or 'away'.")
    comp_id = None
    if competition:
        comp_id = resolve_competition(ds, competition)
    matches = ds.iter_matches(
        competition=comp_id,
        season=str(season) if season else None,
    )
    records: dict[str, tuple[TeamRecord, TeamRecord, TeamRecord]] = {}
    for match in matches:
        for team_id in (match.home_team, match.away_team):
            bundle = records.setdefault(
                team_id,
                (
                    TeamRecord(team_id=team_id),
                    TeamRecord(team_id=team_id),
                    TeamRecord(team_id=team_id),
                ),
            )
            overall, home, away = bundle
            overall.add_match(match, team_id)
            if match.home_team == team_id:
                home.add_match(match, team_id)
            else:
                away.add_match(match, team_id)
    ranked: list[tuple[TeamRecord, TeamEntity]] = []
    for team_id, bundle in records.items():
        record = {"overall": bundle[0], "home": bundle[1], "away": bundle[2]}[venue]
        if record.matches >= min_matches:
            entity = ds.registry.entities.get(team_id)
            if entity:
                ranked.append((record, entity))
    ranked.sort(key=lambda item: (-item[0].win_rate, -item[0].matches))
    return ranked[:limit]


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------


def _position_filter(position: str | None) -> set[str] | None:
    """Accept a FIFA position code ('ST') or a group ('FWD', 'GK'...)."""
    if not position:
        return None
    key = position.strip().upper()
    return {key} | set(POSITION_GROUPS.get(key, ()))


def _match_club(player: Player, club_keys: set[str]) -> bool:
    return text_key(player.club) in club_keys


def search_players(
    ds: SoccerData,
    *,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_age: int | None = None,
    limit: int = 20,
) -> tuple[list[Player], TeamEntity | None]:
    """Filter the FIFA player database.

    Returns (players, club_entity) where club_entity is the resolved team for
    the club filter (None when no club filter was given).
    """
    if not any([name, nationality, club, position, min_overall is not None, max_age is not None]):
        raise QueryError("Provide at least one filter (name, nationality, club, position, min_overall, max_age).")

    club_entity: TeamEntity | None = None
    club_keys: set[str] | None = None
    if club:
        club_entity = resolve_team(ds, club)
        club_keys = {text_key(raw) for raw in club_entity.fifa_club_names}

    name_key = text_key(name) if name else None
    nationality_key = text_key(nationality) if nationality else None
    wanted_positions = _position_filter(position)

    out: list[Player] = []
    for player in ds.players:
        if name_key and name_key not in text_key(player.name):
            continue
        if nationality_key and nationality_key not in text_key(player.nationality):
            continue
        if club_keys is not None and not _match_club(player, club_keys):
            continue
        if wanted_positions is not None and player.position not in wanted_positions:
            continue
        if min_overall is not None and player.overall < min_overall:
            continue
        if max_age is not None and (player.age is None or player.age > max_age):
            continue
        out.append(player)
    out.sort(key=_player_sort_key)
    return out[:limit], club_entity


def top_players(
    ds: SoccerData,
    *,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    attribute: str = "overall",
    limit: int = 10,
) -> tuple[list[Player], TeamEntity | None, str]:
    """Top-rated players by overall rating or a specific skill attribute."""
    attr = attribute.strip()
    attr_key = attr.casefold()
    attr_column = None
    if attr_key not in {"overall", "potential"}:
        for column in SKILL_COLUMNS:
            if column.casefold() == attr_key:
                attr_column = column
                break
        if attr_column is None:
            raise QueryError(
                f"Unknown attribute '{attribute}'. Use 'overall', 'potential' or a FIFA skill "
                f"such as 'Finishing', 'Dribbling', 'SprintSpeed'."
            )

    club_entity: TeamEntity | None = None
    club_keys: set[str] | None = None
    if club:
        club_entity = resolve_team(ds, club)
        club_keys = {text_key(raw) for raw in club_entity.fifa_club_names}
    nationality_key = text_key(nationality) if nationality else None
    wanted_positions = _position_filter(position)

    def rating(player: Player) -> int:
        if attr_column:
            return player.skills.get(attr_column) or 0
        if attr_key == "potential":
            return player.potential or 0
        return player.overall

    out: list[Player] = []
    for player in ds.players:
        if nationality_key and nationality_key not in text_key(player.nationality):
            continue
        if club_keys is not None and not _match_club(player, club_keys):
            continue
        if wanted_positions is not None and player.position not in wanted_positions:
            continue
        out.append(player)
    out.sort(key=lambda p: (-rating(p), text_key(p.name)))
    return out[:limit], club_entity, attr


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------


@dataclass
class StandingsResult:
    """A computed league table."""

    competition: str
    season: str
    rows: list[StandingRow]
    source: str | None
    notes: list[str] = field(default_factory=list)

    @property
    def champion(self) -> StandingRow | None:
        return self.rows[0] if self.rows else None

    @property
    def relegated(self) -> list[StandingRow]:
        return self.rows[-4:] if len(self.rows) >= 8 else []


def standings(ds: SoccerData, competition: str, season: str) -> StandingsResult:
    """Compute a league table from match results (3 points per win)."""
    comp_id = resolve_competition(ds, competition)
    comp = COMPETITIONS[comp_id]
    season = str(season)
    if comp.type != "league":
        raise QueryError(
            f"{comp.display} is a knockout competition -- use the 'finals' or "
            "'knockout' tools instead of standings."
        )
    source = ds.source_priority_for(comp_id, season)
    if source is None:
        available = sorted(
            s for c, s in ds._by_comp_season if c == comp_id
        )
        raise QueryError(
            f"No data for {comp.display} season {season}. Available seasons: "
            f"{', '.join(available)}."
        )
    matches = [
        m for m in ds._by_comp_season.get((comp_id, season), []) if m.source == source
    ]
    records: dict[str, TeamRecord] = {}
    for match in matches:
        for team_id in (match.home_team, match.away_team):
            records.setdefault(team_id, TeamRecord(team_id=team_id)).add_match(match, team_id)

    ordered = sorted(
        records.items(),
        key=lambda kv: (
            -kv[1].points, -kv[1].wins, -kv[1].goal_diff, -kv[1].goals_for, kv[0]
        ),
    )
    rows = [
        StandingRow(
            position=i + 1,
            team_id=team_id,
            matches=record.matches,
            wins=record.wins,
            draws=record.draws,
            losses=record.losses,
            goals_for=record.goals_for,
            goals_against=record.goals_against,
            points=record.points,
        )
        for i, (team_id, record) in enumerate(ordered)
    ]
    notes = [f"computed from {len(matches)} matches in the dataset"]
    return StandingsResult(
        competition=comp_id, season=season, rows=rows, source=source, notes=notes
    )


def _ties_from_matches(stage_label: str, matches: list[Match]) -> list[KnockoutTie]:
    """Group a flat match list into pairings (two-legged or single)."""
    by_pair: dict[frozenset[str], list[Match]] = {}
    for match in matches:
        by_pair.setdefault(frozenset((match.home_team, match.away_team)), []).append(match)
    ties = []
    for pair, legs in by_pair.items():
        legs.sort(key=lambda m: (m.match_date is not None, m.match_date))
        if len(pair) != 2:
            continue
        team_a, team_b = sorted(pair)
        ties.append(KnockoutTie(stage=stage_label, team_a=team_a, team_b=team_b, legs=legs))
    ties.sort(key=lambda t: (t.stage, t.team_a))
    return ties


def finals(ds: SoccerData, competition: str, season: str | None = None) -> list[FinalResult]:
    """Finals of a cup competition ( Libertadores 'final' stage / Copa do
    Brasil last round or last-dated pairing ), aggregated over the legs."""
    comp_id = resolve_competition(ds, competition)
    comp = COMPETITIONS[comp_id]
    if comp.type != "cup":
        raise QueryError(f"{comp.display} is a league -- the champion is the top of the standings.")
    seasons = [str(season)] if season else sorted(
        {s for c, s in ds._by_comp_season if c == comp_id}
    )
    results: list[FinalResult] = []
    for season_key in seasons:
        source = ds.source_priority_for(comp_id, season_key)
        if source is None:
            continue
        matches = [
            m for m in ds._by_comp_season.get((comp_id, season_key), []) if m.source == source
        ]
        note = None
        if comp_id == "libertadores":
            final_matches = [m for m in matches if m.stage == "final"]
        else:
            final_matches = _cup_final_matches(matches)
            if not final_matches:
                note = "no final found in the dataset for this season"
        if not final_matches:
            if season:
                results.append(FinalResult(competition=comp_id, season=season_key, note=note))
            continue
        ties = _ties_from_matches("Final", final_matches)
        results.append(FinalResult(competition=comp_id, season=season_key, ties=ties))
    return results


def _cup_final_matches(matches: list[Match]) -> list[Match]:
    """Heuristic final detection for Copa do Brasil seasons.

    When round labels exist (dedicated cup file), the final is the highest
    round.  Without rounds (BR-Football), the final is the last-dated pairing:
    the last two matches if they share the same teams (two legs), else just
    the last match.
    """
    dated = [m for m in matches if m.match_date is not None]
    rounded = [m for m in matches if m.round_label and m.round_label.startswith("Round ")]
    if rounded:
        try:
            top_round = max(int(m.round_label.split()[-1]) for m in rounded)
            return [m for m in rounded if m.round_label == f"Round {top_round}"]
        except ValueError:
            pass
    if not dated:
        return []
    dated.sort(key=lambda m: m.match_date)
    last = dated[-1]
    if len(dated) >= 2:
        previous = dated[-2]
        if {previous.home_team, previous.away_team} == {last.home_team, last.away_team}:
            return [previous, last]
    return [last]


def knockout(ds: SoccerData, competition: str, season: str) -> dict[str, list[KnockoutTie]]:
    """Knockout bracket: stage -> ties, for cup competitions."""
    comp_id = resolve_competition(ds, competition)
    comp = COMPETITIONS[comp_id]
    if comp.type != "cup":
        raise QueryError(f"{comp.display} is a league -- use 'standings' instead.")
    season = str(season)
    source = ds.source_priority_for(comp_id, season)
    if source is None:
        available = sorted(s for c, s in ds._by_comp_season if c == comp_id)
        raise QueryError(
            f"No data for {comp.display} season {season}. Available seasons: {', '.join(available)}."
        )
    matches = [
        m for m in ds._by_comp_season.get((comp_id, season), []) if m.source == source
    ]
    stages: dict[str, list[Match]] = {}
    if comp_id == "libertadores":
        for match in matches:
            if match.stage and match.stage != "group stage":
                stages.setdefault(match.round_label or match.stage, []).append(match)
        order = ["Round Of 16", "Quarterfinals", "Semifinals", "Final"]
    else:
        for match in matches:
            if match.round_label:
                stages.setdefault(match.round_label, []).append(match)
        order = sorted(stages, key=lambda label: _round_order(label))
    bracket = {stage: _ties_from_matches(stage, stages[stage]) for stage in order if stage in stages}
    return bracket


def _round_order(label: str) -> int:
    try:
        return int(label.rsplit(" ", 1)[-1])
    except ValueError:
        return 99


@dataclass
class ChampionResult:
    """Outcome of a 'who won X in season Y' query."""

    competition: str
    display: str
    season: str
    comp_type: str
    winner: TeamEntity | None = None
    standings: StandingsResult | None = None  # leagues
    final: FinalResult | None = None  # cups
    decided_on_penalties: bool = False
    note: str | None = None


def champion(ds: SoccerData, competition: str, season: str) -> ChampionResult:
    """Determine the champion of a competition season.

    Leagues: top of the computed standings.  Cups: winner of the final
    (aggregate over legs); ``decided_on_penalties`` is True when the final was
    level on aggregate and the datasets cannot name a winner (shootouts are
    not recorded).
    """
    comp_id = resolve_competition(ds, competition)
    comp = COMPETITIONS[comp_id]
    season = str(season)
    if comp.type == "league":
        table = standings(ds, comp_id, season)
        winner_id = table.champion.team_id if table.champion else None
        return ChampionResult(
            competition=comp_id,
            display=comp.display,
            season=season,
            comp_type="league",
            winner=ds.registry.entities.get(winner_id) if winner_id else None,
            standings=table,
        )
    final_results = finals(ds, comp_id, season)
    if not final_results or not final_results[0].ties:
        available = sorted(s for c, s in ds._by_comp_season if c == comp_id)
        note = final_results[0].note if final_results else "no final in the dataset"
        return ChampionResult(
            competition=comp_id,
            display=comp.display,
            season=season,
            comp_type="cup",
            note=f"{note}. Finals with a result in the dataset: {', '.join(s for s in available)}",
        )
    final = final_results[0]
    winner_id = final.winner
    return ChampionResult(
        competition=comp_id,
        display=comp.display,
        season=season,
        comp_type="cup",
        winner=ds.registry.entities.get(winner_id) if winner_id else None,
        final=final,
        decided_on_penalties=winner_id is None,
    )


# ---------------------------------------------------------------------------
# Statistical queries
# ---------------------------------------------------------------------------


@dataclass
class Aggregates:
    """Goal/outcome aggregates over a set of matches."""

    matches: int = 0
    total_goals: int = 0
    home_wins: int = 0
    draws: int = 0
    away_wins: int = 0
    home_goals: int = 0
    away_goals: int = 0

    @property
    def avg_goals(self) -> float:
        return self.total_goals / self.matches if self.matches else 0.0

    @property
    def home_win_rate(self) -> float:
        return self.home_wins / self.matches if self.matches else 0.0

    @property
    def draw_rate(self) -> float:
        return self.draws / self.matches if self.matches else 0.0

    @property
    def away_win_rate(self) -> float:
        return self.away_wins / self.matches if self.matches else 0.0


def _aggregate(matches: list[Match]) -> Aggregates:
    agg = Aggregates()
    for match in matches:
        agg.matches += 1
        agg.total_goals += match.total_goals
        agg.home_goals += match.home_goals
        agg.away_goals += match.away_goals
        if match.is_home_win:
            agg.home_wins += 1
        elif match.is_draw:
            agg.draws += 1
        else:
            agg.away_wins += 1
    return agg


def competition_stats(
    ds: SoccerData,
    *,
    competition: str | None = None,
    season: str | None = None,
    team: str | None = None,
) -> tuple[Aggregates, str | None, TeamEntity | None]:
    """Average goals and outcome rates for a (filtered) match set."""
    comp_id = None
    if competition:
        comp_id = resolve_competition(ds, competition)
    team_entity = resolve_team(ds, team) if team else None
    matches = ds.iter_matches(
        competition=comp_id,
        season=str(season) if season else None,
        team=team_entity.team_id if team_entity else None,
    )
    return (
        _aggregate(matches),
        comp_id,
        team_entity,
    )


def biggest_wins(
    ds: SoccerData,
    *,
    competition: str | None = None,
    season: str | None = None,
    team: str | None = None,
    limit: int = 10,
) -> list[Match]:
    """Largest goal-margin victories, then most goals."""
    comp_id = None
    if competition:
        comp_id = resolve_competition(ds, competition)
    team_entity = resolve_team(ds, team) if team else None
    matches = ds.iter_matches(
        competition=comp_id,
        season=str(season) if season else None,
        team=team_entity.team_id if team_entity else None,
    )
    matches.sort(key=lambda m: (-m.goal_margin, -m.total_goals, m.match_date or date.min))
    return matches[:limit]


#: Canonical ids of famous derby pairings.
DERBY_PAIRS: list[tuple[str, str, str]] = [
    ("flamengo rj", "fluminense rj", "Fla-Flu"),
    ("flamengo rj", "vasco da gama rj", "Clássico dos Milhões"),
    ("flamengo rj", "botafogo rj", "Clássico da Rivalidade"),
    ("fluminense rj", "vasco da gama rj", "Clássico dos Gigantes"),
    ("botafogo rj", "fluminense rj", "Clássico Grandão"),
    ("gremio rs", "internacional rs", "Grenal"),
    ("palmeiras sp", "corinthians sp", "Derby Paulista"),
    ("corinthians sp", "sao paulo sp", "Majestoso"),
    ("palmeiras sp", "sao paulo sp", "Choque-Rei"),
    ("santos sp", "sao paulo sp", "San-São"),
    ("santos sp", "corinthians sp", "Clássico Alvinegro Praiano"),
    ("cruzeiro mg", "atletico mg", "Clássico Mineiro"),
    ("bahia ba", "vitoria ba", "Ba-Vi"),
    ("sport pe", "nautico pe", "Clássico dos Clássicos"),
    ("ceara ce", "fortaleza ce", "Clássico-Rei"),
    ("atletico pr", "coritiba pr", "Atletiba"),
    ("avai sc", "criciuma sc", "Clássico Catarinense"),
    ("goias go", "vila nova go", "Clássico Goiano"),
    ("remo pa", "paysandu pa", "Re-Pa"),
    ("csa al", "crb al", "Clássico dos Maiorais"),
]


def derbies(
    ds: SoccerData,
    *,
    season: str | None = None,
    competition: str | None = None,
    limit: int | None = None,
) -> list[tuple[str, Match]]:
    """Matches between famous derby rivals, labelled by derby name."""
    comp_id = None
    if competition:
        comp_id = resolve_competition(ds, competition)
    pairs = {frozenset((a, b)): label for a, b, label in DERBY_PAIRS}
    out: list[tuple[str, Match]] = []
    matches = ds.iter_matches(
        competition=comp_id,
        season=str(season) if season else None,
    )
    for match in matches:
        label = pairs.get(frozenset((match.home_team, match.away_team)))
        if label:
            out.append((label, match))
    out.sort(key=lambda item: (item[1].match_date or date.min, item[0]))
    return out if limit is None else out[:limit]


def list_teams(
    ds: SoccerData,
    competition: str | None = None,
    season: str | None = None,
) -> list[TeamEntity]:
    """Teams present in a competition/season (or all Brazilian teams)."""
    if not competition and not season:
        return sorted(
            (e for e in ds.registry.entities.values() if e.is_brazilian and e.match_count),
            key=lambda e: (-e.match_count, e.team_id),
        )
    comp_id = None
    if competition:
        comp_id = resolve_competition(ds, competition)
    team_ids: set[str] = set()
    for match in ds.iter_matches(competition=comp_id, season=str(season) if season else None):
        team_ids.add(match.home_team)
        team_ids.add(match.away_team)
    entities = [ds.registry.entities[t] for t in team_ids if t in ds.registry.entities]
    entities.sort(key=lambda e: (-e.match_count, e.team_id))
    return entities
