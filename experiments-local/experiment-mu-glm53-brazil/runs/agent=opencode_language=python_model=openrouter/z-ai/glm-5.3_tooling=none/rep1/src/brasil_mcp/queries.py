"""Query layer producing formatted, human-readable answers.

Each function returns a JSON-serializable dict containing a ready-to-print
``summary`` string (in the style of the spec's example answers) plus the raw
structured data, so MCP clients can either display the summary or process
the data themselves.
"""

from __future__ import annotations

from .models import Match, Player
from .store import SERIE_A, SoccerStore, default_data_dir

_store: SoccerStore | None = None


def get_store() -> SoccerStore:
    """Lazily build and cache the process-wide SoccerStore."""
    global _store
    if _store is None:
        _store = SoccerStore(default_data_dir())
    return _store


def _match_line(match: Match) -> str:
    return f"- {match.label()}"


def _player_line(player: Player) -> str:
    return (
        f"- {player.name} - Overall: {player.overall}, Position: {player.position or 'n/a'}, "
        f"Club: {player.club or 'n/a'}, Age: {player.age or 'n/a'}, Nationality: {player.nationality}"
    )


def _unknown_team_result(store: SoccerStore, name: str) -> dict:
    suggestions = store.suggest_teams(name)
    hint = ""
    if suggestions:
        hint = " Did you mean: " + ", ".join(store.team_display(s) for s in suggestions[:5]) + "?"
    return {
        "error": f"Team '{name}' not found in the datasets.{hint}",
        "suggestions": [store.team_display(s) for s in suggestions],
    }


def find_team(name: str) -> dict:
    """Resolve a team name (any spelling variant) and describe what we know.

    Cross-file query: reports match-data appearances, seasons, competitions
    and the FIFA squad (when the club exists in the player dataset).
    """
    store = get_store()
    cid = store.resolve_team(name)
    if not cid:
        return _unknown_team_result(store, name)
    matches, total = store.find_matches(team=cid, limit=None)
    seasons = sorted({m.season for m in matches if m.season})
    competitions = sorted({m.competition for m in matches})
    squad = store.squad_of(cid)
    trophies = []
    for season in seasons:
        table = store.standings(season, SERIE_A)
        if table and table["champion"] and table["champion"]["team"] == store.team_display(cid):
            trophies.append(f"{season} Brasileirão Série A")
    lines = [
        f"Team: {store.team_display(cid)}",
        f"Matches in dataset: {total}",
        f"Seasons: {seasons[0]}-{seasons[-1]}" if seasons else "Seasons: n/a",
        f"Competitions: {', '.join(competitions) if competitions else 'none'}",
    ]
    if trophies:
        lines.append(f"Titles in dataset: {', '.join(trophies)}")
    if squad:
        top = sorted((p for p in squad if p.overall is not None), key=lambda p: -p.overall)[:3]
        lines.append(
            f"FIFA squad: {len(squad)} players; top rated: "
            + ", ".join(f"{p.name} ({p.overall})" for p in top)
        )
    else:
        lines.append("FIFA squad: no players for this club in the player dataset")
    return {
        "summary": "\n".join(lines),
        "team": store.team_display(cid),
        "canonical_id": cid,
        "aliases": store.registry.aliases_of(cid)[:10],
        "total_matches": total,
        "seasons": seasons,
        "competitions": competitions,
        "titles": trophies,
        "squad_size": len(squad),
    }


def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
    venue: str = "any",
    limit: int = 20,
) -> dict:
    """Search matches by team, opponent, competition, season, date range, stage or venue."""
    store = get_store()
    if team:
        cid = store.resolve_team(team)
        if not cid:
            return _unknown_team_result(store, team)
        team = cid
    if opponent:
        oid = store.resolve_team(opponent)
        if not oid:
            return _unknown_team_result(store, opponent)
        opponent = oid
    matches, total = store.find_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        stage=stage,
        venue=venue,
        limit=limit,
    )
    filters = _describe_filters(store, team, opponent, competition, season, date_from, date_to, stage, venue)
    if not matches:
        return {"summary": f"No matches found{filters}.", "matches": [], "total": 0}
    lines = [f"Matches{filters}:"]
    lines.extend(_match_line(m) for m in matches)
    remaining = total - len(matches)
    if remaining > 0:
        lines.append(f"... ({remaining} more matches in dataset)")
    if team and opponent:
        h2h = _h2h_summary(store, team, opponent, matches, total)
        lines.append("")
        lines.extend(h2h)
    return {
        "summary": "\n".join(lines),
        "matches": [m.to_dict() for m in matches],
        "total": total,
    }


def _describe_filters(
    store: SoccerStore,
    team,
    opponent,
    competition,
    season,
    date_from,
    date_to,
    stage,
    venue,
) -> str:
    parts = []
    if team:
        label = store.team_display(team)
        if venue == "home":
            parts.append(f"{label} (home)")
        elif venue == "away":
            parts.append(f"{label} (away)")
        else:
            parts.append(label)
    if opponent:
        parts.append(f"vs {store.team_display(opponent)}")
    if competition:
        parts.append(competition)
    if season:
        parts.append(f"{season} season")
    if date_from:
        parts.append(f"from {date_from}")
    if date_to:
        parts.append(f"until {date_to}")
    if stage:
        parts.append(f"stage: {stage}")
    return f" for {' '.join(parts)}" if parts else ""


def _h2h_summary(
    store: SoccerStore, team_id: str, opponent_id: str, matches: list[Match], total: int
) -> list[str]:
    a_record = store.head_to_head(team_id, opponent_id)
    if not a_record or not matches:
        return []
    a, b = a_record["team_a"], a_record["team_b"]
    return [
        f"Head-to-head in dataset: {a['team']} {a['wins']} wins, "
        f"{b['team']} {b['wins']} wins, {a['draws']} draws"
        f" ({a['matches']} matches)"
    ]


def head_to_head(team_a: str, team_b: str, competition: str | None = None, limit: int = 20) -> dict:
    """Head-to-head record between two teams (all competitions by default)."""
    store = get_store()
    a_id = store.resolve_team(team_a)
    b_id = store.resolve_team(team_b)
    if not a_id:
        return _unknown_team_result(store, team_a)
    if not b_id:
        return _unknown_team_result(store, team_b)
    result = store.head_to_head(a_id, b_id, competition=competition)
    if not result or not result["matches"]:
        return {
            "summary": f"No matches found between {team_a} and {team_b}.",
            "matches": [],
            "total": 0,
        }
    a, b = result["team_a"], result["team_b"]
    matches = result["matches"]
    shown = matches[:limit]
    lines = [f"{a['team']} vs {b['team']} head-to-head:"]
    lines.extend(_match_line(m) for m in shown)
    if len(matches) > limit:
        lines.append(f"... ({len(matches) - limit} more matches in dataset)")
    lines.append("")
    lines.append(
        f"Head-to-head in dataset: {a['team']} {a['wins']} wins, "
        f"{b['team']} {b['wins']} wins, {a['draws']} draws"
        f" ({a['matches']} matches)"
    )
    lines.append(
        f"Goals: {a['team']} {a['goals_for']}-{a['goals_against']} {b['team']}"
    )
    return {
        "summary": "\n".join(lines),
        "team_a": a,
        "team_b": b,
        "matches": [m.to_dict() for m in shown],
        "total": len(matches),
    }


def team_stats(team: str, season: int | None = None, competition: str | None = None) -> dict:
    """Win/draw/loss records (overall, home, away) with goals, per competition and per season."""
    store = get_store()
    cid = store.resolve_team(team)
    if not cid:
        return _unknown_team_result(store, team)
    stats = store.team_stats(cid, season=season, competition=competition)
    if not stats or stats["overall"]["matches"] == 0:
        label = f" for {season}" if season else ""
        return {
            "summary": f"No matches found for {stats['team']}{label}.",
            "total": 0,
        }
    overall, home, away = stats["overall"], stats["home"], stats["away"]
    context = []
    if season:
        context.append(str(season))
    if competition:
        context.append(competition)
    context_str = f" ({', '.join(context)})" if context else ""
    lines = [
        f"{overall['team']} record{context_str}:",
        f"- Matches: {overall['matches']}",
        f"- Overall: {overall['wins']} wins, {overall['draws']} draws, {overall['losses']} losses "
        f"(win rate: {overall['win_rate']}%)",
        f"- Home: {home['matches']} matches, {home['wins']}W {home['draws']}D {home['losses']}L, "
        f"goals {home['goals_for']}-{home['goals_against']} (win rate: {home['win_rate']}%)",
        f"- Away: {away['matches']} matches, {away['wins']}W {away['draws']}D {away['losses']}L, "
        f"goals {away['goals_for']}-{away['goals_against']} (win rate: {away['win_rate']}%)",
        f"- Total goals: {overall['goals_for']} scored, {overall['goals_against']} conceded "
        f"(diff {overall['goal_diff']:+d})",
    ]
    if stats["by_competition"]:
        lines.append("By competition:")
        for comp in stats["by_competition"]:
            lines.append(
                f"- {comp['competition']}: {comp['wins']}W {comp['draws']}D {comp['losses']}L "
                f"in {comp['matches']} matches"
            )
    return {"summary": "\n".join(lines), **stats}


def team_season_history(team: str, competition: str | None = None, limit: int = 25) -> dict:
    """Per-season performance trend for a team."""
    store = get_store()
    cid = store.resolve_team(team)
    if not cid:
        return _unknown_team_result(store, team)
    stats = store.team_stats(cid, competition=competition)
    if not stats or not stats["by_season"]:
        return {"summary": f"No seasonal data found for {stats['team'] if stats else team}.", "seasons": []}
    lines = [f"{stats['team']} season-by-season (newest first):"]
    for record in stats["by_season"][:limit]:
        lines.append(
            f"- {record['season']}: {record['matches']} matches, "
            f"{record['wins']}W {record['draws']}D {record['losses']}L, "
            f"goals {record['goals_for']}-{record['goals_against']}, "
            f"{record['points']} pts (win rate {record['win_rate']}%)"
        )
    return {"summary": "\n".join(lines), "seasons": stats["by_season"][:limit]}


def standings(season: int, competition: str = SERIE_A) -> dict:
    """League table for a season, computed from match results.

    Also reports the champion and the bottom four (typical relegation zone).
    """
    store = get_store()
    table = store.standings(season, competition)
    if not table:
        return {
            "summary": f"No data found for {competition} {season}.",
            "table": [],
        }
    if competition and "libertadores" in competition.lower():
        lines = [f"{table['competition']} {table['season']}:"]
        for stage in table["stages"]:
            lines.append(f"{stage['stage'].title()}:")
            lines.extend(f"  {_match_line(m)}" for m in stage["matches"])
        return {
            "summary": "\n".join(lines),
            "season": table["season"],
            "competition": table["competition"],
            "stages": [
                {"stage": s["stage"], "matches": [m.to_dict() for m in s["matches"]]}
                for s in table["stages"]
            ],
        }
    rows = table["table"]
    lines = [f"{table['competition']} {table['season']} Final Standings (calculated from matches):"]
    for position, row in enumerate(rows, start=1):
        marker = " - Champion" if position == 1 else ""
        lines.append(
            f"{position}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L){marker}"
        )
    relegated = ", ".join(row["team"] for row in table["relegated"])
    lines.append(f"Relegation zone: {relegated}")
    return {
        "summary": "\n".join(lines),
        "season": table["season"],
        "competition": table["competition"],
        "table": rows,
        "champion": table["champion"],
        "relegated": table["relegated"],
    }


def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    max_age: int | None = None,
    order_by: str = "overall",
    limit: int = 20,
) -> dict:
    """Search FIFA players by name, nationality, club, position or ratings.

    ``club`` accepts Brazilian team name variants (e.g. 'Athletico-PR') as
    well as foreign club names. Position accepts codes ('ST', 'LW') or group
    names ('forward', 'goalkeeper', 'midfielder', 'defender').
    """
    store = get_store()
    players, total = store.player_search(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        max_overall=max_overall,
        max_age=max_age,
        order_by=order_by,
        limit=limit,
    )
    filters = []
    if name:
        filters.append(f"name containing '{name}'")
    if nationality:
        filters.append(f"nationality {nationality}")
    if club:
        filters.append(f"club {club}")
    if position:
        filters.append(f"position {position}")
    if min_overall is not None:
        filters.append(f"overall >= {min_overall}")
    if max_age is not None:
        filters.append(f"age <= {max_age}")
    filter_text = f" ({'; '.join(filters)})" if filters else ""
    if not players:
        hint = ""
        if club and store.resolve_team(club):
            available = store.brazilian_clubs_with_squads()
            if available:
                names = ", ".join(c["club"] for c in available[:10])
                hint = (
                    f" Note: the FIFA dataset in this repo does not include a squad for "
                    f"'{store.team_display(store.resolve_team(club))}'. Brazilian clubs with squads: {names}."
                )
        return {
            "summary": f"No players found{filter_text}.{hint}",
            "players": [],
            "total": 0,
        }
    lines = [f"Players{filter_text} - showing {len(players)} of {total}:"]
    lines.extend(_player_line(p) for p in players)
    if total > len(players):
        lines.append(f"... ({total - len(players)} more players in dataset)")
    return {
        "summary": "\n".join(lines),
        "players": [p.to_dict() for p in players],
        "total": total,
    }


def team_players(team: str, position: str | None = None, limit: int = 25) -> dict:
    """The FIFA squad of a Brazilian team, highest rated first."""
    store = get_store()
    cid = store.resolve_team(team)
    if not cid:
        return _unknown_team_result(store, team)
    squad = store.squad_of(cid)
    if not squad:
        available = store.brazilian_clubs_with_squads()
        names = ", ".join(c["club"] for c in available) or "none"
        return {
            "summary": (
                f"No FIFA squad found for {store.team_display(cid)} in the player dataset. "
                f"Brazilian clubs with squads in the dataset: {names}."
            ),
            "players": [],
            "total": 0,
        }
    players, total = store.player_search(
        club=cid, position=position, order_by="overall", limit=limit
    )
    lines = [
        f"{store.team_display(cid)} squad in FIFA dataset ({len(squad)} players, "
        f"highest rated first):"
    ]
    lines.extend(_player_line(p) for p in players)
    return {
        "summary": "\n".join(lines),
        "players": [p.to_dict() for p in players],
        "total": total,
    }


def competition_info(competition: str | None = None, season: int | None = None) -> dict:
    """Describe what competitions, seasons and matches the datasets cover."""
    store = get_store()
    rows = store.competitions_summary()
    if competition:
        wanted = [c for c in rows if competition.lower() in c["competition"].lower()]
    else:
        wanted = rows
    lines = ["Competitions available in the datasets:"]
    for row in wanted:
        extra = f", {season}" if season else ""
        lines.append(
            f"- {row['competition']}: {row['matches']} matches, "
            f"seasons {row['seasons']}{extra}, {row['teams']} teams"
        )
    if season:
        matches, total = store.find_matches(competition=competition, season=season, limit=None)
        lines.append(f"Matches found for {season}: {len(matches)}")
    return {"summary": "\n".join(lines), "competitions": wanted}


def derbies(season: int | None = None, competition: str | None = None, limit: int = 15) -> dict:
    """Matches between traditional rivals (Fla-Flu, Grenal, Majestoso, ...)."""
    store = get_store()
    pairs = store.derbies(season=season, competition=competition, limit=limit)
    context = f" in {season}" if season else ""
    if not pairs:
        return {
            "summary": f"No derby matches found{context}.",
            "derbies": {},
        }
    lines = [f"Derby matches{context}:"]
    total = 0
    for name, matches in pairs.items():
        total += len(matches)
        lines.append(f"{name} ({len(matches)} matches):")
        lines.extend(f"  {_match_line(m)}" for m in matches)
    return {
        "summary": "\n".join(lines),
        "derbies": {
            name: [m.to_dict() for m in matches] for name, matches in pairs.items()
        },
        "total": total,
    }


def biggest_wins(competition: str | None = None, season: int | None = None, limit: int = 10) -> dict:
    """Largest goal-margin victories in the datasets."""
    store = get_store()
    wins = store.biggest_wins(competition=competition, season=season, limit=limit)
    if not wins:
        return {"summary": "No played matches found for the requested filters.", "matches": []}
    lines = ["Biggest victories (provided data):"]
    for position, match in enumerate(wins, start=1):
        lines.append(f"{position}. {match.label()}")
    return {"summary": "\n".join(lines), "matches": [m.to_dict() for m in wins]}


def goals_analysis(competition: str | None = None, season: int | None = None) -> dict:
    """Average goals per match plus home/away win rates and draw rate."""
    store = get_store()
    analysis = store.goals_analysis(competition=competition, season=season)
    if not analysis:
        return {"summary": "No played matches found for the requested filters."}
    label = f" ({competition}{' ' + str(season) if season else ''})" if competition or season else ""
    lines = [
        f"Goals analysis{label}:",
        f"- Matches: {analysis['matches']}",
        f"- Average goals per match: {analysis['avg_goals_per_match']}",
        f"- Average home goals: {analysis['avg_home_goals']}, "
        f"average away goals: {analysis['avg_away_goals']}",
        f"- Home win rate: {analysis['home_win_rate']}%",
        f"- Away win rate: {analysis['away_win_rate']}%",
        f"- Draw rate: {analysis['draw_rate']}%",
    ]
    return {"summary": "\n".join(lines), **analysis}


def best_records(
    competition: str | None = None,
    season: int | None = None,
    venue: str = "overall",
    min_matches: int = 10,
    limit: int = 10,
) -> dict:
    """Rank teams by points per game (optionally home-only or away-only)."""
    store = get_store()
    records = store.best_records(
        competition=competition,
        season=season,
        venue=venue,
        min_matches=min_matches,
        limit=limit,
    )
    if not records:
        return {"summary": "No records found for the requested filters.", "teams": []}
    venue_label = {"home": "home", "away": "away", "overall": "overall"}[venue]
    context = []
    if competition:
        context.append(competition)
    if season:
        context.append(str(season))
    context_str = f" ({', '.join(context)})" if context else ""
    lines = [f"Best {venue_label} records{context_str} (min {min_matches} matches):"]
    for position, record in enumerate(records, start=1):
        lines.append(
            f"{position}. {record['team']} - {record['ppg']} pts/game "
            f"({record['wins']}W {record['draws']}D {record['losses']}L, "
            f"win rate {record['win_rate']}%)"
        )
    return {"summary": "\n".join(lines), "teams": records}


def compare_teams(team_a: str, team_b: str, season: int | None = None) -> dict:
    """Side-by-side comparison of two teams: records, titles and head-to-head.

    Cross-file query: match statistics come from the match datasets while
    squad ratings come from the FIFA player dataset.
    """
    store = get_store()
    a_id = store.resolve_team(team_a)
    b_id = store.resolve_team(team_b)
    if not a_id:
        return _unknown_team_result(store, team_a)
    if not b_id:
        return _unknown_team_result(store, team_b)
    a_stats = store.team_stats(a_id, season=season)
    b_stats = store.team_stats(b_id, season=season)
    h2h = store.head_to_head(a_id, b_id)
    season_label = f" {season}" if season else ""
    lines = [
        f"{a_stats['team']} vs {b_stats['team']} comparison{season_label}:",
        "",
        f"{a_stats['team']}: {a_stats['overall']['matches']} matches, "
        f"{a_stats['overall']['wins']}W {a_stats['overall']['draws']}D {a_stats['overall']['losses']}L, "
        f"goals {a_stats['overall']['goals_for']}-{a_stats['overall']['goals_against']} "
        f"({a_stats['overall']['points']} pts)",
        f"{b_stats['team']}: {b_stats['overall']['matches']} matches, "
        f"{b_stats['overall']['wins']}W {b_stats['overall']['draws']}D {b_stats['overall']['losses']}L, "
        f"goals {b_stats['overall']['goals_for']}-{b_stats['overall']['goals_against']} "
        f"({b_stats['overall']['points']} pts)",
    ]
    if h2h and h2h["matches"]:
        a, b = h2h["team_a"], h2h["team_b"]
        lines.extend(
            [
                "",
                f"Head-to-head: {a['team']} {a['wins']} wins, {b['team']} {b['wins']} wins, "
                f"{a['draws']} draws ({a['matches']} matches)",
            ]
        )
        last = h2h["matches"][0]
        lines.append(f"Most recent meeting: {last.label()}")
    for stats, cid in ((a_stats, a_id), (b_stats, b_id)):
        squad = store.squad_of(cid)
        if squad:
            best = max((p.overall for p in squad if p.overall is not None), default=None)
            lines.append(
                f"{stats['team']} FIFA squad: {len(squad)} players (best rating: {best})"
            )
    return {
        "summary": "\n".join(lines),
        "team_a": a_stats,
        "team_b": b_stats,
        "head_to_head": (
            {"team_a": h2h["team_a"], "team_b": h2h["team_b"], "total": len(h2h["matches"])}
            if h2h else None
        ),
    }
