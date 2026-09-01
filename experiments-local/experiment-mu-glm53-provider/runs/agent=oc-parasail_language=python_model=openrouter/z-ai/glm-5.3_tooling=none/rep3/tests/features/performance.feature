Feature: Query Performance
  The spec requires simple lookups under 2 seconds and aggregate
  queries under 5 seconds.

  Scenario: Simple lookups respond in under 2 seconds
    Given the MCP server is running
    When I time a call to "search_matches" with arguments "team=Flamengo, limit=20"
    Then the call should take less than 2 seconds

  Scenario: Player lookups respond in under 2 seconds
    Given the MCP server is running
    When I time a call to "search_players" with arguments "nationality=Brazil, limit=20"
    Then the call should take less than 2 seconds

  Scenario: Aggregate queries respond in under 5 seconds
    Given the MCP server is running
    When I time a call to "standings" with arguments "competition=Brasileirão, season=2019"
    Then the call should take less than 5 seconds

  Scenario: Head-to-head aggregation responds in under 5 seconds
    Given the MCP server is running
    When I time a call to "head_to_head" with arguments "team_a=Palmeiras, team_b=Santos"
    Then the call should take less than 5 seconds

  Scenario: The whole dataset loads in under 10 seconds
    Given the match data is loaded
    Then the dataset should contain more than 15000 matches
