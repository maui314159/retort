import pandas as pd
import re
from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP
import warnings

warnings.filterwarnings('ignore')

# Initialize the MCP server
mcp = FastMCP("Brazilian Soccer MCP")

def normalize_team_name(name: str) -> str:
    """Normalize team names for consistent matching."""
    if not isinstance(name, str) or pd.isna(name):
        return ""
    # Remove state suffix like "-SP", "-RJ"
    name = re.sub(r'-[A-Z]{2}$', '', str(name).strip())
    # Normalize: lowercase, remove extra spaces
    name = re.sub(r'\s+', ' ', name.lower()).strip()
    return name

def load_data():
    """Load and preprocess all Brazilian soccer datasets."""
    data_dir = Path("data/kaggle")
    
    # 1. Brasileirao Matches
    df1 = pd.read_csv(data_dir / "Brasileirao_Matches.csv")
    df1['competition'] = 'Brasileirão Serie A'
    df1['home_team_norm'] = df1['home_team'].apply(normalize_team_name)
    df1['away_team_norm'] = df1['away_team'].apply(normalize_team_name)
    df1.rename(columns={'datetime': 'date'}, inplace=True)
    
    # 2. Brazilian Cup Matches
    df2 = pd.read_csv(data_dir / "Brazilian_Cup_Matches.csv")
    df2['competition'] = 'Copa do Brasil'
    df2['home_team_norm'] = df2['home_team'].apply(normalize_team_name)
    df2['away_team_norm'] = df2['away_team'].apply(normalize_team_name)
    df2.rename(columns={'datetime': 'date'}, inplace=True)
    
    # 3. Libertadores Matches
    df3 = pd.read_csv(data_dir / "Libertadores_Matches.csv")
    df3['competition'] = 'Copa Libertadores'
    df3['home_team_norm'] = df3['home_team'].apply(normalize_team_name)
    df3['away_team_norm'] = df3['away_team'].apply(normalize_team_name)
    df3.rename(columns={'datetime': 'date'}, inplace=True)
    
    # 4. BR-Football-Dataset
    df4 = pd.read_csv(data_dir / "BR-Football-Dataset.csv")
    df4['competition'] = df4['tournament']
    df4['home_team_norm'] = df4['home'].apply(normalize_team_name)
    df4['away_team_norm'] = df4['away'].apply(normalize_team_name)
    df4['season'] = pd.to_datetime(df4['date']).dt.year
    
    # 5. novo_campeonato_brasileiro
    df5 = pd.read_csv(data_dir / "novo_campeonato_brasileiro.csv", encoding='utf-8')
    df5['competition'] = 'Brasileirão'
    df5['home_team_norm'] = df5['Equipe_mandante'].apply(normalize_team_name)
    df5['away_team_norm'] = df5['Equipe_visitante'].apply(normalize_team_name)
    df5.rename(columns={
        'Ano': 'season', 'Data': 'date', 
        'Equipe_mandante': 'home_team', 'Equipe_visitante': 'away_team',
        'Gols_mandante': 'home_goal', 'Gols_visitante': 'away_goal'
    }, inplace=True)
    
    # Standardize columns for all match dataframes
    cols = ['competition', 'season', 'date', 'home_team', 'away_team', 'home_goal', 'away_goal', 'home_team_norm', 'away_team_norm']
    for df in [df1, df2, df3, df4, df5]:
        for col in cols:
            if col not in df.columns:
                df[col] = None
    
    df_matches = pd.concat([df1[cols], df2[cols], df3[cols], df4[cols], df5[cols]], ignore_index=True)
    
    # Clean up types
    df_matches['home_goal'] = pd.to_numeric(df_matches['home_goal'], errors='coerce')
    df_matches['away_goal'] = pd.to_numeric(df_matches['away_goal'], errors='coerce')
    df_matches['season'] = pd.to_numeric(df_matches['season'], errors='coerce')
    
    # 6. FIFA Data
    df_fifa = pd.read_csv(data_dir / "fifa_data.csv", encoding='utf-8-sig')
    df_fifa['name_norm'] = df_fifa['Name'].apply(lambda x: str(x).lower() if pd.notnull(x) else "")
    df_fifa['club_norm'] = df_fifa['Club'].apply(lambda x: str(x).lower() if pd.notnull(x) else "")
    df_fifa['nationality_norm'] = df_fifa['Nationality'].apply(lambda x: str(x).lower() if pd.notnull(x) else "")
    df_fifa['Overall'] = pd.to_numeric(df_fifa['Overall'], errors='coerce')
    
    return df_matches, df_fifa

# Load data at module level
df_matches, df_fifa = load_data()


@mcp.tool()
def search_matches(
    team: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 20
) -> str:
    """Search for matches based on team, competition, or season.
    
    Args:
        team: Team name to search for (e.g., 'Flamengo', 'Palmeiras')
        competition: Competition name (e.g., 'Brasileirão', 'Copa do Brasil', 'Libertadores')
        season: Year of the season (e.g., 2023)
        limit: Maximum number of results to return (default: 20)
    """
    df = df_matches.copy()
    
    if team:
        team_norm = normalize_team_name(team)
        mask = df['home_team_norm'].str.contains(team_norm, na=False) | df['away_team_norm'].str.contains(team_norm, na=False)
        df = df[mask]
        
    if competition:
        comp_norm = normalize_team_name(competition)
        df = df[df['competition'].str.lower().str.contains(comp_norm, na=False)]
        
    if season:
        df = df[df['season'] == season]
        
    df = df.dropna(subset=['date']).sort_values(by='date', ascending=False).head(limit)
    
    if df.empty:
        return "No matches found matching the criteria."
    
    results = []
    for _, row in df.iterrows():
        h_goal = int(row['home_goal']) if pd.notna(row['home_goal']) else '?'
        a_goal = int(row['away_goal']) if pd.notna(row['away_goal']) else '?'
        season_str = int(row['season']) if pd.notna(row['season']) else 'N/A'
        results.append(
            f"{row['date']} | {row['home_team']} {h_goal} - {a_goal} {row['away_team']} | {row['competition']} (Season: {season_str})"
        )
    
    return "\n".join(results)


@mcp.tool()
def get_team_stats(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None
) -> str:
    """Get statistics for a specific team (wins, draws, losses, goals).
    
    Args:
        team: Team name (required)
        competition: Filter by competition (optional)
        season: Filter by season year (optional)
    """
    df = df_matches.copy()
    team_norm = normalize_team_name(team)
    
    mask = (df['home_team_norm'] == team_norm) | (df['away_team_norm'] == team_norm)
    df = df[mask]
    
    if competition:
        comp_norm = normalize_team_name(competition)
        df = df[df['competition'].str.lower().str.contains(comp_norm, na=False)]
        
    if season:
        df = df[df['season'] == season]
        
    df = df.dropna(subset=['home_goal', 'away_goal'])
    
    if df.empty:
        return f"No match data found for {team} with the given filters."
    
    matches = len(df)
    wins = 0
    draws = 0
    losses = 0
    goals_for = 0
    goals_against = 0
    
    for _, row in df.iterrows():
        is_home = (row['home_team_norm'] == team_norm)
        gf = int(row['home_goal']) if is_home else int(row['away_goal'])
        ga = int(row['away_goal']) if is_home else int(row['home_goal'])
        goals_for += gf
        goals_against += ga
        
        if gf > ga:
            wins += 1
        elif gf == ga:
            draws += 1
        else:
            losses += 1
            
    win_rate = (wins / matches * 100) if matches > 0 else 0
    
    return (
        f"Statistics for {team}:\n"
        f"- Matches: {matches}\n"
        f"- Wins: {wins}\n"
        f"- Draws: {draws}\n"
        f"- Losses: {losses}\n"
        f"- Goals For: {goals_for}\n"
        f"- Goals Against: {goals_against}\n"
        f"- Win Rate: {win_rate:.1f}%"
    )


@mcp.tool()
def get_head_to_head(
    team1: str,
    team2: str,
    competition: Optional[str] = None,
    limit: int = 10
) -> str:
    """Get head-to-head statistics and recent matches between two teams.
    
    Args:
        team1: First team name
        team2: Second team name
        competition: Filter by competition (optional)
        limit: Maximum number of recent matches to show (default: 10)
    """
    df = df_matches.copy()
    t1_norm = normalize_team_name(team1)
    t2_norm = normalize_team_name(team2)
    
    mask = (
        ((df['home_team_norm'] == t1_norm) & (df['away_team_norm'] == t2_norm)) |
        ((df['home_team_norm'] == t2_norm) & (df['away_team_norm'] == t1_norm))
    )
    df = df[mask]
    
    if competition:
        comp_norm = normalize_team_name(competition)
        df = df[df['competition'].str.lower().str.contains(comp_norm, na=False)]
        
    df = df.dropna(subset=['home_goal', 'away_goal'])
    
    if df.empty:
        return f"No matches found between {team1} and {team2}."
    
    t1_wins = 0
    t2_wins = 0
    draws = 0
    
    for _, row in df.iterrows():
        if row['home_team_norm'] == t1_norm:
            if row['home_goal'] > row['away_goal']:
                t1_wins += 1
            elif row['home_goal'] < row['away_goal']:
                t2_wins += 1
            else:
                draws += 1
        else:
            if row['away_goal'] > row['home_goal']:
                t1_wins += 1
            elif row['away_goal'] < row['home_goal']:
                t2_wins += 1
            else:
                draws += 1
                
    total = len(df)
    
    recent = df.dropna(subset=['date']).sort_values(by='date', ascending=False).head(limit)
    recent_matches = []
    for _, row in recent.iterrows():
        recent_matches.append(
            f"{row['date']} | {row['home_team']} {int(row['home_goal'])} - {int(row['away_goal'])} {row['away_team']} | {row['competition']}"
        )
    
    return (
        f"Head-to-Head: {team1} vs {team2}\n"
        f"Total Matches: {total}\n"
        f"- {team1} wins: {t1_wins}\n"
        f"- {team2} wins: {t2_wins}\n"
        f"- Draws: {draws}\n\n"
        f"Recent Matches:\n" + "\n".join(recent_matches)
    )


@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 10
) -> str:
    """Search for players by name, nationality, club, position, or minimum overall rating.
    
    Args:
        name: Player name (partial match allowed)
        nationality: Player nationality (e.g., 'Brazil', 'Argentina')
        club: Club name (partial match allowed)
        position: Playing position (e.g., 'ST', 'GK', 'CAM')
        min_overall: Minimum overall rating (e.g., 85)
        limit: Maximum number of results to return (default: 10)
    """
    df = df_fifa.copy()
    
    if name:
        name_norm = name.lower()
        df = df[df['name_norm'].str.contains(name_norm, na=False)]
        
    if nationality:
        nat_norm = nationality.lower()
        df = df[df['nationality_norm'].str.contains(nat_norm, na=False)]
        
    if club:
        club_norm = club.lower()
        df = df[df['club_norm'].str.contains(club_norm, na=False)]
        
    if position:
        pos_norm = position.upper()
        df = df[df['Position'].str.contains(pos_norm, na=False)]
        
    if min_overall:
        df = df[df['Overall'] >= min_overall]
        
    df = df.dropna(subset=['Overall']).sort_values(by='Overall', ascending=False).head(limit)
    
    if df.empty:
        return "No players found matching the criteria."
    
    results = []
    for _, row in df.iterrows():
        results.append(
            f"{row['Name']} | Overall: {int(row['Overall'])} | Position: {row['Position']} | Club: {row['Club']} | Nationality: {row['Nationality']}"
        )
        
    return "\n".join(results)


@mcp.tool()
def get_competition_standings(
    competition: str,
    season: int
) -> str:
    """Calculate and return the standings for a specific competition and season.
    
    Args:
        competition: Competition name (e.g., 'Brasileirão Serie A')
        season: Year of the season (e.g., 2023)
    """
    df = df_matches.copy()
    comp_norm = normalize_team_name(competition)
    
    df = df[df['competition'].str.lower().str.contains(comp_norm, na=False)]
    df = df[df['season'] == season]
    df = df.dropna(subset=['home_goal', 'away_goal', 'home_team', 'away_team'])
    
    if df.empty:
        return f"No match data found for {competition} in season {season}."
    
    stats = {}
    for _, row in df.iterrows():
        h_team = str(row['home_team']).strip()
        a_team = str(row['away_team']).strip()
        h_goal = int(row['home_goal'])
        a_goal = int(row['away_goal'])
        
        for team in [h_team, a_team]:
            if team not in stats:
                stats[team] = {'matches': 0, 'wins': 0, 'draws': 0, 'losses': 0, 'gf': 0, 'ga': 0, 'pts': 0}
                
        stats[h_team]['matches'] += 1
        stats[a_team]['matches'] += 1
        stats[h_team]['gf'] += h_goal
        stats[h_team]['ga'] += a_goal
        stats[a_team]['gf'] += a_goal
        stats[a_team]['ga'] += h_goal
        
        if h_goal > a_goal:
            stats[h_team]['wins'] += 1
            stats[h_team]['pts'] += 3
            stats[a_team]['losses'] += 1
        elif h_goal < a_goal:
            stats[a_team]['wins'] += 1
            stats[a_team]['pts'] += 3
            stats[h_team]['losses'] += 1
        else:
            stats[h_team]['draws'] += 1
            stats[h_team]['pts'] += 1
            stats[a_team]['draws'] += 1
            stats[a_team]['pts'] += 1
            
    standings = []
    for team, s in stats.items():
        gd = s['gf'] - s['ga']
        standings.append((team, s['pts'], s['matches'], s['wins'], s['draws'], s['losses'], s['gf'], s['ga'], gd))
        
    # Sort by points (desc), then goal difference (desc), then goals for (desc)
    standings.sort(key=lambda x: (x[1], x[8], x[6]), reverse=True)
    
    results = [f"Standings for {competition} ({season}):"]
    results.append(f"{'Pos':<4} | {'Team':<25} | {'Pts':<4} | {'P':<3} | {'W':<3} | {'D':<3} | {'L':<3} | {'GF':<3} | {'GA':<3} | {'GD':<4}")
    results.append("-" * 80)
    
    for i, (team, pts, matches, w, d, l, gf, ga, gd) in enumerate(standings, 1):
        results.append(f"{i:<4} | {team:<25} | {pts:<4} | {matches:<3} | {w:<3} | {d:<3} | {l:<3} | {gf:<3} | {ga:<3} | {gd:<4}")
        
    return "\n".join(results)


if __name__ == "__main__":
    mcp.run()
