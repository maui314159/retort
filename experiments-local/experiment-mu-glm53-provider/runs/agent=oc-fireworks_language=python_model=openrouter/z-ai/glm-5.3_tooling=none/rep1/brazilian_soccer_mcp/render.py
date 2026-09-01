"""
 brazilian_soccer_mcp / render.py
 ================================

 Why
 ---
 TASK.md specifies example *answer formats* ("2019 Brasileirão Final
 Standings: 1. Flamengo - 90 pts (28W, 6D, 4L) - Champion ...").  Both the
 MCP tools (text content) and the CLI print those human answers, and they
 must stay identical, so every renderer lives here and consumes the dict
 returned by :mod:`brazilian_soccer_mcp.queries`.

 What
 ---
 One ``render_<tool>(result: dict) -> str`` per query function.  Every
 renderer is defensive: it never assumes a field exists (query errors
 render as a friendly message with suggestions).

 Test: exercised end-to-end via ``tests/test_server.py`` (tools/call text
 output) and the sample-question scenarios.
=======================================================================
"""

from __future__ import annotations


def _fmt_match(match: dict) -> str:
    date = match.get("date") or "date unknown"
    score = match.get("score") or "-"
    parts = [f"{date}: {match.get('home', '?')} {score} {match.get('away', '?')}"]
    bits = [match.get("competition_display", match.get("competition"))]
    if match.get("phase"):
        bits.append(str(match["phase"]))
    if match.get("season"):
        bits.append(str(match["season"]))
    parts.append(f" ({', '.join(b for b in bits if b)})")
    return "".join(parts)


def _fmt_score_line(match: dict) -> str:
    score = match.get("score") or "-"
    return (
        f"{match.get('home', '?')} {score} {match.get('away', '?')} "
        f"({match.get('competition_display', '')}"
        f"{' ' + str(match['season']) if match.get('season') else ''}"
        f"{', ' + str(match['phase']) if match.get('phase') else ''})"
    )


def render_error(result: dict) -> str:
    lines = [f"Sorry - {result.get('error', 'query failed')}"]
    if result.get("suggestions"):
        lines.append("Suggestions: " + ", ".join(result["suggestions"]))
    return "\n".join(lines)


def render_search_matches(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    header_bits = []
    if result.get("team") and result.get("opponent"):
        header_bits.append(f"{result['team']} vs {result['opponent']}")
    elif result.get("team"):
        header_bits.append(f"Matches involving {result['team']}")
    elif result.get("opponent"):
        header_bits.append(f"Matches involving {result['opponent']}")
    scope = result.get("competition", "all competitions")
    if scope != "all competitions" or not header_bits:
        header_bits.append(scope)
    if result.get("season"):
        header_bits.append(str(result["season"]))
    if result.get("stage_or_round"):
        header_bits.append(f"stage/round: {result['stage_or_round']}")
    lines = ["Match search: " + " - ".join(header_bits)]
    if result.get("team_alternatives"):
        lines.append(
            f"(Also matched clubs named similarly: "
            f"{', '.join(result['team_alternatives'])})"
        )
    for match in result.get("matches", []):
        lines.append("- " + _fmt_match(match))
    if not result.get("matches"):
        lines.append("- No matches found for these criteria.")
    if result.get("truncated"):
        lines.append(
            f"... ({result.get('total', 0) - result.get('shown', 0)} "
            f"more matches in dataset)"
        )
    else:
        lines.append(f"Total: {result.get('total', 0)} match(es)")
    return "\n".join(lines)


def render_last_match(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    a, b = result.get("team_a"), result.get("team_b")
    latest = result.get("last_played")
    if latest:
        when = latest.get("date") or "date unknown"
        opener = f"Last {a} vs {b} match (played): {when}: {_fmt_score_line(latest)}"
        lines = [opener]
    else:
        lines = [f"{a} and {b} have no played match in the dataset."]
    for scheduled in result.get("later_scheduled", []):
        lines.append(
            f"Later scheduled (no final score recorded): "
            f"{scheduled.get('date')}: {scheduled.get('home')} vs "
            f"{scheduled.get('away')}"
        )
    lines.append(f"Total meetings in dataset: {result.get('total_meetings', 0)}")
    return "\n".join(lines)


def render_head_to_head(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    a, b = result.get("team_a"), result.get("team_b")
    scope = result.get("competition", "all competitions")
    season_bit = f", {result['season']}" if result.get("season") else ""
    lines = [f"{a} vs {b} head-to-head ({scope}{season_bit}):"]
    lines.append(
        f"- Meetings: {result.get('meetings', 0)} | "
        f"{a}: {result.get('wins_team_a', 0)} wins, "
        f"{b}: {result.get('wins_team_b', 0)} wins, "
        f"{result.get('draws', 0)} draws"
    )
    lines.append(
        f"- Goals: {a} {result.get('goals_team_a', 0)} - "
        f"{result.get('goals_team_b', 0)} {b}"
    )
    for match in result.get("matches", []):
        lines.append("- " + _fmt_match(match))
    if not result.get("matches"):
        lines.append("- No matches found between these teams.")
    return "\n".join(lines)


def _fmt_record(record: dict, label: str) -> list[str]:
    lines = [f"{label}:"]
    lines.append(f"- Matches: {record.get('matches', 0)}")
    lines.append(
        f"- Wins: {record.get('wins', 0)}, Draws: {record.get('draws', 0)}, "
        f"Losses: {record.get('losses', 0)}"
    )
    lines.append(
        f"- Goals For: {record.get('goals_for', 0)}, "
        f"Goals Against: {record.get('goals_against', 0)}"
    )
    if record.get("win_rate") is not None:
        lines.append(f"- Win rate: {record['win_rate']}%")
    return lines


def render_team_stats(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    team = result.get("team")
    venue = result.get("venue") or "all"
    scope_bits = [
        str(result.get("season") or "all seasons"),
        result.get("competition", "all competitions"),
    ]
    venue_word = {
        "home": "home record",
        "away": "away record",
        "all": "overall record",
    }[venue]
    lines = [f"{team} {venue_word} ({', '.join(scope_bits)}):"]
    lines.extend(
        "  " + line for line in _fmt_record(result.get("record", {}), "Record")
    )
    if result.get("home_record") is not None:
        for split in ("home_record", "away_record"):
            rec = result.get(split)
            if rec:
                label = "Home split" if split == "home_record" else "Away split"
                lines.append(
                    f"  {label}: {rec.get('wins', 0)}W {rec.get('draws', 0)}D "
                    f"{rec.get('losses', 0)}L, GF {rec.get('goals_for', 0)}, "
                    f"GA {rec.get('goals_against', 0)}"
                )
    for comp in result.get("by_competition", []):
        lines.append(
            f"  {comp.get('competition')}: {comp.get('matches', 0)} matches, "
            f"{comp.get('wins', 0)}W {comp.get('draws', 0)}D "
            f"{comp.get('losses', 0)}L"
        )
    return "\n".join(lines)


def render_team_profile(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    club = result.get("club", {})
    lines = [f"{club.get('name')} (id: {club.get('key')})"]
    if club.get("state"):
        lines.append(f"State: {club['state']}")
    if club.get("country"):
        lines.append(f"Country: {club['country']}")
    seasons = (
        f"{club.get('first_season')}-{club.get('last_season')}"
        if club.get("first_season")
        else "n/a"
    )
    lines.append(
        f"Matches in dataset: {club.get('match_count', 0)} "
        f"({club.get('played_count', 0)} played), seasons {seasons}"
    )
    if club.get("name_variations"):
        shown = ", ".join(club["name_variations"][:8])
        more = len(club["name_variations"]) - 8
        lines.append(
            f"Name variations seen: {shown}" + (f" (+{more} more)" if more > 0 else "")
        )
    lines.append("Competitions played:")
    for comp in result.get("by_competition", []):
        seasons_info = comp.get("seasons", {})
        lines.append(
            f"- {comp.get('competition')}: {comp.get('matches', 0)} matches "
            f"({seasons_info.get('first')}-{seasons_info.get('last')})"
        )
    record = result.get("all_time_record", {})
    lines.append(
        f"All-time record: {record.get('wins', 0)}W {record.get('draws', 0)}D "
        f"{record.get('losses', 0)}L, GF {record.get('goals_for', 0)}, "
        f"GA {record.get('goals_against', 0)}"
    )
    fifa = result.get("fifa_players_in_dataset", 0)
    lines.append(f"FIFA player database: {fifa} player(s) listed at this club")
    if result.get("similar_named_clubs"):
        lines.append(
            "Similarly named clubs: " + ", ".join(result["similar_named_clubs"])
        )
    return "\n".join(lines)


def render_standings(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    header = (
        f"{result.get('competition')} {result.get('season')} standings "
        f"(calculated from {result.get('matches_counted', 0)} matches):"
    )
    lines = [header]
    for row in result.get("rows", []):
        marker = (
            " - Champion"
            if result.get("champion")
            and row["position"] == result["champion"]["position"]
            else ""
        )
        if (
            result.get("relegated")
            and row["position"] >= result["relegated"][-1]["position"]
        ):
            marker += " - Relegated"
        lines.append(
            f"{row['position']}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L, "
            f"GF {row['goals_for']}, GA {row['goals_against']}){marker}"
        )
    if result.get("relegated"):
        lines.append(
            f"Relegated (bottom {len(result['relegated'])}): "
            + ", ".join(r["team"] for r in result["relegated"])
        )
    return "\n".join(lines)


def render_biggest_wins(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    scope = result.get("competition", "all competitions")
    season = f" {result['season']}" if result.get("season") else ""
    lines = [f"Biggest victories ({scope}{season}):"]
    for index, match in enumerate(result.get("biggest_wins", []), start=1):
        lines.append(
            f"{index}. {match.get('date')}: {match.get('home')} "
            f"{match.get('score')} {match.get('away')} "
            f"({match.get('competition_display')}, margin "
            f"{match.get('margin')})"
        )
    if not result.get("biggest_wins"):
        lines.append("- No played matches found for this scope.")
    return "\n".join(lines)


def render_competition_stats(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    stats = result.get("stats", {})
    scope = result.get("competition", "all competitions")
    season = f" {result['season']}" if result.get("season") else ""
    lines = [f"Statistics for {scope}{season}:"]
    if not stats.get("played"):
        lines.append("- No played matches in scope.")
        return "\n".join(lines)
    lines.append(
        f"- Matches played: {stats['played']}"
        + (
            f" (+{stats['not_played']} unplayed listed)"
            if stats.get("not_played")
            else ""
        )
    )
    lines.append(f"- Average goals per match: {stats.get('avg_goals_per_match')}")
    lines.append(
        f"- Home win rate: {stats.get('home_win_rate')}% "
        f"(draws {stats.get('draw_rate')}%, away {stats.get('away_win_rate')}%)"
    )
    lines.append(
        f"- Average home goals: {stats.get('avg_home_goals')}, "
        f"away goals: {stats.get('avg_away_goals')}"
    )
    for entry in result.get("by_competition", []):
        lines.append(
            f"- {entry.get('competition')}: "
            f"{entry.get('avg_goals_per_match')} goals/match, "
            f"home win {entry.get('home_win_rate')}% over "
            f"{entry.get('played')} matches"
        )
    return "\n".join(lines)


def render_best_records(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    scope = result.get("competition", "all competitions")
    season = f" {result['season']}" if result.get("season") else ""
    header = (
        f"Best {result.get('venue')} records by {result.get('metric')} "
        f"({scope}{season}, min {result.get('min_matches')} matches):"
    )
    lines = [header]
    for index, row in enumerate(result.get("records", []), start=1):
        lines.append(
            f"{index}. {row['team']}: {row[result.get('metric')]} "
            f"({row['wins']}W {row['draws']}D {row['losses']}L in "
            f"{row['matches']} {result.get('venue')} matches)"
        )
    if not result.get("records"):
        lines.append("- Not enough matches for any team at this threshold.")
    return "\n".join(lines)


def render_derbies(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    season = result.get("season")
    lines = [
        "Classic Brazilian derbies"
        + (f" in {season}" if season else " (all seasons)")
        + ":"
    ]
    for derby in result.get("derbies", []):
        all_time = derby.get("all_time", {})
        lines.append(
            f"- {derby['derby']} ({derby['rivalry']}): {derby['team_a']} vs "
            f"{derby['team_b']} - {derby.get('matches_in_scope', 0)} match(es) in scope, "
            f"all-time {all_time.get('wins_team_a', 0)}-"
            f"{all_time.get('draws', 0)}-{all_time.get('wins_team_b', 0)} "
            f"(W-D-W)"
        )
        for match in derby.get("matches", []):
            lines.append("    * " + _fmt_match(match))
    if not result.get("derbies_with_matches"):
        lines.append("- No derby fixtures found in this scope.")
    return "\n".join(lines)


def render_player_search(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    criteria = result.get("criteria", {})
    crit_bits = []
    if criteria.get("name"):
        crit_bits.append(f"name~'{criteria['name']}'")
    if criteria.get("nationality"):
        crit_bits.append(f"nationality={criteria['nationality']}")
    if criteria.get("club"):
        crit_bits.append(f"club={criteria['club']}")
    if criteria.get("position"):
        crit_bits.append(f"position={criteria['position']}")
    if criteria.get("min_overall"):
        crit_bits.append(f"overall>={criteria['min_overall']}")
    lines = ["Player search" + (": " + ", ".join(crit_bits) if crit_bits else ":")]
    for index, player in enumerate(result.get("players", []), start=1):
        lines.append(
            f"{index}. {player['name']} - Overall: {player['overall']}, "
            f"Position: {player.get('position') or 'n/a'}, "
            f"Club: {player.get('club') or 'no club'}, "
            f"Age: {player.get('age') or 'n/a'}"
        )
    if not result.get("players"):
        lines.append("- No players match these criteria in the FIFA dataset.")
        if criteria.get("club"):
            lines.append(
                f"  (Note: the FIFA snapshot lists few Brazilian clubs; "
                f"'{criteria['club']}' may not be among them.)"
            )
    if result.get("truncated"):
        lines.append(
            f"... ({result.get('total', 0) - result.get('shown', 0)} more players)"
        )
    else:
        lines.append(f"Total: {result.get('total', 0)} player(s)")
    return "\n".join(lines)


def render_player_club_report(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    nationality = result.get("nationality", "all")
    lines = [
        f"Players by club (nationality: {nationality}"
        + (f", overall >= {result['min_overall']}" if result.get("min_overall") else "")
        + "):"
    ]
    for row in result.get("clubs_report", [])[:15]:
        flag = " [Brazilian club]" if row.get("brazilian_club_in_match_data") else ""
        lines.append(
            f"- {row['club']}: {row['players']} players "
            f"(avg rating: {row['avg_overall']}, best: "
            f"{row['best_player']['name']} {row['best_player']['overall']}){flag}"
        )
    total_clubs = result.get("clubs", 0)
    if total_clubs > 15:
        lines.append(f"... ({total_clubs - 15} more clubs)")
    return "\n".join(lines)


def render_list_competitions(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    lines = ["Competitions in the dataset:"]
    for comp in result.get("competitions", []):
        seasons = comp.get("seasons", [])
        span = f"{seasons[0]}-{seasons[-1]}" if seasons else "n/a"
        lines.append(
            f"- {comp['display']} ({comp['id']}): {comp['matches']} matches, "
            f"seasons {span} - {comp['description']}"
        )
    return "\n".join(lines)


def render_list_teams(result: dict) -> str:
    if not result.get("ok"):
        return render_error(result)
    scope = result.get("competition", "all competitions")
    season = f" {result['season']}" if result.get("season") else ""
    lines = [f"Teams ({scope}{season}) - {result.get('total', 0)} clubs:"]
    for team in result.get("teams", [])[:40]:
        where = (
            f", {team['state']}"
            if team.get("state")
            else (f", {team['country']}" if team.get("country") else "")
        )
        lines.append(f"- {team['name']}{where}: {team['match_count']} matches")
    if result.get("total", 0) > 40:
        lines.append(f"... ({result['total'] - 40} more clubs)")
    return "\n".join(lines)
