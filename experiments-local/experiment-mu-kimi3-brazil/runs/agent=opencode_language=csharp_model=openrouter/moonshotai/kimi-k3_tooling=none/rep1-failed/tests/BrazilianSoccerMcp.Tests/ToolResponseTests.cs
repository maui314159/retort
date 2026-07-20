using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: MCP Tool Responses
///   Tools must return properly formatted, human-readable responses in the
///   style shown by the specification's example answer formats.
/// </summary>
public class ToolResponseTests
{
    private static MatchTools MatchTools => new(TestData.Service);
    private static TeamTools TeamTools => new(TestData.Service);
    private static PlayerTools PlayerTools => new(TestData.Service);
    private static CompetitionTools CompetitionTools => new(TestData.Service);

    /*
     * Scenario: Head-to-head tool returns the spec's answer format
     *   Given the match data is loaded
     *   When I ask for Flamengo vs Fluminense
     *   Then the answer lists matches and a "Head-to-head in dataset" summary line
     */
    [Fact]
    public void Head_to_head_format_matches_spec()
    {
        // Given / When
        var answer = MatchTools.GetHeadToHead("Flamengo", "Fluminense");

        // Then
        Assert.Contains("Flamengo vs Fluminense", answer);
        Assert.Contains("Head-to-head in dataset:", answer);
        Assert.Matches(@"Flamengo \d+ wins, Fluminense \d+ wins, \d+ draws", answer);
    }

    /*
     * Scenario: Team record tool returns the spec's answer format
     *   Given the match data is loaded
     *   When I ask for Corinthians' home record in 2022
     *   Then the answer contains matches, W/D/L, goals and win rate lines
     */
    [Fact]
    public void Team_record_format_matches_spec()
    {
        // Given / When
        var answer = TeamTools.GetTeamRecord("Corinthians", season: 2022, venue: "home");

        // Then
        Assert.Contains("Corinthians home record", answer);
        Assert.Matches(@"- Matches: \d+", answer);
        Assert.Matches(@"- Wins: \d+, Draws: \d+, Losses: \d+", answer);
        Assert.Matches(@"- Goals For: \d+, Goals Against: \d+", answer);
        Assert.Matches(@"- Win rate: \d+(\.\d)?%", answer);
    }

    /*
     * Scenario: Standings tool marks the champion
     *   Given the match data is loaded
     *   When I ask for the 2019 Brasileirão table
     *   Then Flamengo is listed first as Champion
     */
    [Fact]
    public void Standings_format_matches_spec()
    {
        // Given / When
        var answer = CompetitionTools.GetStandings("Brasileirão Série A", 2019);

        // Then
        Assert.Contains("2019", answer);
        Assert.Contains("calculated from matches", answer);
        Assert.Matches(@"1\. Flamengo.*- Champion", answer);
    }

    /*
     * Scenario: Player search tool lists ratings like the spec
     *   Given the FIFA data is loaded
     *   When I ask for top Brazilian players
     *   Then numbered lines with Overall / Position / Club are returned
     */
    [Fact]
    public void Player_search_format_matches_spec()
    {
        // Given / When
        var answer = PlayerTools.SearchPlayers(nationality: "Brazil", min_overall: 88, limit: 5);

        // Then
        Assert.Matches(@"1\. .+ - Overall: \d+, Position: .+, Club: .+", answer);
    }

    /*
     * Scenario: Biggest wins tool is numbered like the spec
     *   Given the match data is loaded
     *   When I ask for the biggest victories
     *   Then a numbered list of dated scorelines is returned
     */
    [Fact]
    public void Biggest_wins_format_matches_spec()
    {
        // Given / When
        var answer = CompetitionTools.GetBiggestWins(limit: 5);

        // Then
        Assert.Contains("Biggest victories", answer);
        Assert.Matches(@"1\. \d{4}-\d{2}-\d{2}: .+ \d+-\d+ .+", answer);
    }

    /*
     * Scenario: Empty results produce friendly messages, not exceptions
     *   Given the data is loaded
     *   When I query nonsense
     *   Then a "No ... found" message is returned
     */
    [Fact]
    public void Empty_results_are_friendly()
    {
        Assert.Contains("No matches found", MatchTools.FindMatches(team1: "XYZZY United"));
        Assert.Contains("No matches between", MatchTools.GetHeadToHead("XYZZY United", "QWERTY FC"));
        Assert.Contains("No players found", PlayerTools.SearchPlayers(name: "XYZZY QWERTY"));
    }

    /*
     * Scenario: Derby tool tags classic rivalry names
     *   Given the match data is loaded
     *   When I ask for 2023 derbies
     *   Then derby names appear in square brackets
     */
    [Fact]
    public void Derby_tool_tags_rivalry_names()
    {
        // Given / When
        var answer = MatchTools.FindDerbies(season: 2023);

        // Then
        Assert.Contains("[Fla-Flu]", answer);
        Assert.Contains("[Grenal]", answer);
    }

    /*
     * Scenario: Knockout bracket tool lists stages in order
     *   Given the match data is loaded
     *   When I ask for the 2019 Copa Libertadores bracket
     *   Then round-of-16 appears before the final in the listing
     */
    [Fact]
    public void Knockout_bracket_is_ordered()
    {
        // Given / When
        var answer = CompetitionTools.GetKnockoutBracket("Copa Libertadores", 2019);

        // Then
        Assert.Contains("round of 16", answer, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("final", answer, StringComparison.OrdinalIgnoreCase);
        Assert.True(
            answer.IndexOf("round of 16", StringComparison.OrdinalIgnoreCase) <
            answer.LastIndexOf("[final]", StringComparison.OrdinalIgnoreCase));
    }
}
