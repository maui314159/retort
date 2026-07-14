from mcp.server.fastmcp import FastMCP
import pandas as pd
from data_loader import get_all_matches, load_fifa_data, normalize_team_name

mcp = FastMCP("BrazilianSoccer")

@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    season: int | None = None,
    competition: str | None = None,
    limit: int = 20
) -> str:
    """Search for matches based on team, opponent, season, or competition."""
    df = get_all_matches()
    
    if team:
        team_norm = normalize_team_name(team)
        mask = (df['home_team_norm'].str.contains(team_norm, na=False)) | \
               (df['away_team_norm'].str.contains(team_norm, na=False))
        df = df[mask]
        
    if opponent:
        opp_norm = normalize_team_name(opponent)
        mask = (df['home_team_norm'].str.contains(opp_norm, na=False)) | \
               (df['away_team_norm'].str.contains(opp_norm, na=False))
        df = df[mask]
        
    if season is not None:
        df = df[df['season'] == season]
        
    if competition:
        comp_norm = competition.lower()
        if "brasileir" in comp_norm:
            mask = df['competition'].str.lower().str.contains("brasileir", na=False) | \
                   df['competition'].str.lower().str.contains("serie a", na=False)
            df = df[mask]
        else:
            df = df[df['competition'].str.lower().str.contains(comp_norm, na=False)]
        
    df = df.sort_values('datetime', ascending=False).head(limit)
    
    results = []
    for _, row in df.iterrows():
        date_str = str(row['datetime'].date()) if pd.notna(row['datetime']) else "Unknown"
        h_goals = int(row['home_goal']) if pd.notna(row['home_goal']) else 0
        a_goals = int(row['away_goal']) if pd.notna(row['away_goal']) else 0
        season_str = str(int(row['season'])) if pd.notna(row['season']) else "Unknown"
        results.append(f"- {date_str}: {row['home_team']} {h_goals}-{a_goals} {row['away_team']} ({row['competition']}, Season {season_str})")
        
    if not results:
        return "No matches found matching the criteria."
        
    return "\n".join(results)

@mcp.tool()
def get_team_statistics(team: str, season: int | None = None, competition: str | None = None) -> str:
    """Get win/loss/draw records, goals scored/conceded, and win rate for a team."""
    df = get_all_matches()
    team_norm = normalize_team_name(team)
    
    if season is not None:
        df = df[df['season'] == season]
    if competition:
        comp_norm = competition.lower()
        if "brasileir" in comp_norm:
            mask = df['competition'].str.lower().str.contains("brasileir", na=False) | \
                   df['competition'].str.lower().str.contains("serie a", na=False)
            df = df[mask]
        else:
            df = df[df['competition'].str.lower().str.contains(comp_norm, na=False)]
        
    home_mask = df['home_team_norm'].str.contains(team_norm, na=False)
    away_mask = df['away_team_norm'].str.contains(team_norm, na=False)
    team_matches = df[home_mask | away_mask]
    
    if team_matches.empty:
        return f"No match data found for {team}."
        
    wins = 0
    draws = 0
    losses = 0
    goals_for = 0
    goals_against = 0
    
    for _, row in team_matches.iterrows():
        is_home = home_mask.loc[row.name]
        team_goals = int(row['home_goal']) if pd.notna(row['home_goal']) and is_home else int(row['away_goal']) if pd.notna(row['away_goal']) else 0
        opp_goals = int(row['away_goal']) if pd.notna(row['away_goal']) and is_home else int(row['home_goal']) if pd.notna(row['home_goal']) else 0
        
        goals_for += team_goals
        goals_against += opp_goals
        
        if team_goals > opp_goals:
            wins += 1
        elif team_goals == opp_goals:
            draws += 1
        else:
            losses += 1
            
    total_matches = len(team_matches)
    win_rate = (wins / total_matches) * 100 if total_matches > 0 else 0
    
    comp_str = f" - {competition}" if competition else ""
    season_str = f" (Season {season})" if season is not None else ""
    
    return f"""{team} Statistics{season_str}{comp_str}:
- Matches: {total_matches}
- Wins: {wins}, Draws: {draws}, Losses: {losses}
- Goals For: {goals_for}, Goals Against: {goals_against}
- Win Rate: {win_rate:.1f}%"""

@mcp.tool()
def get_head_to_head(team1: str, team2: str, limit: int = 10) -> str:
    """Get head-to-head record and recent matches between two teams."""
    df = get_all_matches()
    t1_norm = normalize_team_name(team1)
    t2_norm = normalize_team_name(team2)
    
    mask = (
        (df['home_team_norm'].str.contains(t1_norm, na=False) & df['away_team_norm'].str.contains(t2_norm, na=False)) |
        (df['home_team_norm'].str.contains(t2_norm, na=False) & df['away_team_norm'].str.contains(t1_norm, na=False))
    )
    
    h2h_matches = df[mask].sort_values('datetime', ascending=False).head(limit)
    
    if h2h_matches.empty:
        return f"No head-to-head matches found between {team1} and {team2}."
        
    t1_wins = 0
    t2_wins = 0
    draws = 0
    
    results = []
    for _, row in h2h_matches.iterrows():
        h_norm = row['home_team_norm']
        a_norm = row['away_team_norm']
        h_goals = int(row['home_goal']) if pd.notna(row['home_goal']) else 0
        a_goals = int(row['away_goal']) if pd.notna(row['away_goal']) else 0
        
        if h_goals > a_goals:
            if t1_norm in h_norm: t1_wins += 1
            else: t2_wins += 1
        elif h_goals < a_goals:
            if t1_norm in a_norm: t1_wins += 1
            else: t2_wins += 1
        else:
            draws += 1
            
        date_str = str(row['datetime'].date()) if pd.notna(row['datetime']) else 'Unknown'
        results.append(f"- {date_str}: {row['home_team']} {h_goals}-{a_goals} {row['away_team']} ({row['competition']})")
        
    return f"""Head-to-Head: {team1} vs {team2}
Total matches in dataset: {len(h2h_matches)}
{team1} wins: {t1_wins}
{team2} wins: {t2_wins}
Draws: {draws}

Recent matches:
""" + "\n".join(results)

@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    min_rating: int | None = None,
    position: str | None = None,
    limit: int = 10
) -> str:
    """Search for players in the FIFA database by name, nationality, club, rating, or position."""
    df = load_fifa_data()
    
    if name:
        name_norm = name.lower()
        df = df[df['Name'].str.lower().str.contains(name_norm, na=False)]
        
    if nationality:
        nat_norm = nationality.lower()
        df = df[df['Nationality'].str.lower().str.contains(nat_norm, na=False)]
        
    if club:
        club_norm = normalize_team_name(club)
        df = df[df['Club'].apply(normalize_team_name).str.contains(club_norm, na=False)]
        
    if min_rating is not None:
        df = df[df['Overall'] >= min_rating]
        
    if position:
        pos_norm = position.upper()
        df = df[df['Position'].str.contains(pos_norm, na=False)]
        
    df = df.sort_values('Overall', ascending=False).head(limit)
    
    if df.empty:
        return "No players found matching the criteria."
        
    results = []
    for _, row in df.iterrows():
        results.append(f"- {row['Name']} (Overall: {int(row['Overall'])}, Position: {row['Position']}, Club: {row['Club']}, Nationality: {row['Nationality']})")
        
    return "Top matching players:\n" + "\n".join(results)

@mcp.tool()
def get_competition_standings(competition: str, season: int) -> str:
    """Calculate and return the standings for a specific competition and season."""
    df = get_all_matches()
    comp_norm = competition.lower()
    # Map common names
    if "brasileir" in comp_norm:
        mask = df['competition'].str.lower().str.contains("brasileir", na=False) | \
               df['competition'].str.lower().str.contains("serie a", na=False)
        df = df[mask]
    else:
        df = df[df['competition'].str.lower().str.contains(comp_norm, na=False)]
    df = df[df['season'] == season]
    
    if df.empty:
        return f"No match data found for {competition} in {season}."
        
    standings = {}
    for _, row in df.iterrows():
        h_team = row['home_team_norm'].title()
        a_team = row['away_team_norm'].title()
        h_goals = int(row['home_goal']) if pd.notna(row['home_goal']) else 0
        a_goals = int(row['away_goal']) if pd.notna(row['away_goal']) else 0
        
        for team in [h_team, a_team]:
            if team not in standings:
                standings[team] = {'played': 0, 'won': 0, 'drawn': 0, 'lost': 0, 'gf': 0, 'ga': 0, 'pts': 0}
                
        standings[h_team]['played'] += 1
        standings[a_team]['played'] += 1
        standings[h_team]['gf'] += h_goals
        standings[h_team]['ga'] += a_goals
        standings[a_team]['gf'] += a_goals
        standings[a_team]['ga'] += h_goals
        
        if h_goals > a_goals:
            standings[h_team]['won'] += 1
            standings[h_team]['pts'] += 3
            standings[a_team]['lost'] += 1
        elif h_goals < a_goals:
            standings[a_team]['won'] += 1
            standings[a_team]['pts'] += 3
            standings[h_team]['lost'] += 1
        else:
            standings[h_team]['drawn'] += 1
            standings[h_team]['pts'] += 1
            standings[a_team]['drawn'] += 1
            standings[a_team]['pts'] += 1
            
    sorted_teams = sorted(
        standings.items(),
        key=lambda x: (x[1]['pts'], x[1]['gf'] - x[1]['ga'], x[1]['gf']),
        reverse=True
    )
    
    results = [f"{competition} {season} Standings:"]
    for i, (team, stats) in enumerate(sorted_teams, 1):
        gd = stats['gf'] - stats['ga']
        gd_str = f"+{gd}" if gd > 0 else str(gd)
        results.append(f"{i}. {team} - {stats['pts']} pts ({stats['won']}W, {stats['drawn']}D, {stats['lost']}L, GF: {stats['gf']}, GA: {stats['ga']}, GD: {gd_str})")
        
    return "\n".join(results)

@mcp.tool()
def get_statistical_analysis(metric: str, competition: str | None = None, season: int | None = None) -> str:
    """Get aggregated statistics like average goals, biggest wins, or home win rate."""
    df = get_all_matches()
    
    if competition:
        comp_norm = competition.lower()
        df = df[df['competition'].str.lower().str.contains(comp_norm, na=False)]
    if season is not None:
        df = df[df['season'] == season]
        
    if df.empty:
        return "No match data found for the specified criteria."
        
    metric = metric.lower()
    
    if "average goals" in metric or "goals per match" in metric:
        total_goals = (df['home_goal'].fillna(0) + df['away_goal'].fillna(0)).sum()
        avg_goals = total_goals / len(df)
        return f"Average goals per match: {avg_goals:.2f} (Total matches: {len(df)})"
        
    elif "home win" in metric or "home record" in metric:
        home_wins = (df['home_goal'] > df['away_goal']).sum()
        home_win_rate = (home_wins / len(df)) * 100
        return f"Home win rate: {home_win_rate:.1f}% ({home_wins} wins out of {len(df)} matches)"
        
    elif "biggest win" in metric or "biggest victory" in metric:
        df['goal_diff'] = (df['home_goal'].fillna(0) - df['away_goal'].fillna(0)).abs()
        biggest = df.sort_values('goal_diff', ascending=False).head(5)
        results = ["Biggest victories:"]
        for _, row in biggest.iterrows():
            diff = int(row['goal_diff'])
            date_str = str(row['datetime'].date()) if pd.notna(row['datetime']) else 'Unknown'
            h_goals = int(row['home_goal']) if pd.notna(row['home_goal']) else 0
            a_goals = int(row['away_goal']) if pd.notna(row['away_goal']) else 0
            results.append(f"- {date_str}: {row['home_team']} {h_goals}-{a_goals} {row['away_team']} ({row['competition']}, diff: {diff})")
        return "\n".join(results)
        
    return f"Metric '{metric}' not recognized. Try 'average goals', 'home win rate', or 'biggest win'."