"""
Query engine for Brazilian soccer data analysis.
"""
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date
from collections import defaultdict
import statistics
from functools import lru_cache

from models import (
    Match, Competition, TeamStats, HeadToHead, Player, 
    MatchResult, normalize_team_name
)
from data_loader import loader


class QueryEngine:
    """Engine for querying and analyzing soccer data."""
    
    def __init__(self):
        """Initialize query engine with data loader."""
        self.loader = loader
    
    # Match queries
    @lru_cache(maxsize=128)
    def get_matches_by_team(self, team_name: str, season: Optional[int] = None, 
                           competition: Optional[Competition] = None) -> List[Match]:
        """Get all matches for a team, optionally filtered by season and competition."""
        matches = self.loader.find_matches_by_team(team_name)
        
        if season is not None:
            matches = [m for m in matches if m.season == season]
        
        if competition is not None:
            matches = [m for m in matches if m.competition == competition]
        
        # Sort by date (most recent first)
        matches.sort(key=lambda m: m.date, reverse=True)
        return matches
    
    @lru_cache(maxsize=128)
    def get_matches_between_teams(self, team1: str, team2: str) -> List[Match]:
        """Get all matches between two teams."""
        matches = self.loader.find_matches_between_teams(team1, team2)
        matches.sort(key=lambda m: m.date, reverse=True)
        return matches
    
    def get_matches_by_date_range(self, start_date: date, end_date: date) -> List[Match]:
        """Get matches within a date range."""
        matches = self.loader.load_all_matches()
        result = []
        
        for match in matches:
            match_date = match.date.date()
            if start_date <= match_date <= end_date:
                result.append(match)
        
        result.sort(key=lambda m: m.date, reverse=True)
        return result
    
    # Team statistics
    @lru_cache(maxsize=128)
    def get_team_stats(self, team_name: str, season: Optional[int] = None,
                      competition: Optional[Competition] = None) -> TeamStats:
        """Get statistics for a team."""
        matches = self.get_matches_by_team(team_name, season, competition)
        team_norm = normalize_team_name(team_name)
        
        stats = TeamStats(team=team_norm)
        
        for match in matches:
            if match.home_goals is None or match.away_goals is None:
                continue
                
            stats.matches_played += 1
            
            home_norm = normalize_team_name(match.home_team)
            
            if home_norm == team_norm:
                # Team was home
                stats.goals_for += match.home_goals
                stats.goals_against += match.away_goals
                
                if match.result == MatchResult.HOME_WIN:
                    stats.wins += 1
                elif match.result == MatchResult.AWAY_WIN:
                    stats.losses += 1
                else:
                    stats.draws += 1
            else:
                # Team was away
                stats.goals_for += match.away_goals
                stats.goals_against += match.home_goals
                
                if match.result == MatchResult.AWAY_WIN:
                    stats.wins += 1
                elif match.result == MatchResult.HOME_WIN:
                    stats.losses += 1
                else:
                    stats.draws += 1
        
        return stats
    
    @lru_cache(maxsize=64)
    def get_head_to_head(self, team1: str, team2: str) -> HeadToHead:
        """Get head-to-head statistics between two teams."""
        matches = self.get_matches_between_teams(team1, team2)
        return HeadToHead(team1=normalize_team_name(team1), 
                         team2=normalize_team_name(team2), 
                         matches=matches)
    
    @lru_cache(maxsize=32)
    def get_team_rankings(self, season: int, competition: Competition) -> List[Dict[str, Any]]:
        """Get team rankings for a specific season and competition."""
        matches = self.loader.load_all_matches()
        season_matches = [m for m in matches if m.season == season and m.competition == competition]
        
        # Initialize team stats
        team_stats = {}
        
        for match in season_matches:
            if match.home_goals is None or match.away_goals is None:
                continue
                
            home_team = normalize_team_name(match.home_team)
            away_team = normalize_team_name(match.away_team)
            
            # Initialize stats for teams if not present
            if home_team not in team_stats:
                team_stats[home_team] = TeamStats(team=home_team)
            if away_team not in team_stats:
                team_stats[away_team] = TeamStats(team=away_team)
            
            # Update home team stats
            home_stats = team_stats[home_team]
            home_stats.matches_played += 1
            home_stats.goals_for += match.home_goals
            home_stats.goals_against += match.away_goals
            
            if match.result == MatchResult.HOME_WIN:
                home_stats.wins += 1
            elif match.result == MatchResult.AWAY_WIN:
                home_stats.losses += 1
            else:
                home_stats.draws += 1
            
            # Update away team stats
            away_stats = team_stats[away_team]
            away_stats.matches_played += 1
            away_stats.goals_for += match.away_goals
            away_stats.goals_against += match.home_goals
            
            if match.result == MatchResult.AWAY_WIN:
                away_stats.wins += 1
            elif match.result == MatchResult.HOME_WIN:
                away_stats.losses += 1
            else:
                away_stats.draws += 1
        
        # Convert to list and sort by points, goal difference, goals for
        rankings = []
        for team, stats in team_stats.items():
            rankings.append({
                'team': team,
                'matches_played': stats.matches_played,
                'wins': stats.wins,
                'draws': stats.draws,
                'losses': stats.losses,
                'points': stats.points,
                'goals_for': stats.goals_for,
                'goals_against': stats.goals_against,
                'goal_difference': stats.goal_difference,
                'win_percentage': stats.win_percentage,
            })
        
        rankings.sort(key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))
        
        # Add position
        for i, rank in enumerate(rankings, 1):
            rank['position'] = i
        
        return rankings
    
    # Player queries
    @lru_cache(maxsize=128)
    def get_players_by_club(self, club_name: str) -> List[Player]:
        """Get all players from a club."""
        return self.loader.find_players_by_club(club_name)
    
    @lru_cache(maxsize=128)
    def get_players_by_nationality(self, nationality: str) -> List[Player]:
        """Get all players by nationality."""
        return self.loader.find_players_by_nationality(nationality)
    
    @lru_cache(maxsize=128)
    def search_players(self, query: str, limit: int = 50) -> List[Player]:
        """Search players by name."""
        players = self.loader.search_players_by_name(query)
        # Sort by overall rating (highest first)
        players.sort(key=lambda p: p.overall_rating if p.overall_rating else 0, reverse=True)
        return players[:limit]
    
    @lru_cache(maxsize=64)
    def get_top_players(self, nationality: Optional[str] = None, 
                       club: Optional[str] = None, limit: int = 20) -> List[Player]:
        """Get top players by overall rating, optionally filtered."""
        players = self.loader.load_all_players()
        
        if nationality:
            players = [p for p in players if p.nationality.lower() == nationality.lower()]
        
        if club:
            club_norm = normalize_team_name(club)
            players = [p for p in players if p.club and normalize_team_name(p.club) == club_norm]
        
        # Filter out players without ratings
        players = [p for p in players if p.overall_rating is not None]
        
        # Sort by overall rating
        players.sort(key=lambda p: p.overall_rating, reverse=True)
        return players[:limit]
    
    # Competition analysis
    @lru_cache(maxsize=32)
    def get_competition_stats(self, competition: Competition) -> Dict[str, Any]:
        """Get statistics for a competition."""
        matches = self.loader.load_all_matches()
        comp_matches = [m for m in matches if m.competition == competition]
        
        if not comp_matches:
            return {}
        
        total_goals = 0
        total_matches = 0
        home_wins = 0
        away_wins = 0
        draws = 0
        
        for match in comp_matches:
            if match.home_goals is None or match.away_goals is None:
                continue
                
            total_matches += 1
            total_goals += match.home_goals + match.away_goals
            
            if match.result == MatchResult.HOME_WIN:
                home_wins += 1
            elif match.result == MatchResult.AWAY_WIN:
                away_wins += 1
            elif match.result == MatchResult.DRAW:
                draws += 1
        
        avg_goals = total_goals / total_matches if total_matches > 0 else 0
        home_win_pct = (home_wins / total_matches * 100) if total_matches > 0 else 0
        away_win_pct = (away_wins / total_matches * 100) if total_matches > 0 else 0
        draw_pct = (draws / total_matches * 100) if total_matches > 0 else 0
        
        # Find seasons with data
        seasons = sorted(set(m.season for m in comp_matches if m.season))
        
        return {
            'competition': competition.value,
            'total_matches': total_matches,
            'total_goals': total_goals,
            'average_goals_per_match': round(avg_goals, 2),
            'home_wins': home_wins,
            'away_wins': away_wins,
            'draws': draws,
            'home_win_percentage': round(home_win_pct, 1),
            'away_win_percentage': round(away_win_pct, 1),
            'draw_percentage': round(draw_pct, 1),
            'seasons': seasons,
            'first_season': min(seasons) if seasons else None,
            'last_season': max(seasons) if seasons else None,
        }
    
    @lru_cache(maxsize=32)
    def get_biggest_wins(self, competition: Optional[Competition] = None, 
                        limit: int = 10) -> List[Dict[str, Any]]:
        """Get biggest wins (largest goal difference)."""
        matches = self.loader.load_all_matches()
        
        if competition:
            matches = [m for m in matches if m.competition == competition]
        
        # Filter matches with valid scores
        valid_matches = []
        for match in matches:
            if match.home_goals is not None and match.away_goals is not None:
                goal_diff = abs(match.home_goals - match.away_goals)
                valid_matches.append((goal_diff, match))
        
        # Sort by goal difference (largest first)
        valid_matches.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for goal_diff, match in valid_matches[:limit]:
            results.append({
                'date': match.date.strftime('%Y-%m-%d'),
                'home_team': match.home_team,
                'away_team': match.away_team,
                'home_goals': match.home_goals,
                'away_goals': match.away_goals,
                'goal_difference': goal_diff,
                'competition': match.competition.value,
                'season': match.season,
            })
        
        return results
    
    @lru_cache(maxsize=32)
    def get_highest_scoring_matches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get highest scoring matches (most total goals)."""
        matches = self.loader.load_all_matches()
        
        # Filter matches with valid scores
        valid_matches = []
        for match in matches:
            if match.home_goals is not None and match.away_goals is not None:
                total_goals = match.home_goals + match.away_goals
                valid_matches.append((total_goals, match))
        
        # Sort by total goals (highest first)
        valid_matches.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for total_goals, match in valid_matches[:limit]:
            results.append({
                'date': match.date.strftime('%Y-%m-%d'),
                'home_team': match.home_team,
                'away_team': match.away_team,
                'home_goals': match.home_goals,
                'away_goals': match.away_goals,
                'total_goals': total_goals,
                'competition': match.competition.value,
                'season': match.season,
            })
        
        return results
    
    # General analysis
    @lru_cache(maxsize=1)
    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall statistics across all datasets."""
        matches = self.loader.load_all_matches()
        players = self.loader.load_all_players()
        
        total_matches = len(matches)
        total_players = len(players)
        
        # Count matches by competition
        comp_counts = defaultdict(int)
        for match in matches:
            comp_counts[match.competition.value] += 1
        
        # Count Brazilian players
        brazilian_players = len([p for p in players if p.nationality.lower() == 'brazil'])
        
        # Count players by position
        position_counts = defaultdict(int)
        for player in players:
            if player.position:
                position_counts[player.position.value] += 1
        
        # Calculate average ratings
        ratings = [p.overall_rating for p in players if p.overall_rating is not None]
        avg_rating = statistics.mean(ratings) if ratings else 0
        
        # Get range of seasons
        seasons = sorted(set(m.season for m in matches if m.season))
        
        return {
            'total_matches': total_matches,
            'total_players': total_players,
            'brazilian_players': brazilian_players,
            'average_player_rating': round(avg_rating, 1),
            'matches_by_competition': dict(comp_counts),
            'players_by_position': dict(position_counts),
            'seasons_range': f"{min(seasons)}-{max(seasons)}" if seasons else "N/A",
            'first_season': min(seasons) if seasons else None,
            'last_season': max(seasons) if seasons else None,
        }


# Global instance for easy access
engine = QueryEngine()