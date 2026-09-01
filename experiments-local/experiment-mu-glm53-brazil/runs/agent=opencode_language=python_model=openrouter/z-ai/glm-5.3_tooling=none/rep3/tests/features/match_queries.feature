Feature: Match Queries
  The MCP server answers match questions from the canonical index built
  from all five match datasets (Brasileirão, Copa do Brasil, Libertadores,
  BR-Football extended stats, historical 2003-2019 file).

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
    And the total should count 44 fixtures across competitions

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
    And the incomplete 2023 source data should be flagged in notes

  Scenario: Team matches in a season
    Given the match data is loaded
    When I search for "Palmeiras" matches in season 2023
    Then only 2023 fixtures involving Palmeiras are returned

  Scenario: Filter by date range
    Given the match data is loaded
    When I search Brasileirão matches between 2019-05-01 and 2019-05-31
    Then every returned match falls inside the range

  Scenario: Find finals
    Given the match data is loaded
    When I search Libertadores matches with stage "final"
    Then only finals from 2013-2020 are returned

  Scenario: Last match between two teams
    Given the match data is loaded
    When I ask for the last match between "Flamengo" and "Corinthians"
    Then the most recent fixture is returned with its score

  Scenario: Derbies in a season
    Given the match data is loaded
    When I ask for derbies in 2023
    Then Fla-Flu, Gre-Nal and the other classic rivalries are listed

  Scenario: Head-to-head comparison
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos" head-to-head
    Then I receive every fixture plus wins, draws, losses and goals

  Scenario: Unknown team
    Given the match data is loaded
    When I search for a team that does not exist
    Then I receive a helpful error message
