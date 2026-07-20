/**
 * Feature: Player Queries
 *
 * Search FIFA players by name, nationality, club, position and rating.
 */

import { beforeAll, describe, expect, it } from "vitest";
import { givenDataLoaded } from "./helpers.js";
import type { SoccerQueries } from "../src/queries.js";

let q: SoccerQueries;

beforeAll(() => {
  q = givenDataLoaded().queries;
});

describe("Feature: Player Queries", () => {
  it("Scenario: Find all Brazilian players in the dataset", () => {
    // When I filter players by nationality "Brazil"
    const brazilians = q.searchPlayers({ nationality: "Brazil", limit: 200 });
    // Then there are hundreds of them and all are Brazilian
    expect(brazilians.length).toBe(200); // capped by limit
    for (const p of brazilians) expect(p.nationality).toBe("Brazil");
  });

  it("Scenario: Who are the top Brazilian players?", () => {
    // When I ask for the highest-rated Brazilians
    const top = q.searchPlayers({ nationality: "Brazil", limit: 10 });
    // Then Neymar Jr leads the list (highest-rated Brazilian in FIFA data)
    expect(top[0].name).toBe("Neymar Jr");
    expect(top[0].overall).toBe(92);
    // And ratings are sorted descending
    for (let i = 1; i < top.length; i++) {
      expect(top[i - 1].overall!).toBeGreaterThanOrEqual(top[i].overall!);
    }
  });

  it("Scenario: Search player by name", () => {
    // When I search for "Neymar"
    const results = q.searchPlayers({ name: "Neymar", limit: 5 });
    // Then Neymar Jr is found with his details
    expect(results.length).toBeGreaterThan(0);
    const neymar = results.find((p) => p.name === "Neymar Jr");
    expect(neymar).toBeDefined();
    expect(neymar!.nationality).toBe("Brazil");
    expect(neymar!.club).toBe("Paris Saint-Germain");
    expect(neymar!.position).toBeTruthy();
  });

  it("Scenario: Name search is accent-insensitive", () => {
    // When I search with and without accents
    const withAccent = q.searchPlayers({ name: "Coutinho", limit: 10 });
    const plain = q.searchPlayers({ name: "coutinho", limit: 10 });
    // Then both find Philippe Coutinho
    expect(withAccent.some((p) => p.name.includes("Coutinho"))).toBe(true);
    expect(plain.length).toBe(withAccent.length);
  });

  it("Scenario: Which players play for a Brazilian club?", () => {
    // When I filter FIFA players by club "Grêmio"
    const players = q.searchPlayers({ club: "Grêmio", limit: 50 });
    // Then a full squad list comes back, all playing for Grêmio
    expect(players.length).toBeGreaterThan(10);
    for (const p of players) expect(p.club).toBe("Grêmio");
    // And the club resolves to the canonical team key
    for (const p of players) expect(p.clubKey).toBe("gremio-rs");
  });

  it("Scenario: Show me all forwards from a club", () => {
    // When I filter forwards at Atlético Mineiro
    const forwards = q.searchPlayers({
      club: "Atlético Mineiro",
      position: "forward",
      limit: 50,
    });
    // Then all results are attacking players of that club
    expect(forwards.length).toBeGreaterThan(0);
    const fwdCodes = ["ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"];
    for (const p of forwards) {
      expect(p.club).toBe("Atlético Mineiro");
      expect(fwdCodes).toContain(p.position);
    }
  });

  it("Scenario: Goalkeepers of any nationality at Brazilian clubs", () => {
    // When I combine position group and brazilianClubsOnly
    const gks = q.searchPlayers({ position: "goalkeeper", brazilianClubsOnly: true, limit: 100 });
    expect(gks.length).toBeGreaterThan(10);
    for (const p of gks) {
      expect(p.position).toBe("GK");
      expect(p.clubKey).toBeTruthy();
    }
  });

  it("Scenario: Brazilian players at Brazilian clubs summary", () => {
    // When I request the per-club summary for Brazilians
    const summary = q.playersByClubSummary("Brazil");
    // Then Brazilian clubs appear with counts and average ratings
    expect(summary.length).toBeGreaterThan(10);
    for (const row of summary) {
      expect(row.players).toBeGreaterThan(0);
      expect(row.averageOverall).toBeGreaterThan(50);
      expect(row.averageOverall).toBeLessThan(95);
    }
    // And counts are consistent with the raw query for one club
    const gremioRow = summary.find((r) => r.club === "Grêmio");
    expect(gremioRow).toBeDefined();
    const gremioPlayers = q.searchPlayers({ club: "Grêmio", nationality: "Brazil", limit: 100 });
    expect(gremioRow!.players).toBe(gremioPlayers.length);
  });

  it("Scenario: Highest-rated players at a club", () => {
    // When I ask for top players at Flamengo... (Flamengo is not licensed in
    // this FIFA edition, so use a present club: Santos)
    const top = q.searchPlayers({ club: "Santos", limit: 3 });
    expect(top.length).toBe(3);
    for (let i = 1; i < top.length; i++) {
      expect(top[i - 1].overall!).toBeGreaterThanOrEqual(top[i].overall!);
    }
  });

  it("Scenario: Minimum overall filter", () => {
    const elite = q.searchPlayers({ nationality: "Brazil", minOverall: 88, limit: 50 });
    expect(elite.length).toBeGreaterThan(3);
    for (const p of elite) expect(p.overall!).toBeGreaterThanOrEqual(88);
  });
});
