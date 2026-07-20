/**
 * Feature: Dataset loading
 *
 * All six provided CSV files must be loadable and queryable, matches
 * deduplicated across overlapping files, and the knowledge graph built.
 */
import { describe, it, expect } from "vitest";
import { getDataset } from "./helpers.js";
import { DATA_FILES } from "../src/lib/dataset.js";
import { Competition } from "../src/lib/types.js";

describe("Feature: Dataset loading and coverage", () => {
  it("loads all 6 CSV files with the expected row counts", () => {
    const { dataset } = getDataset();
    expect(dataset.loadReport[DATA_FILES.brasileirao]).toBe(4180);
    expect(dataset.loadReport[DATA_FILES.copaDoBrasil]).toBe(1337);
    expect(dataset.loadReport[DATA_FILES.libertadores]).toBe(1255);
    expect(dataset.loadReport[DATA_FILES.historical]).toBe(6886);
    expect(dataset.loadReport[DATA_FILES.extended]).toBe(10296);
    expect(dataset.loadReport[DATA_FILES.fifa]).toBe(18207);
  });

  it("deduplicates overlapping matches across files", () => {
    const { dataset } = getDataset();
    // 27,654 raw match rows; heavy overlap 2014-2022 collapses to far fewer.
    const rawTotal = 4180 + 1337 + 1255 + 6886 + 10296;
    expect(dataset.matches.length).toBeLessThan(rawTotal * 0.8);
    expect(dataset.matches.length).toBeGreaterThan(15000);
    // No duplicate fixture on the same date.
    const keys = new Set<string>();
    for (const m of dataset.matches) {
      const key = `${m.competition}|${m.date}|${m.homeTeam.key}|${m.awayTeam.key}`;
      expect(keys.has(key)).toBe(false);
      keys.add(key);
    }
  });

  it("covers every competition", () => {
    const { dataset } = getDataset();
    const byCompetition = new Map<Competition, number>();
    for (const m of dataset.matches) {
      byCompetition.set(m.competition, (byCompetition.get(m.competition) ?? 0) + 1);
    }
    for (const c of Object.values(Competition)) {
      expect(byCompetition.get(c), c).toBeGreaterThan(0);
    }
    expect(byCompetition.get(Competition.BrasileiraoSerieA)!).toBeGreaterThan(7000);
  });

  it("loads players with ratings, positions and clubs", () => {
    const { dataset } = getDataset();
    expect(dataset.players.length).toBe(18207);
    const neymar = dataset.players.find((p) => p.name === "Neymar Jr")!;
    expect(neymar.nationality).toBe("Brazil");
    expect(neymar.overall).toBe(92);
    expect(neymar.position).toBe("LW");
  });

  it("links Brazilian-club players to canonical match-data teams", () => {
    const { dataset } = getDataset();
    const linked = dataset.players.filter((p) => p.teamKey !== null);
    expect(linked.length).toBeGreaterThan(200);
    // Every linked key must exist in the registry.
    for (const p of linked) {
      expect(dataset.teams.get(p.teamKey!), p.club ?? "").toBeDefined();
    }
  });

  it("builds a knowledge graph with teams, matches, players and competitions", () => {
    const { dataset, graph } = getDataset();
    const types = new Set([...graph.nodes.values()].map((n) => n.type));
    expect(types).toEqual(new Set(["team", "player", "match", "competition"]));
    expect(graph.nodes.size).toBeGreaterThan(30000);
    // Every match node connects to its competition.
    const someMatch = dataset.matches.find((m) => m.homeGoals !== null)!;
    const neighbors = graph.neighbors(`match:${someMatch.id}`);
    expect(neighbors.some((n) => n.edge.type === "PLAYED_IN")).toBe(true);
  });
});
