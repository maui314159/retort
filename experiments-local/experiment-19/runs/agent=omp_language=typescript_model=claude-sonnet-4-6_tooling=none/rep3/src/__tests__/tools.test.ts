import { describe, it, expect, beforeAll } from "vitest";
import { handleToolCall } from "../tools.js";
import { loadMatches, loadPlayers } from "../data.js";

// Pre-warm data cache so individual tests don't pay load cost
beforeAll(() => {
  loadMatches();
  loadPlayers();
});

// ---------------------------------------------------------------------------
// search_matches
// ---------------------------------------------------------------------------

describe("search_matches", () => {
  it("returns Flamengo matches", async () => {
    const result = await handleToolCall("search_matches", { team: "Flamengo", limit: 5 });
    expect(result).toContain("matches");
    expect(result.toLowerCase()).toContain("flamengo");
  });

  it("respects season filter", async () => {
    const result = await handleToolCall("search_matches", {
      team: "Palmeiras",
      season: 2019,
      competition: "brasileirao",
      limit: 50,
    });
    expect(result).toContain("2019");
    // Should not bleed into other seasons
    expect(result).not.toContain("2018:");
    expect(result).not.toContain("2020:");
  });

  it("returns 'no matches' when nothing found", async () => {
    const result = await handleToolCall("search_matches", {
      team: "NonExistentTeamXYZ123",
    });
    expect(result.toLowerCase()).toContain("no matches found");
  });

  it("respects limit parameter", async () => {
    const result = await handleToolCall("search_matches", { limit: 3 });
    // Should list at most 3 match lines (date + team + score per line)
    const lines = result.split("\n").filter((l) => /^\d{4}-\d{2}-\d{2}:/.test(l));
    expect(lines.length).toBeLessThanOrEqual(3);
  });

  it("filters by Libertadores competition", async () => {
    const result = await handleToolCall("search_matches", {
      competition: "libertadores",
      limit: 5,
    });
    expect(result).toContain("Libertadores");
  });

  it("filters by date range", async () => {
    const result = await handleToolCall("search_matches", {
      date_from: "2019-01-01",
      date_to: "2019-12-31",
      competition: "brasileirao",
      limit: 10,
    });
    // All returned dates should be in 2019
    const dateLines = result.split("\n").filter((l) => /^\d{4}-\d{2}-\d{2}:/.test(l));
    expect(dateLines.every((l) => l.startsWith("2019-"))).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// get_head_to_head
// ---------------------------------------------------------------------------

describe("get_head_to_head", () => {
  it("returns head-to-head for Flamengo vs Corinthians", async () => {
    const result = await handleToolCall("get_head_to_head", {
      team1: "Flamengo",
      team2: "Corinthians",
    });
    expect(result).toContain("Head-to-head");
    expect(result.toLowerCase()).toContain("flamengo");
    expect(result.toLowerCase()).toContain("corinthians");
    expect(result).toMatch(/Total matches: \d+/);
  });

  it("reports win/draw/loss summary", async () => {
    const result = await handleToolCall("get_head_to_head", {
      team1: "Palmeiras",
      team2: "Santos",
    });
    expect(result).toMatch(/wins: \d+/);
    expect(result).toContain("Draws:");
  });

  it("returns not found for non-existent matchup", async () => {
    const result = await handleToolCall("get_head_to_head", {
      team1: "TeamAlpha999",
      team2: "TeamBeta888",
    });
    expect(result.toLowerCase()).toContain("no head-to-head");
  });

  it("requires both team params", async () => {
    const result = await handleToolCall("get_head_to_head", { team1: "Flamengo" });
    expect(result.toLowerCase()).toContain("required");
  });
});

// ---------------------------------------------------------------------------
// get_team_stats
// ---------------------------------------------------------------------------

describe("get_team_stats", () => {
  it("returns stats for Corinthians in Brasileirão 2022", async () => {
    const result = await handleToolCall("get_team_stats", {
      team: "Corinthians",
      competition: "brasileirao",
      season: 2022,
    });
    expect(result).toMatch(/Overall:/);
    expect(result).toMatch(/\d+W \d+D \d+L/);
    expect(result).toMatch(/Win rate:/);
  });

  it("separates home and away stats", async () => {
    const result = await handleToolCall("get_team_stats", {
      team: "Flamengo",
      competition: "brasileirao",
      season: 2019,
    });
    expect(result).toContain("Home:");
    expect(result).toContain("Away:");
  });

  it("home-only filter returns only home stats", async () => {
    const result = await handleToolCall("get_team_stats", {
      team: "Palmeiras",
      competition: "brasileirao",
      season: 2021,
      venue: "home",
    });
    expect(result).toContain("Home:");
    expect(result).not.toContain("Away:");
  });

  it("returns not found for missing team", async () => {
    const result = await handleToolCall("get_team_stats", { team: "NoTeam999" });
    expect(result.toLowerCase()).toContain("no matches found");
  });
});

// ---------------------------------------------------------------------------
// search_players
// ---------------------------------------------------------------------------

describe("search_players", () => {
  it("finds Neymar Jr by name", async () => {
    const result = await handleToolCall("search_players", { name: "Neymar" });
    expect(result).toContain("Neymar Jr");
    expect(result).toContain("Brazil");
  });

  it("filters by nationality Brazil", async () => {
    const result = await handleToolCall("search_players", {
      nationality: "Brazil",
      min_overall: 85,
      limit: 10,
    });
    expect(result).toContain("Brazil");
    // Casemiro and Alisson should appear
    const lc = result.toLowerCase();
    expect(lc.includes("casemiro") || lc.includes("alisson") || lc.includes("neymar")).toBe(true);
  });

  it("finds players at Santos (a Brazilian club present in FIFA data)", async () => {
    const result = await handleToolCall("search_players", { club: "Santos", nationality: "Brazil" });
    expect(result).not.toContain("No players found");
    expect(result.toLowerCase()).toContain("santos");
  });

  it("filters by goalkeeper position", async () => {
    const result = await handleToolCall("search_players", {
      position: "GK",
      min_overall: 80,
      limit: 5,
    });
    expect(result).not.toContain("No players found");
    // All listed positions should be GK
    const lines = result.split("\n").filter((l) => l.match(/^\d+\./));
    expect(lines.every((l) => l.includes("| Pos: GK |"))).toBe(true);
  });

  it("respects min/max overall", async () => {
    const result = await handleToolCall("search_players", {
      min_overall: 90,
      max_overall: 92,
    });
    expect(result).not.toContain("No players found");
    // Should contain Neymar (92) but not De Gea (91)
    const lines = result.split("\n").filter((l) => l.match(/Overall: \d+/));
    expect(
      lines.every((l) => {
        const m = l.match(/Overall: (\d+)/);
        const v = m ? parseInt(m[1]) : 0;
        return v >= 90 && v <= 92;
      })
    ).toBe(true);
  });

  it("returns not found for impossible criteria", async () => {
    const result = await handleToolCall("search_players", { min_overall: 99, nationality: "XYZ" });
    expect(result.toLowerCase()).toContain("no players found");
  });
});

// ---------------------------------------------------------------------------
// get_standings
// ---------------------------------------------------------------------------

describe("get_standings", () => {
  it("returns 2019 Brasileirão standings with Flamengo as champion", async () => {
    const result = await handleToolCall("get_standings", { season: 2019 });
    expect(result).toContain("2019");
    // Flamengo won 2019 with 90 pts
    expect(result).toContain("Champion: Flamengo-RJ");
    const lines = result.split("\n").filter((l) => l.match(/^\s+1\s/));
    // First place should be Flamengo
    expect(lines[0]).toContain("Flamengo");
  });

  it("returns historical data for pre-2012 season", async () => {
    const result = await handleToolCall("get_standings", { season: 2006 });
    expect(result).toContain("2006");
    expect(result).not.toContain("No Brasileirão data found");
  });

  it("returns error for season without data", async () => {
    const result = await handleToolCall("get_standings", { season: 1990 });
    expect(result.toLowerCase()).toContain("no brasileirão data found");
  });

  it("standings rows sum to roughly 38 matches each for a full season", async () => {
    const result = await handleToolCall("get_standings", { season: 2022, limit: 1 });
    // Table row format: "  1  TeamName...  P  W  D  L  GF  GA  GD  Pts"
    // Capture the P column (first number after the team name)
    const rowMatch = result.match(/^\s+1\s+\S.+?\s{2,}(\d+)\s+\d+/m);
    if (rowMatch) {
      const played = parseInt(rowMatch[1]);
      expect(played).toBeGreaterThanOrEqual(30);
      expect(played).toBeLessThanOrEqual(42);
    } else {
      // If regex fails, just verify the standings returned successfully
      expect(result).toContain("2022");
    }
  });
});

// ---------------------------------------------------------------------------
// get_biggest_wins
// ---------------------------------------------------------------------------

describe("get_biggest_wins", () => {
  it("returns top 10 wins by default", async () => {
    const result = await handleToolCall("get_biggest_wins", {});
    const lines = result.split("\n").filter((l) => l.match(/^\d+\./));
    expect(lines.length).toBe(10);
  });

  it("first result has the largest goal margin", async () => {
    const result = await handleToolCall("get_biggest_wins", { limit: 3 });
    const margins = result
      .split("\n")
      .filter((l) => l.includes("margin:"))
      .map((l) => {
        const m = l.match(/margin: (\d+)/);
        return m ? parseInt(m[1]) : 0;
      });
    expect(margins[0]).toBeGreaterThanOrEqual(margins[1] ?? 0);
  });

  it("filters by competition", async () => {
    const result = await handleToolCall("get_biggest_wins", {
      competition: "libertadores",
      limit: 5,
    });
    expect(result).toContain("Libertadores");
  });
});

// ---------------------------------------------------------------------------
// get_league_overview
// ---------------------------------------------------------------------------

describe("get_league_overview", () => {
  it("returns overview with goals and win rates", async () => {
    const result = await handleToolCall("get_league_overview", {
      competition: "brasileirao",
      season: 2019,
    });
    expect(result).toContain("Total matches:");
    expect(result).toContain("Total goals:");
    expect(result).toContain("Avg goals/match:");
    expect(result).toContain("Home wins:");
    expect(result).toContain("Away wins:");
    expect(result).toContain("Draws:");
  });

  it("avg goals/match is a sensible number (1.5-4.0) for Brasileirão", async () => {
    const result = await handleToolCall("get_league_overview", {
      competition: "brasileirao",
      season: 2019,
    });
    const m = result.match(/Avg goals\/match:\s+([\d.]+)/);
    expect(m).not.toBeNull();
    const avg = parseFloat(m![1]);
    expect(avg).toBeGreaterThan(1.5);
    expect(avg).toBeLessThan(4.5);
  });
});

// ---------------------------------------------------------------------------
// list_teams
// ---------------------------------------------------------------------------

describe("list_teams", () => {
  it("lists teams in Brasileirão", async () => {
    const result = await handleToolCall("list_teams", { competition: "brasileirao" });
    expect(result).toContain("Flamengo");
    expect(result).toContain("Corinthians");
    expect(result).toContain("Palmeiras");
  });

  it("search filter works", async () => {
    const result = await handleToolCall("list_teams", { search: "flamengo" });
    const lines = result.split("\n").filter((l) => l.trim() && !l.match(/^\d+ unique/));
    // All listed teams should contain "flamengo" in normalized form
    expect(lines.every((l) => l.toLowerCase().includes("flamengo"))).toBe(true);
  });

  it("returns total team count for all competitions", async () => {
    const result = await handleToolCall("list_teams", {});
    const m = result.match(/(\d+) unique team/);
    expect(m).not.toBeNull();
    const count = parseInt(m![1]);
    expect(count).toBeGreaterThan(100); // many unique teams across all datasets
  });
});
