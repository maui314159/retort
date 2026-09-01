from .loader import SoccerData, load_data
from .analysis import (
    find_matches,
    head_to_head,
    team_stats,
    standings,
    biggest_wins,
    average_goals,
    search_players,
    brazilian_club_summary,
)

__all__ = [
    "SoccerData",
    "load_data",
    "find_matches",
    "head_to_head",
    "team_stats",
    "standings",
    "biggest_wins",
    "average_goals",
    "search_players",
    "brazilian_club_summary",
]
