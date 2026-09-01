Feature: Team Queries
  Team records, home/away splits, cross-file profiles and name resolution.

  Scenario: Home record in a season
    Given the match data is loaded
    When I request Corinthians' home record in the 2022 Brasileirão
    Then I receive matches, wins, draws, losses, goals and win rate
    And the incomplete 2022 source data is flagged

  Scenario: Home plus away equals overall
    Given the match data is loaded
    When I request Grêmio's 2019 home, away and overall records
    Then home matches plus away matches equal the overall total

  Scenario: Cross-file team profile
    Given the match data is loaded
    When I request the profile for "Palmeiras"
    Then every competition and season featuring Palmeiras is listed
    And its FIFA players are summarized (or their absence noted)

  Scenario: List teams in a competition season
    Given the match data is loaded
    When I list the teams of the 2019 Brasileirão
    Then all twenty clubs are returned

  Scenario: Resolve spelling variants
    Given the match data is loaded
    When I resolve "Athletico Paranaense - PR"
    Then it maps to the same club as "Athletico" and "Atletico-PR"

  Scenario: Disambiguate same-name clubs
    Given the match data is loaded
    When I resolve "América"
    Then América Mineiro (most matches) is ranked first
    And América RN is offered as an alternative
