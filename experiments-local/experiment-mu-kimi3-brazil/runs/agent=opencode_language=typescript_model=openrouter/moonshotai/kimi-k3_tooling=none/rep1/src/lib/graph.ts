/**
 * In-memory knowledge graph built over the unified dataset.
 *
 * Node types: team, player, match, competition.
 * Edge types: HOME_IN / AWAY_IN (team -> match), WON / LOST / DREW
 * (team -> match), PLAYS_FOR (player -> team), HAS_NATIONALITY
 * (player -> country label), PLAYED_IN (match -> competition).
 */
import { Competition, Match, Player, Team, matchResult } from "./types.js";
import { Dataset } from "./dataset.js";

export type NodeType = "team" | "player" | "match" | "competition";
export type EdgeType =
  | "HOME_IN"
  | "AWAY_IN"
  | "WON"
  | "LOST"
  | "DREW"
  | "PLAYS_FOR"
  | "HAS_NATIONALITY"
  | "PLAYED_IN";

export interface GraphNode {
  id: string;
  type: NodeType;
  label: string;
}

export interface GraphEdge {
  from: string;
  to: string;
  type: EdgeType;
}

export class KnowledgeGraph {
  readonly nodes = new Map<string, GraphNode>();
  /** Adjacency: node id -> outgoing edges. */
  private outgoing = new Map<string, GraphEdge[]>();
  /** Adjacency: node id -> incoming edges. */
  private incoming = new Map<string, GraphEdge[]>();

  static teamNodeId(team: Team): string {
    return `team:${team.key}`;
  }

  static playerNodeId(player: Player): string {
    return `player:${player.id}`;
  }

  static matchNodeId(match: Match): string {
    return `match:${match.id}`;
  }

  static competitionNodeId(competition: Competition): string {
    return `competition:${competition}`;
  }

  private addNode(node: GraphNode): void {
    if (!this.nodes.has(node.id)) this.nodes.set(node.id, node);
  }

  private addEdge(edge: GraphEdge): void {
    if (!this.outgoing.has(edge.from)) this.outgoing.set(edge.from, []);
    this.outgoing.get(edge.from)!.push(edge);
    if (!this.incoming.has(edge.to)) this.incoming.set(edge.to, []);
    this.incoming.get(edge.to)!.push(edge);
  }

  /** Build the full graph from the loaded dataset. */
  static fromDataset(dataset: Dataset): KnowledgeGraph {
    const g = new KnowledgeGraph();

    for (const competition of Object.values(Competition)) {
      g.addNode({
        id: KnowledgeGraph.competitionNodeId(competition),
        type: "competition",
        label: competition,
      });
    }

    for (const team of dataset.teams.all()) {
      g.addNode({
        id: KnowledgeGraph.teamNodeId(team),
        type: "team",
        label: team.uf ? `${team.name} (${team.uf})` : team.name,
      });
    }

    for (const match of dataset.matches) {
      const matchId = KnowledgeGraph.matchNodeId(match);
      const score =
        match.homeGoals !== null && match.awayGoals !== null
          ? `${match.homeGoals}-${match.awayGoals}`
          : "not played";
      g.addNode({
        id: matchId,
        type: "match",
        label: `${match.date ?? "unknown date"}: ${match.homeTeam.name} ${score} ${match.awayTeam.name}`,
      });
      g.addEdge({ from: matchId, to: KnowledgeGraph.competitionNodeId(match.competition), type: "PLAYED_IN" });

      const homeId = KnowledgeGraph.teamNodeId(match.homeTeam);
      const awayId = KnowledgeGraph.teamNodeId(match.awayTeam);
      g.addEdge({ from: homeId, to: matchId, type: "HOME_IN" });
      g.addEdge({ from: awayId, to: matchId, type: "AWAY_IN" });

      const result = matchResult(match);
      if (result === "home") {
        g.addEdge({ from: homeId, to: matchId, type: "WON" });
        g.addEdge({ from: awayId, to: matchId, type: "LOST" });
      } else if (result === "away") {
        g.addEdge({ from: awayId, to: matchId, type: "WON" });
        g.addEdge({ from: homeId, to: matchId, type: "LOST" });
      } else if (result === "draw") {
        g.addEdge({ from: homeId, to: matchId, type: "DREW" });
        g.addEdge({ from: awayId, to: matchId, type: "DREW" });
      }
    }

    for (const player of dataset.players) {
      const playerId = KnowledgeGraph.playerNodeId(player);
      g.addNode({ id: playerId, type: "player", label: player.name });
      if (player.teamKey) {
        const team = dataset.teams.get(player.teamKey);
        if (team) {
          g.addEdge({ from: playerId, to: KnowledgeGraph.teamNodeId(team), type: "PLAYS_FOR" });
        }
      }
    }

    return g;
  }

  /** Neighbors of a node (both directions), optionally filtered by edge type. */
  neighbors(nodeId: string, edgeType?: EdgeType): { edge: GraphEdge; node: GraphNode }[] {
    const out: { edge: GraphEdge; node: GraphNode }[] = [];
    for (const e of this.outgoing.get(nodeId) ?? []) {
      if (edgeType && e.type !== edgeType) continue;
      const n = this.nodes.get(e.to);
      if (n) out.push({ edge: e, node: n });
    }
    for (const e of this.incoming.get(nodeId) ?? []) {
      if (edgeType && e.type !== edgeType) continue;
      const n = this.nodes.get(e.from);
      if (n) out.push({ edge: e, node: n });
    }
    return out;
  }

  degree(nodeId: string): number {
    return (this.outgoing.get(nodeId)?.length ?? 0) + (this.incoming.get(nodeId)?.length ?? 0);
  }
}
