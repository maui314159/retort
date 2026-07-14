from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd

from .normalizers import canonical_team_id, team_display_name, parse_date, set_base_states, _clean, STATES


@dataclass
class DataBundle:
    matches: pd.DataFrame
    matches_unique: pd.DataFrame
    players: pd.DataFrame
    stats: pd.DataFrame
    seasons: dict
    competitions: list


_SOURCE_PRIORITY = {
    "brasileirao": 0,
    "cup": 0,
    "libertadores": 0,
    "hist": 1,
    "brfootball": 2,
}


def _norm_goals(value) -> Optional[int]:
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _load_brasileirao(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    rows = []
    for _, r in df.iterrows():
        hg = _norm_goals(r["home_goal"])
        ag = _norm_goals(r["away_goal"])
        if hg is None or ag is None:
            continue
        home_id = canonical_team_id(r["home_team"])
        away_id = canonical_team_id(r["away_team"])
        rows.append({
            "source": "brasileirao",
            "competition": "Brasileirao",
            "season": int(r["season"]) if not pd.isna(r["season"]) else None,
            "round": int(r["round"]) if not pd.isna(r["round"]) else None,
            "stage": None,
            "date": parse_date(str(r["datetime"])),
            "home_id": home_id,
            "home_name": team_display_name(home_id),
            "home_state": r.get("home_team_state"),
            "away_id": away_id,
            "away_name": team_display_name(away_id),
            "away_state": r.get("away_team_state"),
            "home_goal": hg,
            "away_goal": ag,
            "stadium": None,
        })
    return pd.DataFrame(rows)


def _load_cup(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    rows = []
    for _, r in df.iterrows():
        hg = _norm_goals(r["home_goal"])
        ag = _norm_goals(r["away_goal"])
        if hg is None or ag is None:
            continue
        home_id = canonical_team_id(r["home_team"])
        away_id = canonical_team_id(r["away_team"])
        rnd = r["round"]
        rows.append({
            "source": "cup",
            "competition": "Copa do Brasil",
            "season": int(r["season"]) if not pd.isna(r["season"]) else None,
            "round": int(float(rnd)) if not pd.isna(rnd) and str(rnd).replace(".", "").isdigit() else None,
            "stage": str(rnd) if not pd.isna(rnd) else None,
            "date": parse_date(str(r["datetime"])),
            "home_id": home_id,
            "home_name": team_display_name(home_id),
            "home_state": None,
            "away_id": away_id,
            "away_name": team_display_name(away_id),
            "away_state": None,
            "home_goal": hg,
            "away_goal": ag,
            "stadium": None,
        })
    return pd.DataFrame(rows)


def _load_libertadores(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    rows = []
    for _, r in df.iterrows():
        hg = _norm_goals(r["home_goal"])
        ag = _norm_goals(r["away_goal"])
        if hg is None or ag is None:
            continue
        home_id = canonical_team_id(r["home_team"])
        away_id = canonical_team_id(r["away_team"])
        rows.append({
            "source": "libertadores",
            "competition": "Libertadores",
            "season": int(r["season"]) if not pd.isna(r["season"]) else None,
            "round": None,
            "stage": r.get("stage"),
            "date": parse_date(str(r["datetime"])),
            "home_id": home_id,
            "home_name": team_display_name(home_id),
            "home_state": None,
            "away_id": away_id,
            "away_name": team_display_name(away_id),
            "away_state": None,
            "home_goal": hg,
            "away_goal": ag,
            "stadium": None,
        })
    return pd.DataFrame(rows)


def _load_hist(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    rows = []
    for _, r in df.iterrows():
        hg = _norm_goals(r["Gols_mandante"])
        ag = _norm_goals(r["Gols_visitante"])
        if hg is None or ag is None:
            continue
        home_id = canonical_team_id(r["Equipe_mandante"])
        away_id = canonical_team_id(r["Equipe_visitante"])
        rows.append({
            "source": "hist",
            "competition": "Brasileirao",
            "season": int(r["Ano"]) if not pd.isna(r["Ano"]) else None,
            "round": int(r["Rodada"]) if not pd.isna(r["Rodada"]) else None,
            "stage": None,
            "date": parse_date(str(r["Data"])),
            "home_id": home_id,
            "home_name": team_display_name(home_id),
            "home_state": r.get("Mandante_UF"),
            "away_id": away_id,
            "away_name": team_display_name(away_id),
            "away_state": r.get("Visitante_UF"),
            "home_goal": hg,
            "away_goal": ag,
            "stadium": r.get("Arena"),
        })
    return pd.DataFrame(rows)


def _load_brfootball(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    rows = []
    for _, r in df.iterrows():
        hg = _norm_goals(r["home_goal"])
        ag = _norm_goals(r["away_goal"])
        if hg is None or ag is None:
            continue
        home_id = canonical_team_id(r["home"])
        away_id = canonical_team_id(r["away"])
        tournament = str(r["tournament"]).strip()
        if tournament == "Serie A":
            competition = "Brasileirao"
        elif tournament == "Copa do Brasil":
            competition = "Copa do Brasil"
        else:
            competition = tournament
        d = parse_date(str(r["date"]))
        season = d.year if d else None
        rows.append({
            "source": "brfootball",
            "competition": competition,
            "season": season,
            "round": None,
            "stage": None,
            "date": d,
            "home_id": home_id,
            "home_name": team_display_name(home_id),
            "home_state": None,
            "away_id": away_id,
            "away_name": team_display_name(away_id),
            "away_state": None,
            "home_goal": hg,
            "away_goal": ag,
            "stadium": None,
            "tournament": tournament,
            "home_corner": _norm_goals(r.get("home_corner")),
            "away_corner": _norm_goals(r.get("away_corner")),
            "home_shots": _norm_goals(r.get("home_shots")),
            "away_shots": _norm_goals(r.get("away_shots")),
            "home_attack": _norm_goals(r.get("home_attack")),
            "away_attack": _norm_goals(r.get("away_attack")),
            "total_corners": _norm_goals(r.get("total_corners")),
            "ht_result": r.get("ht_result"),
            "at_result": r.get("at_result"),
        })
    return pd.DataFrame(rows)


_SKILL_COLS = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
    "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
    "Composure", "Marking", "StandingTackle", "SlidingTackle",
]


def _load_players(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    keep = [
        "ID", "Name", "Age", "Nationality", "Overall", "Potential", "Club",
        "Position", "Jersey Number", "Height", "Weight", "Preferred Foot",
    ] + [c for c in _SKILL_COLS if c in df.columns]
    sub = df[keep].copy()
    sub["club_id"] = sub["Club"].apply(
        lambda c: canonical_team_id(c) if isinstance(c, str) else ""
    )
    sub["Overall"] = pd.to_numeric(sub["Overall"], errors="coerce")
    sub["Potential"] = pd.to_numeric(sub["Potential"], errors="coerce")
    sub["Age"] = pd.to_numeric(sub["Age"], errors="coerce")
    sub["Jersey Number"] = pd.to_numeric(sub["Jersey Number"], errors="coerce")
    return sub


def _compute_base_states(base: str) -> dict:
    files_cols = [
        ("Brasileirao_Matches.csv", ["home_team", "away_team"]),
        ("Brazilian_Cup_Matches.csv", ["home_team", "away_team"]),
        ("Libertadores_Matches.csv", ["home_team", "away_team"]),
        ("BR-Football-Dataset.csv", ["home", "away"]),
        ("novo_campeonato_brasileiro.csv", ["Equipe_mandante", "Equipe_visitante"]),
        ("fifa_data.csv", ["Club"]),
    ]
    base_states: dict[str, set] = {}
    for fname, cols in files_cols:
        try:
            df = pd.read_csv(base + fname, usecols=cols)
        except Exception:
            continue
        for col in cols:
            if col not in df.columns:
                continue
            for raw in df[col].dropna().unique():
                cleaned = _clean(raw)
                tokens = cleaned.split()
                if len(tokens) >= 2 and tokens[-1] in STATES:
                    b = " ".join(tokens[:-1])
                    base_states.setdefault(b, set()).add(tokens[-1])
    return base_states


def load_all(data_dir: str = "data/kaggle") -> DataBundle:
    base = data_dir.rstrip("/") + "/"
    set_base_states(_compute_base_states(base))
    frames = [
        _load_brasileirao(base + "Brasileirao_Matches.csv"),
        _load_cup(base + "Brazilian_Cup_Matches.csv"),
        _load_libertadores(base + "Libertadores_Matches.csv"),
        _load_hist(base + "novo_campeonato_brasileiro.csv"),
        _load_brfootball(base + "BR-Football-Dataset.csv"),
    ]
    matches = pd.concat(frames, ignore_index=True, sort=False)
    matches["_pri"] = matches["source"].map(_SOURCE_PRIORITY).fillna(9).astype(int)

    stat_cols = [
        "tournament", "home_corner", "away_corner", "home_shots", "away_shots",
        "home_attack", "away_attack", "total_corners", "ht_result", "at_result",
    ]
    stats = matches[matches["source"] == "brfootball"][
        ["competition", "season", "date", "home_id", "away_id", "home_goal", "away_goal"]
        + [c for c in stat_cols if c in matches.columns]
    ].copy()

    key_cols = ["competition", "season", "home_id", "away_id"]
    sorted_matches = matches.sort_values("_pri")
    unique = sorted_matches.drop_duplicates(key_cols, keep="first").copy()
    sources_agg = (
        matches.groupby(key_cols, as_index=False)["source"]
        .agg(lambda s: sorted(set(s.tolist())))
        .rename(columns={"source": "sources"})
    )
    unique = unique.drop(columns=["_pri"]).merge(
        sources_agg, on=key_cols, how="left"
    )
    matches = matches.drop(columns=["_pri"])

    seasons = {
        comp: sorted(
            int(s) for s in unique.loc[unique["competition"] == comp, "season"]
            .dropna().unique()
        )
        for comp in unique["competition"].unique()
    }
    competitions = sorted(unique["competition"].unique().tolist())

    return DataBundle(
        matches=matches,
        matches_unique=unique,
        players=_load_players(base + "fifa_data.csv"),
        stats=stats,
        seasons=seasons,
        competitions=competitions,
    )
