# language: en
Feature: Data Quality
  Team-name variations, date formats and UTF-8 must be handled consistently

  Scenario: Team name variations resolve to the same club
    Given the team registry is finalized
    When I resolve "Palmeiras-SP" and "Palmeiras"
    Then both names should resolve to the same club
    When I resolve "Sao Paulo" and "São Paulo"
    Then both names should resolve to the same club
    When I resolve "Athletico Paranaense" and "Atlético - PR"
    Then both names should resolve to the same club

  Scenario: Distinct clubs with the same base name stay distinct
    Given the team registry is finalized
    When I resolve "Botafogo - RJ" and "Botafogo - PB"
    Then the names should resolve to different clubs

  Scenario: Brazilian date format is parsed
    Given a Brazilian formatted date "29/03/2003"
    When I parse the date
    Then the parsed date should be 2003-03-29

  Scenario: ISO date with time is parsed
    Given an ISO datetime "2012-05-19 18:30:00"
    When I parse the date
    Then the parsed date should be 2012-05-19

  Scenario: UTF-8 display names are preserved
    Given the team registry is finalized
    When I check the display names
    Then the names "São Paulo", "Grêmio" and "Avaí" should be present

  Scenario: Cross-file player and match data link on the same club
    Given the store is loaded
    When I query the FIFA club "Atlético Mineiro"
    Then the players should link to the same club that appears in match data
