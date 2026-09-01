"""
soccer_mcp.tools -- the MCP tool surface.

CONTEXT
-------
This module defines the 20 tools exposed by the Brazilian Soccer MCP server
(see TASK.md "Required Capabilities").  Each tool is a thin, typed function
that:

1. loads the process-wide cached dataset (``data_loader.get_dataset``);
2. delegates to the pure query layer (``soccer_mcp.queries``);
3. renders the result with ``soccer_mcp.formatting`` into the spec's
   "Example answer format" style;
4. converts ``QueryError`` into a helpful plain-text answer instead of a
   protocol error, so an LLM can recover (e.g. by asking the user to
   disambiguate "Atletico" between MG/PR/GO/BA/AC).

``server.py`` registers every public function whose name does not start with
an underscore on the MCPServer instance.
"""

from __future__ import annotations

from . import formatting, queries
from .data_loader import SOURCE_LABELS, SoccerData, get_dataset
from .normalize import COMPETITIONS, text_key
from .queries import QueryError

#: Source ids/labels accepted by tools with a ``source`` parameter.
_SOURCE_LOOKUP: dict[str, str] = {}
for _id, _label in SOURCE_LABELS.items():
    _SOURCE_LOOKUP[text_key(_id)] = _id
    _SOURCE_LOOKUP[text_key(_label)] = _id


def _dataset() -> SoccerData:
    return get_dataset()


def _error_text(error: QueryError) -> str:
    lines = [f"Could not answer: {error}"]
    if error.alternatives:
        lines.append("Candidates:")
        for entity in error.alternatives[:8]:
            lines.append(f"- {entity.display_name} ({entity.match_count} matches)")
    return "\n".join(lines)


def _resolve_source(source: str | None) -> str | None:
    if source is None:
        return None
    return _SOURCE_LOOKUP.get(text_key(source), source)


# ---------------------------------------------------------------------------
# Match tools
# ---------------------------------------------------------------------------


def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    stage: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    source: str | None = None,
    limit: int = 20,
) -> str:
    """Search matches across all datasets.

    Filter by team and/or opponent (any name variant works, e.g. "Flamengo",
    "Palmeiras-SP"), by competition ("Brasileirão", "Copa do Brasil",
    "Libertadores", "Série B", "Série C"), season (e.g. 2023), stage (e.g.
    "final", "semifinals", "group"), and an inclusive date range (YYYY-MM-DD
    or DD/MM/YYYY).  Optionally restrict to one source file (e.g.
    "Brasileirao_Matches.csv").  When both team and opponent are given, a
    head-to-head summary is included.  Overlapping rows across datasets are
    deduplicated automatically.
    """
    try:
        result = queries.search_matches(
            _dataset(),
            team=team,
            opponent=opponent,
            competition=competition,
            season=str(season) if season else None,
            stage=stage,
            date_from=date_from,
            date_to=date_to,
            source=_resolve_source(source),
            limit=limit,
        )
    except QueryError as error:
        return _error_text(error)
    return formatting.format_match_search(_dataset(), result, limit)


def head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """Head-to-head record between two teams (wins/draws/losses, goals).

    Example: head_to_head(team_a="Palmeiras", team_b="Santos").  Optional
    competition/season filters.  Uses deduplicated matches across all
    datasets.
    """
    try:
        result = queries.head_to_head(
            _dataset(),
            team_a,
            team_b,
            competition=competition,
            season=str(season) if season else None,
        )
    except QueryError as error:
        return _error_text(error)
    return formatting.format_head_to_head(result, _dataset())


def last_match(team: str, opponent: str | None = None) -> str:
    """Most recent match of a team (optionally against a given opponent)."""
    try:
        ds = _dataset()
        entity = queries.resolve_team(ds, team)
        match = queries.last_match(ds, team, opponent)
    except QueryError as error:
        return _error_text(error)
    return formatting.format_last_match(ds, match, entity)


# ---------------------------------------------------------------------------
# Team tools
# ---------------------------------------------------------------------------


def team_stats(
    team: str,
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """Win/draw/loss record, goals and home/away split for one team.

    Optional competition and season filters, e.g.
    team_stats(team="Corinthians", competition="Brasileirão", season=2022).
    """
    try:
        result = queries.team_stats(
            _dataset(), team, competition=competition, season=str(season) if season else None
        )
    except QueryError as error:
        return _error_text(error)
    return formatting.format_team_stats(_dataset(), result)


def compare_teams(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """Compare two teams side by side, including their head-to-head record."""
    try:
        stats_a, stats_b, h2h = queries.compare_teams(
            _dataset(),
            team_a,
            team_b,
            competition=competition,
            season=str(season) if season else None,
        )
    except QueryError as error:
        return _error_text(error)
    return formatting.format_compare(stats_a, stats_b, h2h)


def best_records(
    venue: str = "overall",
    competition: str | None = None,
    season: int | None = None,
    min_matches: int = 10,
    limit: int = 10,
) -> str:
    """Rank teams by win rate. venue: 'overall', 'home' or 'away'.

    Answers questions like "Which team has the best away record?".  Teams
    with fewer than min_matches (default 10) in the filter are skipped.
    """
    try:
        ds = _dataset()
        ranked = queries.best_records(
            ds,
            venue=venue,
            competition=competition,
            season=str(season) if season else None,
            min_matches=min_matches,
            limit=limit,
        )
    except QueryError as error:
        return _error_text(error)
    scope = "in the dataset"
    if competition:
        try:
            comp_id = queries.resolve_competition(ds, competition)
            scope = f"in the {formatting.comp_name(comp_id)}"
        except QueryError:
            pass
        if season:
            scope += f" {season}"
    elif season:
        scope = f"in season {season}"
    return formatting.format_ranking(ds, ranked, venue, scope)


def find_team(name: str) -> str:
    """Resolve a team name to its canonical entity.

    Shows the canonical id, state, every name variant seen in the datasets,
    competitions and seasons played, and the FIFA database club name when
    present.  Handles "Palmeiras-SP", "Sport Club Corinthians Paulista",
    nicknames ("Timão") and foreign spellings ("Nacional (URU)").
    """
    try:
        ds = _dataset()
        entity = queries.resolve_team(ds, name)
    except QueryError as error:
        return _error_text(error)
    return formatting.format_team_entity(entity)


def team_competitions(team: str) -> str:
    """Which competitions and seasons has a team played in the datasets?"""
    return find_team(team)


def list_teams(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 60,
) -> str:
    """List teams in a competition/season (or all Brazilian teams).

    Without arguments, lists every Brazilian club present in the match data,
    ordered by number of matches.
    """
    try:
        entities = queries.list_teams(
            _dataset(), competition=competition, season=str(season) if season else None
        )
    except QueryError as error:
        return _error_text(error)
    scope = "in the dataset"
    if competition and season:
        scope = f"in {competition} {season}"
    elif season:
        scope = f"in season {season}"
    return formatting.format_teams(entities[:limit], scope)


# ---------------------------------------------------------------------------
# Player tools
# ---------------------------------------------------------------------------


def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_age: int | None = None,
    limit: int = 20,
) -> str:
    """Search the FIFA player database (18,207 players).

    Filters: name (substring, accent-insensitive), nationality (e.g.
    "Brazil"), club (any name variant, e.g. "São Paulo FC" or "Juventus"),
    position (FIFA code like "ST"/"LW" or group "GK"/"DEF"/"MID"/"FWD"),
    minimum overall rating and maximum age.  At least one filter is required.
    """
    try:
        players, club_entity = queries.search_players(
            _dataset(),
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            max_age=max_age,
            limit=limit,
        )
    except QueryError as error:
        return _error_text(error)
    ds = _dataset()
    title = _player_title(name, nationality, club, club_entity, position, min_overall)
    text = formatting.format_players(players, title)
    if club and club_entity and not club_entity.fifa_club_names:
        text += _fifa_coverage_note(ds, club_entity)
    return text


def _player_title(
    name: str | None,
    nationality: str | None,
    club: str | None,
    club_entity,
    position: str | None,
    min_overall: int | None,
) -> str:
    parts = []
    if name:
        parts.append(f"name containing '{name}'")
    if nationality:
        parts.append(f"nationality: {nationality}")
    if club and club_entity:
        parts.append(f"club: {club_entity.display_name}")
    elif club:
        parts.append(f"club: {club}")
    if position:
        parts.append(f"position: {position.upper()}")
    if min_overall is not None:
        parts.append(f"overall >= {min_overall}")
    scope = "; ".join(parts) if parts else "all players"
    return f"Players matching ({scope}):"


def _fifa_coverage_note(ds: SoccerData, club_entity) -> str:
    """Honest context when a club is absent from the FIFA database."""
    brazilian_clubs = sorted(
        e.fifa_club_names and next(iter(e.fifa_club_names))
        for e in ds.registry.entities.values()
        if e.is_brazilian and e.fifa_club_names
    )
    return (
        f"\n\nNote: the FIFA dataset (FIFA 19-era data) does not include "
        f"{club_entity.display_name}. Brazilian clubs it does cover: "
        f"{', '.join(brazilian_clubs)}."
    )


def top_players(
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    attribute: str = "overall",
    limit: int = 10,
) -> str:
    """Top-rated players by overall rating or a skill attribute.

    attribute: 'overall' (default), 'potential', or a FIFA skill such as
    'Finishing', 'Dribbling', 'SprintSpeed'.  Example: who are the top
    Brazilian players? -> top_players(nationality="Brazil").
    """
    try:
        players, club_entity, attr = queries.top_players(
            _dataset(),
            nationality=nationality,
            club=club,
            position=position,
            attribute=attribute,
            limit=limit,
        )
    except QueryError as error:
        return _error_text(error)
    ds = _dataset()
    scope = []
    if nationality:
        scope.append(nationality)
    if club and club_entity:
        scope.append(club_entity.display_name)
    if position:
        scope.append(f"position {position.upper()}")
    scope_txt = " ".join(scope) if scope else "all"
    attr_txt = "overall rating" if attr == "overall" else (
        "potential" if attr == "potential" else attr
    )
    title = f"Top {scope_txt} players by {attr_txt}:"
    text = formatting.format_players(players, title)
    if club and club_entity and not club_entity.fifa_club_names:
        text += _fifa_coverage_note(ds, club_entity)
    return text


def find_player(name: str) -> str:
    """Look up one player by name and show full details.

    Example: find_player(name="Gabriel Barbosa").  Returns all matching
    players (substring, accent-insensitive) with ratings, club, position and
    key attributes.
    """
    try:
        players, _ = queries.search_players(_dataset(), name=name, limit=10)
    except QueryError as error:
        return _error_text(error)
    if not players:
        return f"No player found matching '{name}' in the FIFA dataset."
    if len(players) == 1:
        return formatting.format_player_detail(players[0])
    lines = [f"Players matching '{name}' ({len(players)} shown):"]
    for player in players:
        lines.append(formatting._player_line(player))
    lines.append("(use search_players with more filters to narrow down)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Competition tools
# ---------------------------------------------------------------------------


def list_competitions() -> str:
    """List competitions in the dataset with seasons, match counts and sources."""
    ds = _dataset()
    coverages = [ds.competition_coverage(comp_id) for comp_id in COMPETITIONS]
    return formatting.format_competitions(coverages)


def standings(competition: str, season: int, limit: int | None = None) -> str:
    """League table computed from match results (3 points per win).

    Works for Brasileirão Série A (2003-2023), Série B and Série C.  Marks the
    champion and the relegation zone.  Example:
    standings(competition="Brasileirão", season=2019).
    """
    try:
        result = queries.standings(_dataset(), competition, str(season))
    except QueryError as error:
        return _error_text(error)
    return formatting.format_standings(_dataset(), result, limit)


def champion(competition: str, season: int) -> str:
    """Who won a competition in a given season?

    Leagues: top of the computed standings.  Cups (Copa do Brasil,
    Libertadores): winner of the final over the aggregate of its legs; if the
    final was level and decided on penalties, says so (shootouts are not in
    the datasets).
    """
    try:
        result = queries.champion(_dataset(), competition, str(season))
    except QueryError as error:
        return _error_text(error)
    return formatting.format_champion(_dataset(), result)


def finals(competition: str, season: int | None = None) -> str:
    """Finals of a cup competition.

    Without a season, lists every final in the dataset (e.g. all Copa do
    Brasil finals).  With a season, shows that final's legs and aggregate.
    """
    try:
        results = queries.finals(_dataset(), competition, str(season) if season else None)
    except QueryError as error:
        return _error_text(error)
    if not results:
        return "No data found for this competition."
    return formatting.format_finals(_dataset(), results)


def knockout(competition: str, season: int) -> str:
    """Knockout bracket of a cup competition/season with aggregated ties.

    Example: knockout(competition="Libertadores", season=2018) shows the round
    of 16, quarterfinals, semifinals and final with two-legged aggregates.
    """
    try:
        bracket = queries.knockout(_dataset(), competition, str(season))
    except QueryError as error:
        return _error_text(error)
    return formatting.format_knockout(_dataset(), bracket)


# ---------------------------------------------------------------------------
# Statistics tools
# ---------------------------------------------------------------------------


def competition_stats(
    competition: str | None = None,
    season: int | None = None,
    team: str | None = None,
) -> str:
    """Aggregated statistics: average goals per match and outcome rates.

    Answers "What's the average goals per match in the Brasileirão?" and
    home/away win-rate questions.  All arguments optional; e.g.
    competition_stats(competition="Brasileirão", season=2019).
    """
    try:
        agg, comp_id, team_entity = queries.competition_stats(
            _dataset(),
            competition=competition,
            season=str(season) if season else None,
            team=team,
        )
    except QueryError as error:
        return _error_text(error)
    if team_entity:
        scope = f"{team_entity.display_name} matches"
        if comp_id:
            scope += f" in the {formatting.comp_name(comp_id)}"
            if season:
                scope += f" {season}"
    elif comp_id:
        scope = f"the {formatting.comp_name(comp_id)}" + (f" {season}" if season else "")
    else:
        scope = "all matches in the dataset"
    return formatting.format_aggregates(agg, scope)


def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    team: str | None = None,
    limit: int = 10,
) -> str:
    """Largest victories by goal margin.

    Example: biggest_wins(competition="Libertadores").  Optional season and
    team filters.
    """
    try:
        matches = queries.biggest_wins(
            _dataset(),
            competition=competition,
            season=str(season) if season else None,
            team=team,
            limit=limit,
        )
    except QueryError as error:
        return _error_text(error)
    scope = "in the dataset"
    if competition and season:
        scope = f"in the {competition} {season}"
    elif competition:
        scope = f"in the {competition}"
    elif season:
        scope = f"in season {season}"
    return formatting.format_biggest_wins(_dataset(), matches, scope)


def derbies(
    season: int | None = None,
    competition: str | None = None,
    limit: int = 40,
) -> str:
    """Matches between famous rival pairs (Fla-Flu, Grenal, Derby Paulista...).

    Example: derbies(season=2023) lists all derby fixtures of that season
    across competitions.
    """
    try:
        items = queries.derbies(
            _dataset(),
            season=str(season) if season else None,
            competition=competition,
            limit=limit,
        )
    except QueryError as error:
        return _error_text(error)
    return formatting.format_derbies(_dataset(), items)
