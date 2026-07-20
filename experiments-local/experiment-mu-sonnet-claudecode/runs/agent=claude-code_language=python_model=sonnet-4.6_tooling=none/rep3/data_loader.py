"""Data loader and query engine for Brazilian soccer datasets."""

import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

# Team name normalization map for common variants
_TEAM_ALIASES: dict[str, str] = {
    "atletico mineiro": "atletico-mg",
    "atletico-mg": "atletico-mg",
    "atletico mg": "atletico-mg",
    "atletico": "atletico-mg",
    "atletico paranaense": "atletico-pr",
    "atletico-pr": "atletico-pr",
    "atletico goianiense": "atletico-go",
    "atletico-go": "atletico-go",
    "flamengo": "flamengo",
    "fluminense": "fluminense",
    "vasco": "vasco",
    "vasco da gama": "vasco",
    "botafogo": "botafogo",
    "palmeiras": "palmeiras",
    "corinthians": "corinthians",
    "sport club corinthians paulista": "corinthians",
    "sao paulo": "sao paulo",
    "santos": "santos",
    "gremio": "gremio",
    "internacional": "internacional",
    "cruzeiro": "cruzeiro",
    "sport": "sport",
    "sport recife": "sport",
}


def _strip_accents(text: str) -> str:
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8")


def normalize_team(name: str) -> str:
    """Normalize team name: remove state suffix, lowercase, strip accents."""
    if not isinstance(name, str):
        return ""
    # Remove state suffix like "-SP", "-RJ", "-MG", etc.
    cleaned = re.sub(r"-[A-Z]{2}$", "", name.strip())
    cleaned = _strip_accents(cleaned).lower().strip()
    return _TEAM_ALIASES.get(cleaned, cleaned)


def team_matches(name: str, candidate: str) -> bool:
    """Return True if candidate team name matches search name."""
    norm_name = normalize_team(name)
    norm_cand = normalize_team(candidate)
    return norm_name in norm_cand or norm_cand in norm_name


def _parse_date(val) -> Optional[pd.Timestamp]:
    if pd.isna(val):
        return None
    s = str(val).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return pd.Timestamp(pd.to_datetime(s, format=fmt))
        except Exception:
            pass
    try:
        return pd.Timestamp(pd.to_datetime(s))
    except Exception:
        return None


@lru_cache(maxsize=1)
def load_brasileirao() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brasileirao_Matches.csv")
    df["competition"] = "Brasileirao Serie A"
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["home"] = df["home_team"].apply(normalize_team)
    df["away"] = df["away_team"].apply(normalize_team)
    df["home_goals"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goals"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    return df


@lru_cache(maxsize=1)
def load_copa_brasil() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brazilian_Cup_Matches.csv")
    df["competition"] = "Copa do Brasil"
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["home"] = df["home_team"].apply(normalize_team)
    df["away"] = df["away_team"].apply(normalize_team)
    df["home_goals"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goals"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    return df


@lru_cache(maxsize=1)
def load_libertadores() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Libertadores_Matches.csv")
    df["competition"] = "Copa Libertadores"
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["home"] = df["home_team"].apply(normalize_team)
    df["away"] = df["away_team"].apply(normalize_team)
    df["home_goals"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goals"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    return df


@lru_cache(maxsize=1)
def load_br_football() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "BR-Football-Dataset.csv")
    df["competition"] = df["tournament"].fillna("Unknown")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["home"] = df["home"].apply(normalize_team)
    df["away"] = df["away"].apply(normalize_team)
    df["home_goals"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goals"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = df["date"].dt.year.astype("Int64")
    return df


@lru_cache(maxsize=1)
def load_historico() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv", encoding="utf-8")
    df["competition"] = "Brasileirao Serie A"
    df["date"] = df["Data"].apply(_parse_date)
    df["home"] = df["Equipe_mandante"].apply(normalize_team)
    df["away"] = df["Equipe_visitante"].apply(normalize_team)
    df["home_goals"] = pd.to_numeric(df["Gols_mandante"], errors="coerce")
    df["away_goals"] = pd.to_numeric(df["Gols_visitante"], errors="coerce")
    df["season"] = pd.to_numeric(df["Ano"], errors="coerce").astype("Int64")
    df["home_team"] = df["Equipe_mandante"]
    df["away_team"] = df["Equipe_visitante"]
    df["round"] = df["Rodada"]
    return df


@lru_cache(maxsize=1)
def load_fifa() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "fifa_data.csv", encoding="utf-8")
    # Handle BOM in column names
    df.columns = [c.strip().lstrip("﻿") for c in df.columns]
    return df


@lru_cache(maxsize=1)
def load_all_matches() -> pd.DataFrame:
    """Combine all match datasets into a unified DataFrame."""
    cols = ["date", "home", "away", "home_team", "away_team", "home_goals", "away_goals", "season", "competition", "round"]

    frames = []
    for loader in [load_brasileirao, load_copa_brasil, load_libertadores, load_br_football, load_historico]:
        df = loader()
        available = [c for c in cols if c in df.columns]
        frames.append(df[available])

    combined = pd.concat(frames, ignore_index=True, sort=False)
    # Fill missing home_team/away_team from normalized home/away columns
    if "home_team" not in combined.columns:
        combined["home_team"] = combined["home"]
    else:
        combined["home_team"] = combined["home_team"].fillna(combined["home"])
    if "away_team" not in combined.columns:
        combined["away_team"] = combined["away"]
    else:
        combined["away_team"] = combined["away_team"].fillna(combined["away"])
    return combined


# ── Query functions ────────────────────────────────────────────────────────────


def find_matches(
    team1: Optional[str] = None,
    team2: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Find matches matching the given criteria."""
    df = load_all_matches()

    if team1:
        norm1 = normalize_team(team1)
        mask = df["home"].apply(lambda x: norm1 in str(x) or str(x) in norm1) | \
               df["away"].apply(lambda x: norm1 in str(x) or str(x) in norm1)
        df = df[mask]

    if team2:
        norm2 = normalize_team(team2)
        mask = df["home"].apply(lambda x: norm2 in str(x) or str(x) in norm2) | \
               df["away"].apply(lambda x: norm2 in str(x) or str(x) in norm2)
        df = df[mask]

    if competition:
        comp_lower = competition.lower()
        df = df[df["competition"].str.lower().str.contains(comp_lower, na=False)]

    if season:
        df = df[df["season"] == season]

    if date_from:
        df = df[df["date"] >= pd.to_datetime(date_from)]

    if date_to:
        df = df[df["date"] <= pd.to_datetime(date_to)]

    df = df.sort_values("date", ascending=False, na_position="last")
    df = df.head(limit)

    results = []
    for _, row in df.iterrows():
        results.append({
            "date": str(row["date"])[:10] if pd.notna(row.get("date")) else "unknown",
            "home_team": str(row.get("home_team") or row.get("home", "")),
            "away_team": str(row.get("away_team") or row.get("away", "")),
            "home_goals": int(row["home_goals"]) if pd.notna(row.get("home_goals")) else None,
            "away_goals": int(row["away_goals"]) if pd.notna(row.get("away_goals")) else None,
            "competition": str(row.get("competition", "")),
            "season": int(row["season"]) if pd.notna(row.get("season")) else None,
            "round": str(row["round"]) if pd.notna(row.get("round")) else None,
        })
    return results


def get_team_stats(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> dict:
    """Calculate win/draw/loss stats for a team."""
    df = load_all_matches()

    norm = normalize_team(team)
    home_mask = df["home"].apply(lambda x: norm in str(x) or str(x) in norm)
    away_mask = df["away"].apply(lambda x: norm in str(x) or str(x) in norm)
    team_df = df[home_mask | away_mask]

    if competition:
        comp_lower = competition.lower()
        team_df = team_df[team_df["competition"].str.lower().str.contains(comp_lower, na=False)]

    if season:
        team_df = team_df[team_df["season"] == season]

    if team_df.empty:
        return {"team": team, "matches": 0, "message": "No matches found"}

    team_df = team_df.dropna(subset=["home_goals", "away_goals"])

    home = team_df[team_df["home"].apply(lambda x: norm in str(x) or str(x) in norm)]
    away = team_df[team_df["away"].apply(lambda x: norm in str(x) or str(x) in norm)]

    home_wins = (home["home_goals"] > home["away_goals"]).sum()
    home_draws = (home["home_goals"] == home["away_goals"]).sum()
    home_losses = (home["home_goals"] < home["away_goals"]).sum()
    home_gf = home["home_goals"].sum()
    home_ga = home["away_goals"].sum()

    away_wins = (away["away_goals"] > away["home_goals"]).sum()
    away_draws = (away["away_goals"] == away["home_goals"]).sum()
    away_losses = (away["away_goals"] < away["home_goals"]).sum()
    away_gf = away["away_goals"].sum()
    away_ga = away["home_goals"].sum()

    total_matches = len(home) + len(away)
    wins = int(home_wins + away_wins)
    draws = int(home_draws + away_draws)
    losses = int(home_losses + away_losses)
    gf = int(home_gf + away_gf)
    ga = int(home_ga + away_ga)

    return {
        "team": team,
        "competition": competition or "all",
        "season": season or "all",
        "matches": total_matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "win_rate": round(wins / total_matches * 100, 1) if total_matches > 0 else 0,
        "home": {
            "matches": int(len(home)),
            "wins": int(home_wins),
            "draws": int(home_draws),
            "losses": int(home_losses),
            "goals_for": int(home_gf),
            "goals_against": int(home_ga),
        },
        "away": {
            "matches": int(len(away)),
            "wins": int(away_wins),
            "draws": int(away_draws),
            "losses": int(away_losses),
            "goals_for": int(away_gf),
            "goals_against": int(away_ga),
        },
    }


def get_head_to_head(team1: str, team2: str, limit: int = 20) -> dict:
    """Get head-to-head record between two teams."""
    df = load_all_matches()

    norm1 = normalize_team(team1)
    norm2 = normalize_team(team2)

    mask = (
        (df["home"].apply(lambda x: norm1 in str(x) or str(x) in norm1) &
         df["away"].apply(lambda x: norm2 in str(x) or str(x) in norm2)) |
        (df["home"].apply(lambda x: norm2 in str(x) or str(x) in norm2) &
         df["away"].apply(lambda x: norm1 in str(x) or str(x) in norm1))
    )
    h2h = df[mask].dropna(subset=["home_goals", "away_goals"]).sort_values("date", ascending=False)

    t1_wins = 0
    t2_wins = 0
    draws = 0

    for _, row in h2h.iterrows():
        is_home1 = norm1 in str(row["home"]) or str(row["home"]) in norm1
        hg, ag = row["home_goals"], row["away_goals"]
        if hg > ag:
            if is_home1:
                t1_wins += 1
            else:
                t2_wins += 1
        elif ag > hg:
            if is_home1:
                t2_wins += 1
            else:
                t1_wins += 1
        else:
            draws += 1

    recent = []
    for _, row in h2h.head(limit).iterrows():
        recent.append({
            "date": str(row["date"])[:10] if pd.notna(row.get("date")) else "unknown",
            "home_team": str(row.get("home_team") or row.get("home", "")),
            "away_team": str(row.get("away_team") or row.get("away", "")),
            "home_goals": int(row["home_goals"]),
            "away_goals": int(row["away_goals"]),
            "competition": str(row.get("competition", "")),
            "season": int(row["season"]) if pd.notna(row.get("season")) else None,
        })

    return {
        "team1": team1,
        "team2": team2,
        "total_matches": len(h2h),
        f"{team1}_wins": t1_wins,
        f"{team2}_wins": t2_wins,
        "draws": draws,
        "recent_matches": recent,
    }


def find_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> list[dict]:
    """Find players from the FIFA dataset."""
    df = load_fifa()

    if name:
        df = df[df["Name"].str.contains(name, case=False, na=False)]

    if nationality:
        df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]

    if club:
        df = df[df["Club"].str.contains(club, case=False, na=False)]

    if position:
        df = df[df["Position"].str.contains(position, case=False, na=False)]

    if min_overall:
        df = df[pd.to_numeric(df["Overall"], errors="coerce") >= min_overall]

    df = df.sort_values("Overall", ascending=False)
    df = df.head(limit)

    results = []
    for _, row in df.iterrows():
        results.append({
            "name": str(row.get("Name", "")),
            "nationality": str(row.get("Nationality", "")),
            "age": str(row.get("Age", "")),
            "overall": str(row.get("Overall", "")),
            "potential": str(row.get("Potential", "")),
            "club": str(row.get("Club", "")),
            "position": str(row.get("Position", "")),
            "jersey_number": str(row.get("Jersey Number", "")),
            "value": str(row.get("Value", "")),
        })
    return results


def get_standings(season: int, competition: str = "Brasileirao") -> list[dict]:
    """Calculate standings for a given season and competition."""
    df = load_all_matches()

    comp_lower = competition.lower()
    season_df = df[
        (df["season"] == season) &
        (df["competition"].str.lower().str.contains(comp_lower, na=False))
    ].dropna(subset=["home_goals", "away_goals"])

    if season_df.empty:
        return []

    teams: dict[str, dict] = {}

    def get_or_create(team_norm: str) -> dict:
        if team_norm not in teams:
            teams[team_norm] = {"team": team_norm, "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "pts": 0}
        return teams[team_norm]

    for _, row in season_df.iterrows():
        h, a = row["home"], row["away"]
        hg, ag = int(row["home_goals"]), int(row["away_goals"])
        ht = get_or_create(h)
        at = get_or_create(a)

        ht["P"] += 1; at["P"] += 1
        ht["GF"] += hg; ht["GA"] += ag
        at["GF"] += ag; at["GA"] += hg

        if hg > ag:
            ht["W"] += 1; ht["pts"] += 3
            at["L"] += 1
        elif ag > hg:
            at["W"] += 1; at["pts"] += 3
            ht["L"] += 1
        else:
            ht["D"] += 1; ht["pts"] += 1
            at["D"] += 1; at["pts"] += 1

    table = sorted(teams.values(), key=lambda x: (x["pts"], x["W"], x["GF"] - x["GA"]), reverse=True)
    for i, row in enumerate(table):
        row["position"] = i + 1
        row["GD"] = row["GF"] - row["GA"]
    return table


def get_biggest_wins(competition: Optional[str] = None, limit: int = 10) -> list[dict]:
    """Get matches with the biggest goal differences."""
    df = load_all_matches().dropna(subset=["home_goals", "away_goals"])

    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]

    df = df.copy()
    df["goal_diff"] = (df["home_goals"] - df["away_goals"]).abs()
    df = df.sort_values("goal_diff", ascending=False).head(limit)

    results = []
    for _, row in df.iterrows():
        results.append({
            "date": str(row["date"])[:10] if pd.notna(row.get("date")) else "unknown",
            "home_team": str(row.get("home_team") or row.get("home", "")),
            "away_team": str(row.get("away_team") or row.get("away", "")),
            "home_goals": int(row["home_goals"]),
            "away_goals": int(row["away_goals"]),
            "goal_difference": int(row["goal_diff"]),
            "competition": str(row.get("competition", "")),
            "season": int(row["season"]) if pd.notna(row.get("season")) else None,
        })
    return results


def get_competition_summary(competition: Optional[str] = None) -> dict:
    """Get summary statistics across the dataset."""
    df = load_all_matches().dropna(subset=["home_goals", "away_goals"])

    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]

    total = len(df)
    if total == 0:
        return {"error": "No matches found"}

    home_wins = (df["home_goals"] > df["away_goals"]).sum()
    away_wins = (df["home_goals"] < df["away_goals"]).sum()
    draws = (df["home_goals"] == df["away_goals"]).sum()
    total_goals = df["home_goals"].sum() + df["away_goals"].sum()

    return {
        "total_matches": total,
        "home_wins": int(home_wins),
        "away_wins": int(away_wins),
        "draws": int(draws),
        "home_win_rate": round(home_wins / total * 100, 1),
        "away_win_rate": round(away_wins / total * 100, 1),
        "draw_rate": round(draws / total * 100, 1),
        "total_goals": int(total_goals),
        "avg_goals_per_match": round(total_goals / total, 2),
        "competitions": df["competition"].value_counts().to_dict(),
        "seasons": sorted(df["season"].dropna().unique().astype(int).tolist()),
    }
