import { describe, it, expect } from "vitest";
import {
  searchPlayers,
  getPlayerDetails,
  getBrazilianPlayersAtBrazilianClubs,
  getTopPlayers,
} from "../src/tools/player-tools.js";

describe("searchPlayers", () => {
  it("finds player by name", () => {
    const result = searchPlayers({ name: "Neymar" });
    expect(result).toContain("Neymar");
  });

  it("finds Brazilian players", () => {
    const result = searchPlayers({ nationality: "Brazil", limit: 5 });
    expect(result).toContain("Brazil");
  });

  it("finds players by club", () => {
    // Santos and Botafogo are among the Brazilian clubs in the FIFA dataset
    const result = searchPlayers({ club: "Santos", limit: 10 });
    expect(result.toLowerCase()).toContain("santos");
  });

  it("finds players by position", () => {
    const result = searchPlayers({ position: "GK", limit: 10 });
    expect(result).toContain("GK");
  });

  it("filters by minimum overall", () => {
    const result = searchPlayers({ minOverall: 85, limit: 10 });
    expect(result).not.toContain("No players found");
    // All shown players should have overall >= 85
    const lines = result.split("\n").filter((l) => l.includes("Overall:"));
    for (const line of lines) {
      const match = line.match(/Overall: (\d+)/);
      if (match) {
        expect(parseInt(match[1])).toBeGreaterThanOrEqual(85);
      }
    }
  });

  it("returns no results for impossible criteria", () => {
    const result = searchPlayers({ name: "ZZZZUNKNOWNPLAYERXXX" });
    expect(result).toBe("No players found for the given criteria.");
  });

  it("respects limit", () => {
    const result = searchPlayers({ nationality: "Brazil", limit: 5 });
    const numbered = result.match(/^\d+\./gm);
    expect(numbered?.length).toBeLessThanOrEqual(5);
  });

  it("sorts results by overall rating descending", () => {
    const result = searchPlayers({ nationality: "Brazil", limit: 5 });
    const overalls: number[] = [];
    for (const line of result.split("\n")) {
      const match = line.match(/Overall: (\d+)/);
      if (match) overalls.push(parseInt(match[1]));
    }
    for (let i = 1; i < overalls.length; i++) {
      expect(overalls[i]).toBeLessThanOrEqual(overalls[i - 1]);
    }
  });
});

describe("getPlayerDetails", () => {
  it("returns full player details", () => {
    const result = getPlayerDetails({ name: "Neymar" });
    expect(result).toContain("Player: Neymar");
    expect(result).toContain("Nationality:");
    expect(result).toContain("Overall Rating:");
    expect(result).toContain("Position:");
  });

  it("returns message for unknown player", () => {
    const result = getPlayerDetails({ name: "ZZZZUNKNOWN" });
    expect(result).toContain("No player found");
  });

  it("includes skill attributes", () => {
    const result = getPlayerDetails({ name: "Neymar" });
    expect(result).toContain("Dribbling:");
  });
});

describe("getBrazilianPlayersAtBrazilianClubs", () => {
  it("returns Brazilian players at Brazilian clubs", () => {
    const result = getBrazilianPlayersAtBrazilianClubs({});
    expect(result).toContain("Brazilian players at Brazilian clubs");
    expect(result).toContain("By club:");
  });

  it("groups players by club", () => {
    const result = getBrazilianPlayersAtBrazilianClubs({});
    // Should list clubs
    expect(result.toLowerCase()).toMatch(/flamengo|palmeiras|corinthians|santos/);
  });
});

describe("getTopPlayers", () => {
  it("returns top players overall", () => {
    const result = getTopPlayers({ limit: 5 });
    expect(result).toContain("Top Players");
    expect(result).toContain("1.");
  });

  it("filters by nationality", () => {
    const result = getTopPlayers({ nationality: "Brazil", limit: 5 });
    expect(result).toContain("Brazil");
  });

  it("filters by club", () => {
    const result = getTopPlayers({ club: "Santos", limit: 5 });
    expect(result.toLowerCase()).toContain("santos");
  });

  it("filters by position", () => {
    const result = getTopPlayers({ position: "ST", limit: 5 });
    expect(result).toContain("ST");
  });
});
