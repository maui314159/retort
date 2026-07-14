"""
Data loader for Brazilian soccer datasets.
Handles CSV parsing, team name normalization, and date format handling.
"""

import pandas as pd
import os
from pathlib import Path
from typing import Optional

# Known team name variations for normalization
TEAM_NAME_MAP = {
    # Variations with state suffixes
    "Palmeiras-SP": "Palmeiras",
    "Flamengo-RJ": "Flamengo",
    "Corinthians-SP": "Corinthians",
    "São Paulo-SP": "São Paulo",
    "Santos-SP": "Santos",
    "Vasco da Gama-RJ": "Vasco da Gama",
    "Fluminense-RJ": "Fluminense",
    "Botafogo-RJ": "Botafogo",
    "Grêmio-RS": "Grêmio",
    "Internacional-RS": "Internacional",
    "Athletico-PR": "Athletico-PR",
    "Coritiba-PR": "Coritiba",
    "Bahia-BA": "Bahia",
    "Vitória-BA": "Vitória",
    "Sport-PE": "Sport Recife",
    "Nautico-PE": "Náutico",
    "Fortaleza-CE": "Fortaleza",
    "Ceará-CE": "Ceará",
    "Atlético-MG": "Atlético Mineiro",
    "Cruzeiro-MG": "Cruzeiro",
    "América-MG": "América Mineiro",
    "Goiás-GO": "Goiás",
    "Atlético-GO": "Atlético Goianiense",
    "Figueirense-SC": "Figueirense",
    "Criciúma-SC": "Criciúma",
    "Juventude-RS": "Juventude",
    "Ponte Preta-SP": "Ponte Preta",
    "Portuguesa-SP": "Portuguesa",
    "São Caetano-SP": "São Caetano",
    "Paraná-PR": "Paraná",
    "Paysandu-PA": "Paysandu",
    # Common variations
    "Athletico Paranaense": "Athletico-PR",
    "Atlético Paranaense": "Athletico-PR",
    "Atletico-PR": "Athletico-PR",
    "Corinthians": "Corinthians",
    "São Paulo": "São Paulo",
    "Santos": "Santos",
    "Flamengo": "Flamengo",
    "Vasco": "Vasco da Gama",
    "Fluminense": "Fluminense",
    "Botafogo": "Botafogo",
    "Grêmio": "Grêmio",
    "Internacional": "Internacional",
    "Atlético Mineiro": "Atlético Mineiro",
    "Cruzeiro": "Cruzeiro",
    "Sport": "Sport Recife",
    "Sport Recife": "Sport Recife",
    "Bahia": "Bahia",
    "Vitória": "Vitória",
    "Fortaleza": "Fortaleza",
    "Ceará": "Ceará",
    "Goiás": "Goiás",
    "Avaí": "Avaí",
    "Juventude": "Juventude",
    "Criciúma": "Criciúma",
    "Figueirense": "Figueirense",
    "Ponte Preta": "Ponte Preta",
    "Portuguesa": "Portuguesa",
    "América Mineiro": "América Mineiro",
    "América-MG": "América Mineiro",
    "EC Bahia": "Bahia",
    "Atlético-MG": "Atlético Mineiro",
}

def normalize_team_name(name: str) -> str:
    """Normalize team names to handle variations."""
    if pd.isna(name):
        return ""

    # Strip whitespace and common suffixes
    name = name.strip()

    # Check direct mapping
    if name in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[name]

    # Remove state suffix pattern like "-SP", "-RJ", etc.
    import re
    name_no_suffix = re.sub(r'\s*-\s*[A-Z]{2}$', '', name)

    # Check if the cleaned name maps to something
    if name_no_suffix in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[name_no_suffix]

    # Return cleaned name as fallback
    return name_no_suffix if name_no_suffix != name else name

class SoccerDataLoader:
    """Loads and manages all Brazilian soccer datasets."""

    def __init__(self, data_dir: str = "data/kaggle"):
        self.data_dir = Path(data_dir)
        self.brasileirao_matches: Optional[pd.DataFrame] = None
        self.brazilian_cup_matches: Optional[pd.DataFrame] = None
        self.libertadores_matches: Optional[pd.DataFrame] = None
        self.br_football: Optional[pd.DataFrame] = None
        self.historical_brasileirao: Optional[pd.DataFrame] = None
        self.fifa_players: Optional[pd.DataFrame] = None

    def load_all(self):
        """Load all datasets."""
        self.load_brasileirao_matches()
        self.load_brazilian_cup_matches()
        self.load_libertadores_matches()
        self.load_br_football_dataset()
        self.load_historical_brasileirao()
        self.load_fifa_players()

    def load_brasileirao_matches(self):
        """Load Brasileirão matches (2012+ format)."""
        file_path = self.data_dir / "Brasileirao_Matches.csv"
        if not file_path.exists():
            return

        df = pd.read_csv(file_path)
        df['competition'] = 'Brasileirão'

        # Standardize column names and convert types
        if 'home_goal' in df.columns:
            df = df.rename(columns={'home_goal': 'home_goals', 'away_goal': 'away_goals'})
        df['home_goals'] = pd.to_numeric(df['home_goals'], errors='coerce').fillna(0).astype(int)
        df['away_goals'] = pd.to_numeric(df['away_goals'], errors='coerce').fillna(0).astype(int)

        # Normalize team names
        df['home_team_norm'] = df['home_team'].apply(normalize_team_name)
        df['away_team_norm'] = df['away_team'].apply(normalize_team_name)

        # Parse datetime
        df['match_date'] = pd.to_datetime(df['datetime'], errors='coerce')

        self.brasileirao_matches = df

    def load_brazilian_cup_matches(self):
        """Load Copa do Brasil matches."""
        file_path = self.data_dir / "Brazilian_Cup_Matches.csv"
        if not file_path.exists():
            return

        df = pd.read_csv(file_path)
        df['competition'] = 'Copa do Brasil'

        # Standardize column names and convert types
        if 'home_goal' in df.columns:
            df = df.rename(columns={'home_goal': 'home_goals', 'away_goal': 'away_goals'})
        df['home_goals'] = pd.to_numeric(df['home_goals'], errors='coerce').fillna(0).astype(int)
        df['away_goals'] = pd.to_numeric(df['away_goals'], errors='coerce').fillna(0).astype(int)

        # Normalize team names
        df['home_team_norm'] = df['home_team'].apply(normalize_team_name)
        df['away_team_norm'] = df['away_team'].apply(normalize_team_name)

        # Parse datetime
        df['match_date'] = pd.to_datetime(df['datetime'], errors='coerce')

        self.brazilian_cup_matches = df

    def load_libertadores_matches(self):
        """Load Copa Libertadores matches."""
        file_path = self.data_dir / "Libertadores_Matches.csv"
        if not file_path.exists():
            return

        df = pd.read_csv(file_path)
        df['competition'] = 'Copa Libertadores'

        # Standardize column names and convert types
        if 'home_goal' in df.columns:
            df = df.rename(columns={'home_goal': 'home_goals', 'away_goal': 'away_goals'})
        df['home_goals'] = pd.to_numeric(df['home_goals'], errors='coerce').fillna(0).astype(int)
        df['away_goals'] = pd.to_numeric(df['away_goals'], errors='coerce').fillna(0).astype(int)

        # Normalize team names
        df['home_team_norm'] = df['home_team'].apply(normalize_team_name)
        df['away_team_norm'] = df['away_team'].apply(normalize_team_name)

        # Parse datetime
        df['match_date'] = pd.to_datetime(df['datetime'], errors='coerce')

        self.libertadores_matches = df

    def load_br_football_dataset(self):
        """Load extended match statistics dataset."""
        file_path = self.data_dir / "BR-Football-Dataset.csv"
        if not file_path.exists():
            return

        df = pd.read_csv(file_path)

        # Rename columns to match standard format
        df = df.rename(columns={
            'home': 'home_team',
            'away': 'away_team',
            'date': 'match_date_str',
            'time': 'match_time'
        })

        df['competition'] = df['tournament']

        # Convert goal columns to numeric
        df['home_goals'] = pd.to_numeric(df['home_goal'], errors='coerce').fillna(0).astype(int)
        df['away_goals'] = pd.to_numeric(df['away_goal'], errors='coerce').fillna(0).astype(int)

        # Normalize team names
        df['home_team_norm'] = df['home_team'].apply(normalize_team_name)
        df['away_team_norm'] = df['away_team'].apply(normalize_team_name)

        # Parse date
        df['match_date'] = pd.to_datetime(df['match_date_str'], errors='coerce')

        self.br_football = df

    def load_historical_brasileirao(self):
        """Load historical Brasileirão data (2003-2019)."""
        file_path = self.data_dir / "novo_campeonato_brasileiro.csv"
        if not file_path.exists():
            return

        df = pd.read_csv(file_path)

        # Rename columns to match standard format
        df = df.rename(columns={
            'Equipe_mandante': 'home_team',
            'Equipe_visitante': 'away_team',
            'Gols_mandante': 'home_goals',
            'Gols_visitante': 'away_goals',
            'Rodada': 'round',
            'Ano': 'season',
            'Data': 'date_str',
            'Arena': 'stadium',
            'Vencedor': 'winner'
        })

        df['competition'] = 'Brasileirão'

        # Convert goal columns to numeric
        df['home_goals'] = pd.to_numeric(df['home_goals'], errors='coerce').fillna(0).astype(int)
        df['away_goals'] = pd.to_numeric(df['away_goals'], errors='coerce').fillna(0).astype(int)

        # Normalize team names
        df['home_team_norm'] = df['home_team'].apply(normalize_team_name)
        df['away_team_norm'] = df['away_team'].apply(normalize_team_name)

        # Parse Brazilian date format (DD/MM/YYYY)
        df['match_date'] = pd.to_datetime(df['date_str'], format='%d/%m/%Y', errors='coerce')

        self.historical_brasileirao = df

    def load_fifa_players(self):
        """Load FIFA player database."""
        file_path = self.data_dir / "fifa_data.csv"
        if not file_path.exists():
            return

        df = pd.read_csv(file_path, encoding='utf-8-sig')

        # Clean column names (remove BOM and spaces)
        df.columns = df.columns.str.strip()

        # Normalize club names for matching
        if 'Club' in df.columns:
            df['club_norm'] = df['Club'].str.lower().str.strip()

        self.fifa_players = df

    def get_all_matches(self) -> pd.DataFrame:
        """Combine all match datasets into a single DataFrame."""
        dfs = []

        if self.brasileirao_matches is not None:
            dfs.append(self.brasileirao_matches)

        if self.brazilian_cup_matches is not None:
            dfs.append(self.brazilian_cup_matches)

        if self.libertadores_matches is not None:
            dfs.append(self.libertadores_matches)

        if self.br_football is not None:
            dfs.append(self.br_football)

        if self.historical_brasileirao is not None:
            dfs.append(self.historical_brasileirao)

        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()

    def search_matches(self, team: str = None, competition: str = None,
                       season: int = None, date_from=None, date_to=None) -> pd.DataFrame:
        """Search matches with various filters."""
        all_matches = self.get_all_matches()

        if all_matches.empty:
            return all_matches

        # Filter by team
        if team:
            team_norm = normalize_team_name(team)
            mask = (
                all_matches['home_team_norm'].str.contains(team_norm, case=False, na=False) |
                all_matches['away_team_norm'].str.contains(team_norm, case=False, na=False)
            )
            all_matches = all_matches[mask]

        # Filter by competition
        if competition:
            all_matches = all_matches[
                all_matches['competition'].str.contains(competition, case=False, na=False)
            ]

        # Filter by season
        if season:
            all_matches = all_matches[all_matches['season'] == season]

        # Filter by date range
        if date_from:
            date_from = pd.to_datetime(date_from)
            all_matches = all_matches[all_matches['match_date'] >= date_from]

        if date_to:
            date_to = pd.to_datetime(date_to)
            all_matches = all_matches[all_matches['match_date'] <= date_to]

        return all_matches

    def get_team_stats(self, team: str, season: int = None) -> dict:
        """Calculate team statistics."""
        matches = self.search_matches(team=team, season=season)

        if matches.empty:
            return {"error": f"No matches found for team: {team}"}

        team_norm = normalize_team_name(team)

        # Home matches
        home_matches = matches[matches['home_team_norm'] == team_norm]
        # Away matches
        away_matches = matches[matches['away_team_norm'] == team_norm]

        stats = {
            "team": team,
            "matches_played": len(matches),
            "home_matches": len(home_matches),
            "away_matches": len(away_matches),
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "goals_for": 0,
            "goals_against": 0,
        }

        for _, row in matches.iterrows():
            home_goals = int(row.get('home_goals', 0))
            away_goals = int(row.get('away_goals', 0))

            if pd.isna(home_goals) or pd.isna(away_goals):
                continue

            home_team_norm = row['home_team_norm']
            away_team_norm = row['away_team_norm']

            if home_team_norm == team_norm:
                stats["goals_for"] += home_goals
                stats["goals_against"] += away_goals
                if home_goals > away_goals:
                    stats["wins"] += 1
                elif home_goals < away_goals:
                    stats["losses"] += 1
                else:
                    stats["draws"] += 1
            else:
                stats["goals_for"] += away_goals
                stats["goals_against"] += home_goals
                if away_goals > home_goals:
                    stats["wins"] += 1
                elif away_goals < home_goals:
                    stats["losses"] += 1
                else:
                    stats["draws"] += 1

        stats["points"] = stats["wins"] * 3 + stats["draws"]
        stats["win_rate"] = stats["wins"] / stats["matches_played"] * 100 if stats["matches_played"] > 0 else 0

        return stats

    def head_to_head(self, team1: str, team2: str) -> dict:
        """Calculate head-to-head record between two teams."""
        team1_norm = normalize_team_name(team1)
        team2_norm = normalize_team_name(team2)

        all_matches = self.get_all_matches()

        # Find matches between these two teams
        mask = (
            ((all_matches['home_team_norm'] == team1_norm) & (all_matches['away_team_norm'] == team2_norm)) |
            ((all_matches['home_team_norm'] == team2_norm) & (all_matches['away_team_norm'] == team1_norm))
        )

        h2h_matches = all_matches[mask]

        if h2h_matches.empty:
            return {"error": f"No matches found between {team1} and {team2}"}

        result = {
            "team1": team1,
            "team2": team2,
            "total_matches": len(h2h_matches),
            "team1_wins": 0,
            "team2_wins": 0,
            "draws": 0,
            "matches": []
        }

        for _, row in h2h_matches.iterrows():
            home_goals = int(row.get('home_goals', 0))
            away_goals = int(row.get('away_goals', 0))

            home_team_norm = row['home_team_norm']
            away_team_norm = row['away_team_norm']

            match_info = {
                "date": str(row.get('match_date', '')),
                "home": row['home_team'],
                "away": row['away_team'],
                "score": f"{home_goals}-{away_goals}",
                "competition": row.get('competition', 'Unknown')
            }

            if home_goals > away_goals:
                if home_team_norm == team1_norm:
                    result["team1_wins"] += 1
                    match_info["winner"] = team1
                else:
                    result["team2_wins"] += 1
                    match_info["winner"] = team2
            elif away_goals > home_goals:
                if away_team_norm == team1_norm:
                    result["team1_wins"] += 1
                    match_info["winner"] = team1
                else:
                    result["team2_wins"] += 1
                    match_info["winner"] = team2
            else:
                result["draws"] += 1
                match_info["winner"] = "Draw"

            result["matches"].append(match_info)

        return result

    def search_players(self, name: str = None, nationality: str = None,
                      club: str = None, min_overall: int = None) -> pd.DataFrame:
        """Search FIFA player database."""
        if self.fifa_players is None:
            return pd.DataFrame()

        df = self.fifa_players.copy()

        if name:
            df = df[df['Name'].str.contains(name, case=False, na=False)]

        if nationality:
            df = df[df['Nationality'].str.contains(nationality, case=False, na=False)]

        if club:
            df = df[df['Club'].str.contains(club, case=False, na=False)]

        if min_overall:
            df = df[df['Overall'] >= min_overall]

        return df

    def get_competition_standings(self, competition: str, season: int) -> dict:
        """Calculate standings for a competition season."""
        matches = self.search_matches(competition=competition, season=season)

        if matches.empty:
            return {"error": f"No matches found for {competition} {season}"}

        # Group by team and calculate stats
        teams = {}

        for _, row in matches.iterrows():
            home_team = row['home_team_norm']
            away_team = row['away_team_norm']
            home_goals = int(row.get('home_goals', 0))
            away_goals = int(row.get('away_goals', 0))

            if pd.isna(home_goals) or pd.isna(away_goals):
                continue

            # Initialize team stats
            for team in [home_team, away_team]:
                if team not in teams:
                    teams[team] = {
                        "team": team,
                        "matches": 0,
                        "wins": 0,
                        "draws": 0,
                        "losses": 0,
                        "goals_for": 0,
                        "goals_against": 0,
                        "points": 0
                    }

            # Update home team stats
            teams[home_team]["matches"] += 1
            teams[home_team]["goals_for"] += home_goals
            teams[home_team]["goals_against"] += away_goals

            # Update away team stats
            teams[away_team]["matches"] += 1
            teams[away_team]["goals_for"] += away_goals
            teams[away_team]["goals_against"] += home_goals

            # Update points
            if home_goals > away_goals:
                teams[home_team]["wins"] += 1
                teams[home_team]["points"] += 3
                teams[away_team]["losses"] += 1
            elif away_goals > home_goals:
                teams[away_team]["wins"] += 1
                teams[away_team]["points"] += 3
                teams[home_team]["losses"] += 1
            else:
                teams[home_team]["draws"] += 1
                teams[away_team]["draws"] += 1
                teams[home_team]["points"] += 1
                teams[away_team]["points"] += 1

        # Convert to list and sort by points
        standings = list(teams.values())
        standings.sort(key=lambda x: (x["points"], x["goals_for"] - x["goals_against"], x["goals_for"]), reverse=True)

        return {
            "competition": competition,
            "season": season,
            "standings": standings
        }
