Feature: Team Queries
  As an analyst I want win/draw/loss and goal records for a team
  so that I can evaluate performance by season, competition and venue.

  Background:
    Given the soccer knowledge graph is loaded

  Scenario: Team record aggregates wins, draws, losses and goals
    When I request the team record for "Flamengo" in season 2023
    Then I should receive wins, losses, draws and goals
    And the totals should be internally consistent

  Scenario: Home-only record differs from overall record
    When I request the home record for "Flamengo" in season 2023
    Then the home matches should be fewer than or equal to all matches

  Scenario: Postponed matches are excluded from statistics
    When I request the team record for "Flamengo" in season 2023
    Then the counted matches should exclude the scoreless fixture
