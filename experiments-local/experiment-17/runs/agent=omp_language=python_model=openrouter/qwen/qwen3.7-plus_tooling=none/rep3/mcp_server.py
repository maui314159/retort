from mcp.server.fastmcp import FastMCP
import pandas as pd
from pathlib import Path
from data_loader import load_data, normalize_team
import json

mcp = FastMCP("Brazilian Soccer MCP")

# Load data at startup
DATA_DIR = Path("data/kaggle")
df_matches, df_players = load_data(DATA_DIR)

@mcp.tool()
def search_matches(
    team: str | None = None,
    home_team: str | None = None,
    away_team: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 20
) -> str:
    """Search for matches based on various criteria."""
    df = df_matches.copy()
    
    if team:
        team_norm = normalize_team(team)
        df = df[(df["home_team_norm"].str.contains(team_norm, na=False)) | (df["away_team_norm"].str.contains(team_norm, na=False))]
        
    if home_team:
        team_norm = normalize_team(home_team)
        df = df[df["home_team_norm"].str.contains(team_norm, na=False)]
        
    if away_team:
        team_norm = normalize_team(away_team)
        df = df[df["away_team_norm"].str.contains(team_norm, na=False)]
        
    if competition:
        comp_norm = normalize_team(competition)
        df = df[df["competition"].str.lower().str.contains(comp_norm, na=False)]
        
    if season:
        df = df[df["season"] == season]
        
    if start_date:
        df = df[df["date"] >= pd.to_datetime(start_date)]
        
    if end_date:
        df = df[df["date"] <= pd.to_datetime(end_date)]
        
    df = df.sort_values("date", ascending=False).head(limit)
    
    results = []
    for _, row in df.iterrows():
        date_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "Unknown"
        results.append(
            f"{date_str}: {row['home_team']} {row['home_goal']} - {row['away_goal']} {row['away_team']} "
            f"({row['competition']}, {row['round_stage']})"
        )
    
    return json.dumps(results, indent=2)

@mcp.tool()
def get_team_stats(team: str, season: int | None = None, competition: str | None = None) -> str:
    """Get statistics for a specific team."""
    team_norm = normalize_team(team)
    df = df_matches.copy()
    
    df = df[(df["home_team_norm"].str.contains(team_norm, na=False)) | (df["away_team_norm"].str.contains(team_norm, na=False))]
    
    if season:
        df = df[df["season"] == season]
    if competition:
        comp_norm = normalize_team(competition)
        df = df[df["competition"].str.lower().str.contains(comp_norm, na=False)]
        
    if df.empty:
        return json.dumps({"error": "No matches found for this team"})
        
    wins = 0
    draws = 0
    losses = 0
    goals_for = 0
    goals_against = 0
    
    for _, row in df.iterrows():
        is_home = team_norm in row["home_team_norm"]
        team_goals = row["home_goal"] if is_home else row["away_goal"]
        opp_goals = row["away_goal"] if is_home else row["home_goal"]
        
        goals_for += team_goals
        goals_against += opp_goals
        
        if team_goals > opp_goals:
            wins += 1
        elif team_goals == opp_goals:
            draws += 1
        else:
            losses += 1
            
    matches = len(df)
    win_rate = (wins / matches * 100) if matches > 0 else 0
    
    stats = {
        "team": team,
        "matches": int(matches),
        "wins": int(wins),
        "draws": int(draws),
        "losses": int(losses),
        "goals_for": int(goals_for),
        "goals_against": int(goals_against),
        "win_rate": f"{win_rate:.1f}%"
    }
    
    return json.dumps(stats, indent=2)

@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 20
) -> str:
    """Search for players in the FIFA database."""
    df = df_players.copy()
    
    if name:
        name_norm = normalize_team(name)
        df = df[df["Name_norm"].str.contains(name_norm, na=False)]
        
    if nationality:
        nat_norm = normalize_team(nationality)
        df = df[df["Nationality_norm"].str.contains(nat_norm, na=False)]
        
    if club:
        club_norm = normalize_team(club)
        df = df[df["Club_norm"].str.contains(club_norm, na=False)]
        
    if position:
        pos_norm = normalize_team(position)
        df = df[df["Position"].str.lower().str.contains(pos_norm, na=False)]
        
    if min_overall:
        df = df[df["Overall"] >= min_overall]
        
    df = df.sort_values("Overall", ascending=False).head(limit)
    
    results = []
    for _, row in df.iterrows():
        results.append(
            f"{row['Name']} - Overall: {row['Overall']}, Position: {row['Position']}, "
            f"Club: {row['Club']}, Nationality: {row['Nationality']}"
        )
        
    return json.dumps(results, indent=2)

@mcp.tool()
def get_head_to_head(team1: str, team2: str, season: int | None = None) -> str:
    """Get head-to-head record between two teams."""
    t1_norm = normalize_team(team1)
    t2_norm = normalize_team(team2)
    
    df = df_matches.copy()
    
    mask_t1_home = df["home_team_norm"].str.contains(t1_norm, na=False)
    mask_t1_away = df["away_team_norm"].str.contains(t1_norm, na=False)
    mask_t2_home = df["home_team_norm"].str.contains(t2_norm, na=False)
    mask_t2_away = df["away_team_norm"].str.contains(t2_norm, na=False)
    
    df = df[(mask_t1_home & mask_t2_away) | (mask_t2_home & mask_t1_away)]
    
    if season:
        df = df[df["season"] == season]
        
    if df.empty:
        return json.dumps({"error": "No matches found between these teams"})
        
    t1_wins = 0
    t2_wins = 0
    draws = 0
    
    matches = []
    for _, row in df.iterrows():
        is_t1_home = t1_norm in row["home_team_norm"]
        t1_goals = row["home_goal"] if is_t1_home else row["away_goal"]
        t2_goals = row["away_goal"] if is_t1_home else row["home_goal"]
        
        if t1_goals > t2_goals:
            t1_wins += 1
        elif t1_goals < t2_goals:
            t2_wins += 1
        else:
            draws += 1
            
        date_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "Unknown"
        matches.append(
            f"{date_str}: {row['home_team']} {row['home_goal']} - {row['away_goal']} {row['away_team']} ({row['competition']})"
        )
        
    result = {
        "team1": team1,
        "team2": team2,
        f"{team1}_wins": int(t1_wins),
        f"{team2}_wins": int(t2_wins),
        "draws": int(draws),
        "recent_matches": matches[:10]
    }
    
    return json.dumps(result, indent=2)

@mcp.tool()
def get_competition_standings(competition: str, season: int) -> str:
    """Calculate standings for a competition and season."""
    comp_norm = normalize_team(competition)
    df = df_matches.copy()
    df = df[df["competition"].str.lower().str.contains(comp_norm, na=False)]
    df = df[df["season"] == season]
    
    if df.empty:
        return json.dumps({"error": "No matches found for this competition and season"})
        
    standings = {}
    
    for _, row in df.iterrows():
        for is_home, team, team_norm, goals, opp_goals in [
            (True, row["home_team"], row["home_team_norm"], row["home_goal"], row["away_goal"]),
            (False, row["away_team"], row["away_team_norm"], row["away_goal"], row["home_goal"])
        ]:
            if team_norm not in standings:
                standings[team_norm] = {"team": team, "played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "pts": 0}
                
            standings[team_norm]["played"] += 1
            standings[team_norm]["gf"] += goals
            standings[team_norm]["ga"] += opp_goals
            
            if goals > opp_goals:
                standings[team_norm]["won"] += 1
                standings[team_norm]["pts"] += 3
            elif goals == opp_goals:
                standings[team_norm]["drawn"] += 1
                standings[team_norm]["pts"] += 1
            else:
                standings[team_norm]["lost"] += 1
                
    sorted_standings = sorted(
        standings.values(),
        key=lambda x: (x["pts"], x["gf"] - x["ga"], x["gf"]),
        reverse=True
    )
    
    results = []
    for i, s in enumerate(sorted_standings, 1):
        results.append(
            f"{i}. {s['team']} - {s['pts']} pts ({s['won']}W, {s['drawn']}D, {s['lost']}L), GF: {s['gf']}, GA: {s['ga']}"
        )
        
    return json.dumps(results, indent=2)

@mcp.tool()
def get_match_statistics() -> str:
    """Get aggregate match statistics across all data."""
    df = df_matches.copy()
    
    total_matches = len(df)
    total_goals = int(df["home_goal"].sum() + df["away_goal"].sum())
    avg_goals = total_goals / total_matches if total_matches > 0 else 0
    
    home_wins = len(df[df["home_goal"] > df["away_goal"]])
    home_win_rate = (home_wins / total_matches * 100) if total_matches > 0 else 0
    
    df["goal_diff"] = (df["home_goal"] - df["away_goal"]).abs()
    biggest_wins = df.sort_values("goal_diff", ascending=False).head(5)
    
    biggest_results = []
    for _, row in biggest_wins.iterrows():
        date_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "Unknown"
        biggest_results.append(
            f"{date_str}: {row['home_team']} {row['home_goal']} - {row['away_goal']} {row['away_team']} ({row['competition']})"
        )
        
    stats = {
        "total_matches": int(total_matches),
        "total_goals": int(total_goals),
        "average_goals_per_match": round(avg_goals, 2),
        "home_win_rate": f"{home_win_rate:.1f}%",
        "biggest_wins": biggest_results
    }
    
    return json.dumps(stats, indent=2)

if __name__ == "__main__":
    mcp.run()
