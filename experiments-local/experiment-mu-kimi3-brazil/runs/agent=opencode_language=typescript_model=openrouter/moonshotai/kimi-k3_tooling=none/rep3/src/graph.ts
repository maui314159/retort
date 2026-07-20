/**
 * In-memory knowledge graph over the unified dataset.
 *
 * Nodes: Team, Player, Competition, Season, Match.
 * Edges: PLAYED_HOME / PLAYED_AWAY (match->team), IN_COMPETITION (match->comp),
 *        IN_SEASON (match->season), PLAYS_FOR (player->team),
 *        HAS_NATIONALITY (player->country).
 *
 * The graph exposes typed node/edge tables plus pre-built indexes so the
 * query layer can answer questions in O(1)-O(n over one team's matches).
 */

import type { CompetitionLabel, Match, Player } from "./types.js";
import { isBrazilianTeamKey, teamDisplayName } from "./normalize.js";

export type NodeKind = "team" | "player" | "competition" | "season" | "match" | "country";

export interface GraphNode {
  id: string; // e.g. "team:flamengo-rj"
  kind: NodeKind;
  label: string;
  /** Arbitrary per-node properties. */
  props: Record<string, unknown>;
}

export interface GraphEdge {
  from: string;
  to: string;
  type:
    | "PLAYED_HOME"
    | "PLAYED_AWAY"
    | "IN_COMPETITION"
    | "IN_SEASON"
    | "PLAYS_FOR"
    | "HAS_NATIONALITY";
}

export class KnowledgeGraph {
  readonly nodes = new Map<string, GraphNode>();
  readonly edges: GraphEdge[] = [];
  private outIndex = new Map<string, GraphEdge[]>();
  private inIndex = new Map<string, GraphEdge[]>();

  addNode(node: GraphNode): void {
    if (!this.nodes.has(node.id)) this.nodes.set(node.id, node);
  }

  addEdge(edge: GraphEdge): void {
    this.edges.push(edge);
    const out = this.outIndex.get(edge.from) ?? [];
    out.push(edge);
    this.outIndex.set(edge.from, out);
    const inc = this.inIndex.get(edge.to) ?? [];
    inc.push(edge);
    this.inIndex.set(edge.to, inc);
  }

  neighbors(id: string, direction: "out" | "in" = "out"): GraphEdge[] {
    return direction === "out"
      ? (this.outIndex.get(id) ?? [])
      : (this.inIndex.get(id) ?? []);
  }

  nodeCount(kind?: NodeKind): number {
    if (!kind) return this.nodes.size;
    let n = 0;
    for (const node of this.nodes.values()) if (node.kind === kind) n++;
    return n;
  }
}

/** Indexes derived from the graph for fast querying. */
export interface GraphIndexes {
  matchesByTeam: Map<string, Match[]>;
  matchesByCompetition: Map<CompetitionLabel, Match[]>;
  matchesBySeason: Map<number, Match[]>;
  playersByNationality: Map<string, Player[]>;
  playersByClubKey: Map<string, Player[]>;
  playersByName: Map<string, Player[]>; // loose name -> players
  teams: Map<string, string>; // team key -> display name
}

export interface BuiltGraph {
  graph: KnowledgeGraph;
  indexes: GraphIndexes;
}

export function buildGraph(matches: Match[], players: Player[]): BuiltGraph {
  const graph = new KnowledgeGraph();
  const matchesByTeam = new Map<string, Match[]>();
  const matchesByCompetition = new Map<CompetitionLabel, Match[]>();
  const matchesBySeason = new Map<number, Match[]>();
  const playersByNationality = new Map<string, Player[]>();
  const playersByClubKey = new Map<string, Player[]>();
  const playersByName = new Map<string, Player[]>();
  const teams = new Map<string, string>();

  const push = <T>(map: Map<string, T[]>, key: string, value: T) => {
    const arr = map.get(key) ?? [];
    arr.push(value);
    map.set(key, arr);
  };

  for (const m of matches) {
    const matchNodeId = `match:${m.id}`;
    graph.addNode({
      id: matchNodeId,
      kind: "match",
      label: `${m.homeTeam.name} vs ${m.awayTeam.name}`,
      props: { date: m.date, season: m.season, competition: m.competition },
    });

    for (const [team, edgeType] of [
      [m.homeTeam, "PLAYED_HOME"],
      [m.awayTeam, "PLAYED_AWAY"],
    ] as const) {
      const teamNodeId = `team:${team.key}`;
      if (!graph.nodes.has(teamNodeId)) {
        graph.addNode({
          id: teamNodeId,
          kind: "team",
          label: teamDisplayName(team.key),
          props: { key: team.key, brazilian: isBrazilianTeamKey(team.key) },
        });
      }
      graph.addEdge({ from: matchNodeId, to: teamNodeId, type: edgeType });
      push(matchesByTeam, team.key, m);
      if (!teams.has(team.key)) teams.set(team.key, teamDisplayName(team.key));
    }

    const compNodeId = `competition:${m.competition}`;
    if (!graph.nodes.has(compNodeId)) {
      graph.addNode({ id: compNodeId, kind: "competition", label: m.competition, props: {} });
    }
    graph.addEdge({ from: matchNodeId, to: compNodeId, type: "IN_COMPETITION" });
    const compArr = matchesByCompetition.get(m.competition) ?? [];
    compArr.push(m);
    matchesByCompetition.set(m.competition, compArr);

    if (m.season != null) {
      const seasonNodeId = `season:${m.season}`;
      if (!graph.nodes.has(seasonNodeId)) {
        graph.addNode({ id: seasonNodeId, kind: "season", label: String(m.season), props: { year: m.season } });
      }
      graph.addEdge({ from: matchNodeId, to: seasonNodeId, type: "IN_SEASON" });
      const seasonArr = matchesBySeason.get(m.season) ?? [];
      seasonArr.push(m);
      matchesBySeason.set(m.season, seasonArr);
    }
  }

  for (const p of players) {
    const playerNodeId = `player:${p.id}`;
    graph.addNode({
      id: playerNodeId,
      kind: "player",
      label: p.name,
      props: { ...p },
    });
    const natKey = p.nationality.toLowerCase();
    const countryNodeId = `country:${natKey}`;
    if (!graph.nodes.has(countryNodeId)) {
      graph.addNode({ id: countryNodeId, kind: "country", label: p.nationality, props: {} });
    }
    graph.addEdge({ from: playerNodeId, to: countryNodeId, type: "HAS_NATIONALITY" });
    push(playersByNationality, natKey, p);

    if (p.clubKey) {
      const teamNodeId = `team:${p.clubKey}`;
      if (!graph.nodes.has(teamNodeId)) {
        graph.addNode({
          id: teamNodeId,
          kind: "team",
          label: teamDisplayName(p.clubKey),
          props: { key: p.clubKey, brazilian: true },
        });
      }
      graph.addEdge({ from: playerNodeId, to: teamNodeId, type: "PLAYS_FOR" });
      push(playersByClubKey, p.clubKey, p);
      if (!teams.has(p.clubKey)) teams.set(p.clubKey, teamDisplayName(p.clubKey));
    }
    push(playersByName, p.name.toLowerCase(), p);
  }

  return {
    graph,
    indexes: {
      matchesByTeam,
      matchesByCompetition,
      matchesBySeason,
      playersByNationality,
      playersByClubKey,
      playersByName,
      teams,
    },
  };
}
