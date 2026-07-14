"""
Example usage of the Brazilian Soccer MCP Server tools.
This script demonstrates how to use the tools programmatically.
"""

import sys
sys.path.insert(0, '.')

# Import the server module to access the tools
import server

def main():
    """Run example queries."""
    print("=== Brazilian Soccer MCP Server Examples ===\n")

    # Example 1: Search for matches
    print("1. Search for Flamengo matches:")
    result = server.search_matches(team="Flamengo", limit=5)
    print(result)
    print("\n" + "="*50 + "\n")

    # Example 2: Get team statistics
    print("2. Get Palmeiras statistics:")
    result = server.get_team_stats(team="Palmeiras")
    print(result)
    print("\n" + "="*50 + "\n")

    # Example 3: Head-to-head record
    print("3. Head-to-head: Flamengo vs Fluminense:")
    result = server.head_to_head(team1="Flamengo", team2="Fluminense")
    print(result[:500])
    print("\n" + "="*50 + "\n")

    # Example 4: Search players
    print("4. Search for Brazilian players:")
    result = server.search_players(nationality="Brazil", min_overall=90, limit=10)
    print(result)
    print("\n" + "="*50 + "\n")

    # Example 5: Competition standings
    print("5. Brasileirão 2012 standings:")
    result = server.get_competition_standings(competition="Brasileirão", season=2012)
    print(result[:500])
    print("\n" + "="*50 + "\n")

    # Example 6: Compare teams
    print("6. Compare Flamengo and Palmeiras:")
    result = server.compare_teams(team1="Flamengo", team2="Palmeiras")
    print(result)
    print("\n" + "="*50 + "\n")

    # Example 7: Biggest wins
    print("7. Biggest wins in the dataset:")
    result = server.get_biggest_wins(limit=5)
    print(result)
    print("\n" + "="*50 + "\n")

    # Example 8: Average goals
    print("8. Average goals per match in Brasileirão:")
    result = server.get_average_goals(competition="Brasileirão")
    print(result)
    print("\n" + "="*50 + "\n")

    # Example 9: List competitions
    print("9. Available competitions:")
    result = server.get_competitions()
    print(result)
    print("\n" + "="*50 + "\n")

    # Example 10: List seasons
    print("10. Available seasons for Brasileirão:")
    result = server.get_seasons(competition="Brasileirão")
    print(result[:500])

if __name__ == "__main__":
    main()
