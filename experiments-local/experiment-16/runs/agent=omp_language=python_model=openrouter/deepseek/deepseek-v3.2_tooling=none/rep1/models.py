"""
Data models for Brazilian soccer MCP server.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator
import re


class Competition(str, Enum):
    """Soccer competitions in the datasets."""
    BRASILEIRAO = "Brasileirão"
    COPA_DO_BRASIL = "Copa do Brasil"
    LIBERTADORES = "Copa Libertadores"
    OTHER = "Other"


class MatchResult(str, Enum):
    """Match result from perspective of home team."""
    HOME_WIN = "home_win"
    AWAY_WIN = "away_win"
    DRAW = "draw"


class PlayerPosition(str, Enum):
    """Simplified player positions."""
    GOALKEEPER = "GK"
    DEFENDER = "DEF"
    MIDFIELDER = "MID"
    FORWARD = "FWD"


class Match(BaseModel):
    """Represents a soccer match."""
    id: Optional[str] = None
    date: datetime
    home_team: str
    away_team: str
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    competition: Competition
    season: Optional[int] = None
    round: Optional[str] = None
    stage: Optional[str] = None
    stadium: Optional[str] = None
    
    # Extended statistics (optional)
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    home_attacks: Optional[int] = None
    away_attacks: Optional[int] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    half_time_home_goals: Optional[int] = None
    half_time_away_goals: Optional[int] = None
    
    @property
    def result(self) -> Optional[MatchResult]:
        """Determine match result."""
        if self.home_goals is None or self.away_goals is None:
            return None
        if self.home_goals > self.away_goals:
            return MatchResult.HOME_WIN
        elif self.away_goals > self.home_goals:
            return MatchResult.AWAY_WIN
        else:
            return MatchResult.DRAW
    
    @property
    def total_goals(self) -> Optional[int]:
        """Total goals in the match."""
        if self.home_goals is not None and self.away_goals is not None:
            return self.home_goals + self.away_goals
        return None
    
    @validator('home_team', 'away_team', pre=True)
    def normalize_team_name(cls, v):
        """Normalize team names."""
        if v is None:
            return None
        return normalize_team_name(str(v))
    
    @validator('date', pre=True)
    def parse_date(cls, v):
        """Parse various date formats."""
        if v is None:
            return None
        
        # Handle string dates
        if isinstance(v, str):
            # Try different formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d/%m/%Y',
                '%d/%m/%Y %H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
            
            # Try to extract date from datetime string
            match = re.search(r'\d{4}-\d{2}-\d{2}', v)
            if match:
                return datetime.strptime(match.group(), '%Y-%m-%d')
        
        return v


class TeamStats(BaseModel):
    """Statistics for a team in a given context."""
    team: str
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    
    @property
    def points(self) -> int:
        """Calculate points (3 for win, 1 for draw)."""
        return self.wins * 3 + self.draws
    
    @property
    def goal_difference(self) -> int:
        """Goal difference."""
        return self.goals_for - self.goals_against
    
    @property
    def win_percentage(self) -> float:
        """Win percentage."""
        if self.matches_played == 0:
            return 0.0
        return (self.wins / self.matches_played) * 100
    
    @property
    def average_goals_for(self) -> float:
        """Average goals scored per match."""
        if self.matches_played == 0:
            return 0.0
        return self.goals_for / self.matches_played
    
    @property
    def average_goals_against(self) -> float:
        """Average goals conceded per match."""
        if self.matches_played == 0:
            return 0.0
        return self.goals_against / self.matches_played


class Player(BaseModel):
    """Represents a FIFA player."""
    id: int
    name: str
    age: Optional[int] = None
    nationality: str
    overall_rating: int = Field(..., alias='overall')
    potential_rating: int = Field(..., alias='potential')
    club: Optional[str] = None
    position: Optional[PlayerPosition] = None
    jersey_number: Optional[int] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    
    # Key skills
    pace: Optional[int] = None
    shooting: Optional[int] = None
    passing: Optional[int] = None
    dribbling: Optional[int] = None
    defending: Optional[int] = None
    physicality: Optional[int] = None
    
    @validator('club', pre=True)
    def normalize_club_name(cls, v):
        """Normalize club names."""
        if v is None:
            return None
        return normalize_team_name(str(v))
    
    @validator('position', pre=True)
    def map_position(cls, v):
        """Map FIFA positions to simplified categories."""
        if v is None:
            return None
        
        v = str(v).upper()
        
        # Goalkeeper
        if v == 'GK':
            return PlayerPosition.GOALKEEPER
        
        # Defenders
        if any(pos in v for pos in ['CB', 'LB', 'RB', 'WB', 'SW', 'RWB', 'LWB']):
            return PlayerPosition.DEFENDER
        
        # Midfielders
        if any(pos in v for pos in ['CM', 'CDM', 'CAM', 'LM', 'RM', 'DM', 'AM', 'M']):
            return PlayerPosition.MIDFIELDER
        
        # Forwards
        if any(pos in v for pos in ['ST', 'CF', 'LF', 'RF', 'LW', 'RW', 'F', 'W']):
            return PlayerPosition.FORWARD
        
        return PlayerPosition.MIDFIELDER  # Default


class HeadToHead(BaseModel):
    """Head-to-head statistics between two teams."""
    team1: str
    team2: str
    matches: List[Match] = []
    
    @property
    def team1_wins(self) -> int:
        """Number of wins for team1 (as home or away)."""
        return sum(1 for m in self.matches 
                  if (m.home_team == self.team1 and m.result == MatchResult.HOME_WIN) or
                     (m.away_team == self.team1 and m.result == MatchResult.AWAY_WIN))
    
    @property
    def team2_wins(self) -> int:
        """Number of wins for team2 (as home or away)."""
        return sum(1 for m in self.matches 
                  if (m.home_team == self.team2 and m.result == MatchResult.HOME_WIN) or
                     (m.away_team == self.team2 and m.result == MatchResult.AWAY_WIN))
    
    @property
    def draws(self) -> int:
        """Number of draws."""
        return sum(1 for m in self.matches if m.result == MatchResult.DRAW)
    
    @property
    def total_matches(self) -> int:
        """Total number of matches."""
        return len(self.matches)


# Helper functions
def normalize_team_name(name: str) -> str:
    """Normalize team names across different datasets."""
    if name is None:
        return None
    
    name = str(name).strip()
    
    # Remove state suffix with hyphen (e.g., "Palmeiras-SP" -> "Palmeiras")
    if '-' in name:
        parts = name.split('-')
        if len(parts[-1]) == 2 and parts[-1].isupper():  # State abbreviation
            name = '-'.join(parts[:-1]).strip()
    
    # Remove parentheses with country/state abbreviations
    name = re.sub(r'\s*\([^)]*\)', '', name)
    
    # Remove club suffixes in parentheses (antigo, etc.)
    name = re.sub(r'\s*\([^)]*antigo[^)]*\)', '', name, flags=re.IGNORECASE)
    
    # Standardize common variations
    replacements = {
        'Sao Paulo': 'São Paulo',
        'S. Paulo': 'São Paulo',
        'Atletico': 'Atlético',
        'Athletico': 'Atlético',
        'Gremio': 'Grêmio',
        'Internacional Porto Alegre': 'Internacional',
        'Sport Recife': 'Sport',
        'Fluminense Football Club': 'Fluminense',
        'Corinthians Paulista': 'Corinthians',
        'Palmeiras Sociedade Esportiva': 'Palmeiras',
        'America': 'América',
        'Avai': 'Avaí',
        'Ceara': 'Ceará',
        'Goias': 'Goiás',
        'Parana': 'Paraná',
        'Vitoria': 'Vitória',
    }
    
    for old, new in replacements.items():
        if old in name:
            name = name.replace(old, new)
    
    # Remove common club suffixes
    suffixes = [
        ' FC', ' SC', ' Esporte Clube', ' Club', ' Futebol Clube',
        ' -', ' (RJ)', ' (MG)', ' (SP)', ' (PR)', ' (RS)', ' (BA)', 
        ' (CE)', ' (PE)', ' (SC)', ' (GO)', ' (MT)', ' (MS)', ' (ES)'
    ]
    
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    
    # Remove trailing hyphens and spaces
    name = name.rstrip('-').strip()
    
    return name