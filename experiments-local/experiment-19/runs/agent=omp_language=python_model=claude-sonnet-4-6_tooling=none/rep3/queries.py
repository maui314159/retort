"""
Query functions over the Brazilian soccer DataStore.
Each function returns a human-readable string suitable for MCP tool responses.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

import pandas as pd

from data_loader import DataStore, normalize_team


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ascii_lower(s: str) -> str:
    """Strip diacritics and lowercase — enables accent-insensitive matching."""
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii").lower()


def _team_match(series: pd.Series, name: str) -> pd.Series:
    """Case-insensitive substring match on a normalised team name series."""
    norm = normalize_team(name).lower()
    return series.str.lower().str.contains(re.escape(norm), na=False)


def _competition_match(series: pd.Series, competition: str) -> pd.Series:
    """Accent-insensitive substring match for competition names."""
    needle = _ascii_lower(competition)
    return series.map(lambda c: needle in _ascii_lower(str(c)) if pd.notna(c) else False)


def _filter_matches(
    df: pd.DataFrame,
    team: Optional[str] = None,
    team2: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> pd.DataFrame:
    """Return rows matching all supplied filters."""
    mask = pd.Series([True] * len(df), index=df.index)

    if team:
        home_m = _team_match(df["home_team"], team)
        away_m = _team_match(df["away_team"], team)
        mask &= home_m | away_m

    if team2:
        home_m2 = _team_match(df["home_team"], team2)
        away_m2 = _team_match(df["away_team"], team2)
        mask &= home_m2 | away_m2

    if competition:
        mask &= _competition_match(df["competition"], competition)

    if season is not None:
        mask &= df["season"] == season

    if date_from:
        mask &= df["date"] >= date_from

    if date_to:
        mask &= df["date"] <= date_to

    return df[mask].copy()


# ---------------------------------------------------------------------------
# 1. Find Matches
# ---------------------------------------------------------------------------

def find_matches(
    store: DataStore,
    team: Optional[str] = None,
    team2: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 30,
) -> str:
    """
    Find matches with optional filters.

    When two teams are provided, returns head-to-head history with a summary.
    Competition names can be partial: "brasileirao", "copa", "libertadores".
    Dates should be in YYYY-MM-DD format.
    """
    df = _filter_matches(
        store.all_matches, team=team, team2=team2,
        competition=competition, season=season,
        date_from=date_from, date_to=date_to,
    )

    if df.empty:
        parts = ["No matches found"]
        if team:
            parts.append(f" for {team}")
        if team2:
            parts.append(f" vs {team2}")
        if competition:
            parts.append(f" in {competition}")
        if season:
            parts.append(f" ({season})")
        return "".join(parts) + "."

    # Sort by date descending
    df = df.sort_values("date", ascending=False)

    total = len(df)
    display = df.head(limit)

    lines: list[str] = []

    if team and team2:
        t1 = normalize_team(team)
        t2 = normalize_team(team2)
        lines.append(f"{t1} vs {t2} — {total} matches found:")
        # head-to-head stats
        t1_wins = t2_wins = draws = 0
        t1_lower = t1.lower()
        t2_lower = t2.lower()
        for _, r in df.iterrows():
            hg, ag = int(r["home_goals"]), int(r["away_goals"])
            ht_lower = r["home_team"].lower()
            # determine which team is home
            is_t1_home = t1_lower in ht_lower or re.search(re.escape(t1_lower), ht_lower) is not None
            if hg > ag:
                (t1_wins if is_t1_home else t2_wins).__class__  # just for type; use below
                if is_t1_home:
                    t1_wins += 1
                else:
                    t2_wins += 1
            elif ag > hg:
                if is_t1_home:
                    t2_wins += 1
                else:
                    t1_wins += 1
            else:
                draws += 1
        lines.append(
            f"Head-to-head: {t1} {t1_wins} wins, {t2} {t2_wins} wins, {draws} draws\n"
        )
    elif team:
        t = normalize_team(team)
        lines.append(f"Matches for {t} — {total} found (showing {min(limit, total)}):")
    else:
        lines.append(f"Matches found: {total} (showing {min(limit, total)}):")

    for _, r in display.iterrows():
        date = r["date"] or "Unknown date"
        ht, at = r["home_team"], r["away_team"]
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        comp = r["competition"]
        rnd = f" Round {r['round']}" if r.get("round") and str(r["round"]) != "nan" else ""
        stage = f" ({r['stage']})" if r.get("stage") and str(r["stage"]) != "nan" else ""
        sea = f" {r['season']}" if r.get("season") else ""
        lines.append(f"  {date}: {ht} {hg}-{ag} {at}  [{comp}{sea}{rnd}{stage}]")

    if total > limit:
        lines.append(f"  ... and {total - limit} more matches.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. Team Statistics
# ---------------------------------------------------------------------------

def get_team_stats(
    store: DataStore,
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    home_only: bool = False,
    away_only: bool = False,
) -> str:
    """Return W/L/D record, goals, win rate for a team."""
    df = store.all_matches.copy()

    if competition:
        df = df[_competition_match(df["competition"], competition)]
    if season is not None:
        df = df[df["season"] == season]

    norm = normalize_team(team)
    norm_lower = norm.lower()

    home_mask = _team_match(df["home_team"], team)
    away_mask = _team_match(df["away_team"], team)

    if home_only:
        matches = df[home_mask]
    elif away_only:
        matches = df[away_mask]
    else:
        matches = df[home_mask | away_mask]

    if matches.empty:
        return (
            f"No data found for team '{team}'"
            + (f" in {competition}" if competition else "")
            + (f" season {season}" if season else "")
            + "."
        )

    wins = losses = draws = gf = ga = 0
    for _, r in matches.iterrows():
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        is_home = re.search(re.escape(norm_lower), r["home_team"].lower()) is not None
        if is_home:
            gf += hg; ga += ag
            if hg > ag:
                wins += 1
            elif hg < ag:
                losses += 1
            else:
                draws += 1
        else:
            gf += ag; ga += hg
            if ag > hg:
                wins += 1
            elif ag < hg:
                losses += 1
            else:
                draws += 1

    total = wins + losses + draws
    win_rate = (wins / total * 100) if total > 0 else 0.0

    header_parts = [norm]
    if home_only:
        header_parts.append("(home)")
    elif away_only:
        header_parts.append("(away)")
    if competition:
        header_parts.append(f"— {competition}")
    if season:
        header_parts.append(str(season))

    lines = [" ".join(header_parts) + ":"]
    lines.append(f"  Matches: {total}")
    lines.append(f"  Wins: {wins}")
    lines.append(f"  Draws: {draws}")
    lines.append(f"  Losses: {losses}")
    lines.append(f"  Goals For: {gf}, Goals Against: {ga}, GD: {gf - ga:+d}")
    lines.append(f"  Win rate: {win_rate:.1f}%")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. Player Search
# ---------------------------------------------------------------------------

def find_players(
    store: DataStore,
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_rating: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Search FIFA player dataset."""
    df = store.fifa.copy()

    if name:
        df = df[df["Name"].str.contains(name, case=False, na=False)]
    if nationality:
        df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]
    if club:
        df = df[df["Club"].str.contains(club, case=False, na=False)]
    if position:
        df = df[df["Position"].str.contains(position, case=False, na=False)]
    if min_rating is not None:
        df = df[pd.to_numeric(df["Overall"], errors="coerce") >= min_rating]

    if df.empty:
        return "No players found matching the given criteria."

    # Sort by overall rating descending
    df = df.copy()
    df["_overall_num"] = pd.to_numeric(df["Overall"], errors="coerce")
    df = df.sort_values("_overall_num", ascending=False).drop(columns=["_overall_num"])

    total = len(df)
    display = df.head(limit)

    header_parts = []
    if nationality:
        header_parts.append(nationality)
    if club:
        header_parts.append(f"at {club}")
    if position:
        header_parts.append(f"({position})")
    label = " ".join(header_parts) if header_parts else "All matching"
    lines = [f"{label} players — {total} found (showing {min(limit, total)}):"]

    for i, (_, r) in enumerate(display.iterrows(), 1):
        overall = r.get("Overall", "?")
        potential = r.get("Potential", "?")
        pos = r.get("Position", "?")
        player_club = r.get("Club", "?")
        nat = r.get("Nationality", "?")
        age = r.get("Age", "?")
        lines.append(
            f"  {i}. {r['Name']} — Overall: {overall}, Potential: {potential}, "
            f"Pos: {pos}, Club: {player_club}, Nat: {nat}, Age: {age}"
        )

    if total > limit:
        lines.append(f"  ... and {total - limit} more.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. Season Standings
# ---------------------------------------------------------------------------

def get_standings(
    store: DataStore,
    season: int,
    competition: str = "Brasileirão Série A",
) -> str:
    """Calculate league-style standings from match results for a given season."""
    df = store.all_matches.copy()
    df = df[_competition_match(df["competition"], competition)]
    df = df[df["season"] == season]

    if df.empty:
        return f"No match data found for {competition} season {season}."

    table: dict[str, dict] = {}

    def _ensure(t: str) -> None:
        if t not in table:
            table[t] = {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}

    for _, r in df.iterrows():
        ht, at = r["home_team"], r["away_team"]
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        _ensure(ht); _ensure(at)
        table[ht]["P"] += 1; table[at]["P"] += 1
        table[ht]["GF"] += hg; table[ht]["GA"] += ag
        table[at]["GF"] += ag; table[at]["GA"] += hg
        if hg > ag:
            table[ht]["W"] += 1; table[ht]["Pts"] += 3
            table[at]["L"] += 1
        elif ag > hg:
            table[at]["W"] += 1; table[at]["Pts"] += 3
            table[ht]["L"] += 1
        else:
            table[ht]["D"] += 1; table[ht]["Pts"] += 1
            table[at]["D"] += 1; table[at]["Pts"] += 1

    # Sort: Pts desc, GD desc, GF desc
    rows = sorted(
        table.items(),
        key=lambda x: (x[1]["Pts"], x[1]["GF"] - x[1]["GA"], x[1]["GF"]),
        reverse=True,
    )

    lines = [f"{competition} {season} — Final Standings:"]
    lines.append(f"  {'#':<3} {'Team':<28} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>4} {'GA':>4} {'GD':>4} {'Pts':>4}")
    lines.append("  " + "-" * 65)
    for pos, (team, s) in enumerate(rows, 1):
        gd = s["GF"] - s["GA"]
        lines.append(
            f"  {pos:<3} {team:<28} {s['P']:>3} {s['W']:>3} {s['D']:>3} {s['L']:>3} "
            f"{s['GF']:>4} {s['GA']:>4} {gd:>+4} {s['Pts']:>4}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 5. Statistical Analysis
# ---------------------------------------------------------------------------

def get_biggest_wins(
    store: DataStore,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> str:
    """Return biggest victories (by goal difference) from match data."""
    df = _filter_matches(store.all_matches, competition=competition, season=season)
    df = df.copy()
    df["goal_diff"] = (df["home_goals"] - df["away_goals"]).abs()
    df = df.sort_values("goal_diff", ascending=False).head(limit)

    if df.empty:
        return "No match data found."

    label = competition or "All competitions"
    if season:
        label += f" {season}"
    lines = [f"Biggest victories — {label}:"]
    for i, (_, r) in enumerate(df.iterrows(), 1):
        ht, at = r["home_team"], r["away_team"]
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        date = r["date"] or "?"
        comp = r["competition"]
        diff = abs(hg - ag)
        lines.append(f"  {i}. {date}: {ht} {hg}-{ag} {at}  (diff: {diff})  [{comp}]")
    return "\n".join(lines)


def get_competition_stats(
    store: DataStore,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """Return aggregate statistics for a competition/season."""
    df = _filter_matches(store.all_matches, competition=competition, season=season)

    if df.empty:
        return "No match data found."

    total_matches = len(df)
    total_goals = int((df["home_goals"] + df["away_goals"]).sum())
    avg_goals = total_goals / total_matches if total_matches else 0

    home_wins = int(((df["home_goals"] > df["away_goals"])).sum())
    away_wins = int(((df["away_goals"] > df["home_goals"])).sum())
    draws = total_matches - home_wins - away_wins

    home_win_pct = home_wins / total_matches * 100 if total_matches else 0
    away_win_pct = away_wins / total_matches * 100 if total_matches else 0
    draw_pct = draws / total_matches * 100 if total_matches else 0

    label = competition or "All competitions"
    if season:
        label += f" {season}"

    lines = [f"Statistics — {label}:"]
    lines.append(f"  Total matches: {total_matches}")
    lines.append(f"  Total goals: {total_goals}")
    lines.append(f"  Average goals per match: {avg_goals:.2f}")
    lines.append(f"  Home wins: {home_wins} ({home_win_pct:.1f}%)")
    lines.append(f"  Away wins: {away_wins} ({away_win_pct:.1f}%)")
    lines.append(f"  Draws: {draws} ({draw_pct:.1f}%)")

    # seasons covered
    seasons = sorted(df["season"].dropna().unique().astype(int).tolist())
    if seasons:
        lines.append(f"  Seasons covered: {seasons[0]}–{seasons[-1]}")

    return "\n".join(lines)


def get_best_records(
    store: DataStore,
    record_type: str = "home",
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 10,
    limit: int = 10,
) -> str:
    """
    Return teams ranked by win rate.
    record_type: 'home', 'away', or 'overall'
    """
    df = _filter_matches(store.all_matches, competition=competition, season=season)

    if df.empty:
        return "No match data found."

    stats: dict[str, dict] = {}

    def _ensure(t: str) -> None:
        if t not in stats:
            stats[t] = {"W": 0, "D": 0, "L": 0}

    for _, r in df.iterrows():
        ht, at = r["home_team"], r["away_team"]
        hg, ag = int(r["home_goals"]), int(r["away_goals"])

        if record_type in ("home", "overall"):
            _ensure(ht)
            if hg > ag:
                stats[ht]["W"] += 1
            elif hg < ag:
                stats[ht]["L"] += 1
            else:
                stats[ht]["D"] += 1

        if record_type in ("away", "overall"):
            _ensure(at)
            if ag > hg:
                stats[at]["W"] += 1
            elif ag < hg:
                stats[at]["L"] += 1
            else:
                stats[at]["D"] += 1

    rows = []
    for team, s in stats.items():
        total = s["W"] + s["D"] + s["L"]
        if total < min_matches:
            continue
        win_rate = s["W"] / total * 100
        rows.append((team, total, s["W"], s["D"], s["L"], win_rate))

    rows.sort(key=lambda x: x[5], reverse=True)
    rows = rows[:limit]

    if not rows:
        return f"Not enough data (min {min_matches} matches required)."

    type_label = {"home": "Home", "away": "Away", "overall": "Overall"}[record_type]
    label = competition or "All competitions"
    if season:
        label += f" {season}"
    lines = [f"Best {type_label} Records — {label} (min {min_matches} matches):"]
    lines.append(f"  {'#':<3} {'Team':<28} {'P':>4} {'W':>4} {'D':>4} {'L':>4} {'Win%':>6}")
    lines.append("  " + "-" * 57)
    for i, (team, total, w, d, l, wr) in enumerate(rows, 1):
        lines.append(f"  {i:<3} {team:<28} {total:>4} {w:>4} {d:>4} {l:>4} {wr:>5.1f}%")
    return "\n".join(lines)
