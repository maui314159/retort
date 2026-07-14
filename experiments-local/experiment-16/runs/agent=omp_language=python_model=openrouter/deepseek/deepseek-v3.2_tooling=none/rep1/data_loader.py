"""
Data loading and caching system for Brazilian soccer data.
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
import json
from functools import lru_cache
import warnings

from models import Match, Competition, Player, normalize_team_name


class DataLoader:
    """Loads and caches soccer data from CSV files."""
    
    def __init__(self, data_dir: str = "data/kaggle"):
        """Initialize data loader with data directory."""
        self.data_dir = Path(data_dir)
        self._matches: Optional[List[Match]] = None
        self._players: Optional[List[Player]] = None
        self._team_names: Optional[Set[str]] = None
        
        # Load normalization mapping
        self._load_normalization_mapping()
    
    def _load_normalization_mapping(self):
        """Load team normalization mapping."""
        mapping_file = Path("team_normalization.json")
        if mapping_file.exists():
            with open(mapping_file, 'r', encoding='utf-8') as f:
                self.normalization_map = json.load(f)
        else:
            self.normalization_map = {}
    
    def load_all_matches(self) -> List[Match]:
        """Load all matches from all datasets."""
        if self._matches is not None:
            return self._matches
        
        matches = []
        
        # 1. Brasileirao Matches
        matches.extend(self._load_brasileirao_matches())
        
        # 2. Brazilian Cup Matches
        matches.extend(self._load_cup_matches())
        
        # 3. Libertadores Matches
        matches.extend(self._load_libertadores_matches())
        
        # 4. BR Football Dataset
        matches.extend(self._load_br_football_matches())
        
        # 5. Historical Brasileirao (2003-2019)
        matches.extend(self._load_historical_matches())
        
        self._matches = matches
        print(f"Loaded {len(matches)} matches from all datasets")
        return matches
    
    def _load_brasileirao_matches(self) -> List[Match]:
        """Load Brasileirao matches."""
        file_path = self.data_dir / "Brasileirao_Matches.csv"
        df = pd.read_csv(file_path)
        
        matches = []
        for _, row in df.iterrows():
            try:
                match = Match(
                    id=f"BR_{row.name}",
                    date=row['datetime'],
                    home_team=row['home_team'],
                    away_team=row['away_team'],
                    home_goals=int(row['home_goal']) if pd.notna(row['home_goal']) else None,
                    away_goals=int(row['away_goal']) if pd.notna(row['away_goal']) else None,
                    competition=Competition.BRASILEIRAO,
                    season=int(row['season']) if pd.notna(row['season']) else None,
                    round=str(row['round']) if pd.notna(row['round']) else None,
                )
                matches.append(match)
            except Exception as e:
                warnings.warn(f"Error parsing Brasileirao match {row.name}: {e}")
                continue
        
        return matches
    
    def _load_cup_matches(self) -> List[Match]:
        """Load Brazilian Cup matches."""
        file_path = self.data_dir / "Brazilian_Cup_Matches.csv"
        df = pd.read_csv(file_path)
        
        matches = []
        for _, row in df.iterrows():
            try:
                match = Match(
                    id=f"CUP_{row.name}",
                    date=row['datetime'],
                    home_team=row['home_team'],
                    away_team=row['away_team'],
                    home_goals=int(row['home_goal']) if pd.notna(row['home_goal']) else None,
                    away_goals=int(row['away_goal']) if pd.notna(row['away_goal']) else None,
                    competition=Competition.COPA_DO_BRASIL,
                    season=int(row['season']) if pd.notna(row['season']) else None,
                    round=str(row['round']) if pd.notna(row['round']) else None,
                )
                matches.append(match)
            except Exception as e:
                warnings.warn(f"Error parsing Cup match {row.name}: {e}")
                continue
        
        return matches
    
    def _load_libertadores_matches(self) -> List[Match]:
        """Load Libertadores matches."""
        file_path = self.data_dir / "Libertadores_Matches.csv"
        df = pd.read_csv(file_path)
        
        matches = []
        for _, row in df.iterrows():
            try:
                match = Match(
                    id=f"LIB_{row.name}",
                    date=row['datetime'],
                    home_team=row['home_team'],
                    away_team=row['away_team'],
                    home_goals=int(row['home_goal']) if pd.notna(row['home_goal']) else None,
                    away_goals=int(row['away_goal']) if pd.notna(row['away_goal']) else None,
                    competition=Competition.LIBERTADORES,
                    season=int(row['season']) if pd.notna(row['season']) else None,
                    stage=row['stage'] if pd.notna(row['stage']) else None,
                )
                matches.append(match)
            except Exception as e:
                warnings.warn(f"Error parsing Libertadores match {row.name}: {e}")
                continue
        
        return matches
    
    def _load_br_football_matches(self) -> List[Match]:
        """Load BR Football Dataset matches."""
        file_path = self.data_dir / "BR-Football-Dataset.csv"
        df = pd.read_csv(file_path)
        
        matches = []
        for _, row in df.iterrows():
            try:
                # Determine competition
                tournament = str(row['tournament']).lower() if pd.notna(row['tournament']) else ""
                if 'copa do brasil' in tournament:
                    competition = Competition.COPA_DO_BRASIL
                elif 'libertadores' in tournament:
                    competition = Competition.LIBERTADORES
                elif 'brasileirão' in tournament or 'serie a' in tournament:
                    competition = Competition.BRASILEIRAO
                else:
                    competition = Competition.OTHER
                
                # Create date from date and time columns
                date_str = str(row['date']) if pd.notna(row['date']) else ""
                time_str = str(row['time']) if pd.notna(row['time']) else ""
                
                if date_str and time_str and ':' in time_str:
                    datetime_str = f"{date_str} {time_str}"
                else:
                    datetime_str = date_str
                
                match = Match(
                    id=f"BRF_{row.name}",
                    date=datetime_str,
                    home_team=row['home'],
                    away_team=row['away'],
                    home_goals=int(row['home_goal']) if pd.notna(row['home_goal']) else None,
                    away_goals=int(row['away_goal']) if pd.notna(row['away_goal']) else None,
                    competition=competition,
                    home_corners=int(row['home_corner']) if pd.notna(row['home_corner']) else None,
                    away_corners=int(row['away_corner']) if pd.notna(row['away_corner']) else None,
                    home_attacks=int(row['home_attack']) if pd.notna(row['home_attack']) else None,
                    away_attacks=int(row['away_attack']) if pd.notna(row['away_attack']) else None,
                    home_shots=int(row['home_shots']) if pd.notna(row['home_shots']) else None,
                    away_shots=int(row['away_shots']) if pd.notna(row['away_shots']) else None,
                )
                matches.append(match)
            except Exception as e:
                warnings.warn(f"Error parsing BR Football match {row.name}: {e}")
                continue
        
        return matches
    
    def _load_historical_matches(self) -> List[Match]:
        """Load historical Brasileirao matches (2003-2019)."""
        file_path = self.data_dir / "novo_campeonato_brasileiro.csv"
        df = pd.read_csv(file_path)
        
        matches = []
        for _, row in df.iterrows():
            try:
                match = Match(
                    id=row['ID'] if pd.notna(row['ID']) else f"HIST_{row.name}",
                    date=row['Data'],
                    home_team=row['Equipe_mandante'],
                    away_team=row['Equipe_visitante'],
                    home_goals=int(row['Gols_mandante']) if pd.notna(row['Gols_mandante']) else None,
                    away_goals=int(row['Gols_visitante']) if pd.notna(row['Gols_visitante']) else None,
                    competition=Competition.BRASILEIRAO,
                    season=int(row['Ano']) if pd.notna(row['Ano']) else None,
                    round=str(row['Rodada']) if pd.notna(row['Rodada']) else None,
                    stadium=row['Arena'] if pd.notna(row['Arena']) else None,
                )
                matches.append(match)
            except Exception as e:
                warnings.warn(f"Error parsing historical match {row.name}: {e}")
                continue
        
        return matches
    
    def load_all_players(self) -> List[Player]:
        """Load all players from FIFA dataset."""
        if self._players is not None:
            return self._players
        
        file_path = self.data_dir / "fifa_data.csv"
        df = pd.read_csv(file_path)
        
        players = []
        for _, row in df.iterrows():
            try:
                # Extract key skill ratings
                # Calculate average pace (acceleration + sprint speed) / 2
                try:
                    acceleration = int(str(row['Acceleration']).split('+')[0]) if pd.notna(row['Acceleration']) else None
                    sprint_speed = int(str(row['SprintSpeed']).split('+')[0]) if pd.notna(row['SprintSpeed']) else None
                    if acceleration and sprint_speed:
                        pace = (acceleration + sprint_speed) // 2
                    else:
                        pace = None
                except:
                    pace = None
                
                # Calculate other skills similarly
                shooting = self._extract_skill(row, 'Finishing')
                passing = self._extract_skill(row, 'ShortPassing')
                dribbling = self._extract_skill(row, 'Dribbling')
                defending = self._extract_skill(row, 'Marking')
                physicality = self._extract_skill(row, 'Strength')
                
                player = Player(
                    id=int(row['ID']),
                    name=row['Name'],
                    age=int(row['Age']) if pd.notna(row['Age']) else None,
                    nationality=row['Nationality'],
                    overall=int(row['Overall']) if pd.notna(row['Overall']) else None,
                    potential=int(row['Potential']) if pd.notna(row['Potential']) else None,
                    club=row['Club'] if pd.notna(row['Club']) else None,
                    position=row['Position'] if pd.notna(row['Position']) else None,
                    jersey_number=int(row['Jersey Number']) if pd.notna(row['Jersey Number']) else None,
                    height=row['Height'] if pd.notna(row['Height']) else None,
                    weight=row['Weight'] if pd.notna(row['Weight']) else None,
                    pace=pace,
                    shooting=shooting,
                    passing=passing,
                    dribbling=dribbling,
                    defending=defending,
                    physicality=physicality,
                )
                players.append(player)
            except Exception as e:
                warnings.warn(f"Error parsing player {row['ID'] if 'ID' in row else row.name}: {e}")
                continue
        
        self._players = players
        print(f"Loaded {len(players)} players from FIFA dataset")
        return players
    
    def _extract_skill(self, row, skill_name: str) -> Optional[int]:
        """Extract skill rating from FIFA data."""
        if skill_name not in row or pd.isna(row[skill_name]):
            return None
        try:
            value = str(row[skill_name])
            # Handle values like "75+2"
            if '+' in value:
                base = value.split('+')[0]
                return int(base)
            return int(value)
        except:
            return None
    
    @lru_cache(maxsize=128)
    def get_team_names(self) -> Set[str]:
        """Get all unique team names from matches."""
        if self._team_names is not None:
            return self._team_names
        
        matches = self.load_all_matches()
        team_names = set()
        
        for match in matches:
            team_names.add(match.home_team)
            team_names.add(match.away_team)
        
        self._team_names = team_names
        return team_names
    
    def find_matches_by_team(self, team_name: str, normalize: bool = True) -> List[Match]:
        """Find all matches involving a team."""
        matches = self.load_all_matches()
        target_team = normalize_team_name(team_name) if normalize else team_name
        
        result = []
        for match in matches:
            home_normalized = normalize_team_name(match.home_team)
            away_normalized = normalize_team_name(match.away_team)
            
            if target_team == home_normalized or target_team == away_normalized:
                result.append(match)
        
        return result
    
    def find_matches_between_teams(self, team1: str, team2: str) -> List[Match]:
        """Find all matches between two teams."""
        matches = self.load_all_matches()
        team1_norm = normalize_team_name(team1)
        team2_norm = normalize_team_name(team2)
        
        result = []
        for match in matches:
            home_norm = normalize_team_name(match.home_team)
            away_norm = normalize_team_name(match.away_team)
            
            if (team1_norm == home_norm and team2_norm == away_norm) or \
               (team1_norm == away_norm and team2_norm == home_norm):
                result.append(match)
        
        return result
    
    def find_players_by_club(self, club_name: str) -> List[Player]:
        """Find all players from a club."""
        players = self.load_all_players()
        club_norm = normalize_team_name(club_name)
        
        result = []
        for player in players:
            if player.club and normalize_team_name(player.club) == club_norm:
                result.append(player)
        
        return result
    
    def find_players_by_nationality(self, nationality: str) -> List[Player]:
        """Find all players by nationality."""
        players = self.load_all_players()
        
        return [p for p in players if p.nationality.lower() == nationality.lower()]
    
    def search_players_by_name(self, query: str) -> List[Player]:
        """Search players by name."""
        players = self.load_all_players()
        query_lower = query.lower()
        
        return [p for p in players if query_lower in p.name.lower()]


# Global instance for easy access
loader = DataLoader()