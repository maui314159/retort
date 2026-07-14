/**
 * BDD specs for the MCP server tool layer.
 *
 * Verifies the server builds, all expected tools are registered, and a sample
 * tool call returns a content array with text payload. Uses an injected
 * (small) dataset to keep the test fast and deterministic.
 */

import { describe, expect } from 'vitest';
import { Given, When, Then } from './bdd.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { buildServer, setDataset } from '../src/server.js';
import type { Dataset } from '../src/types.js';

function fakeDataset(): Dataset {
  return {
    matches: [
      {
        competition: 'Brasileirao',
        date: '2019-10-27',
        rawDate: '2019-10-27',
        homeTeam: 'Flamengo',
        awayTeam: 'Grêmio',
        homeGoal: 5,
        awayGoal: 0,
        season: 2019,
        round: 28,
      },
      {
        competition: 'Brasileirao',
        date: '2019-09-03',
        rawDate: '2019-09-03',
        homeTeam: 'Flamengo',
        awayTeam: 'Fluminense',
        homeGoal: 2,
        awayGoal: 1,
        season: 2019,
        round: 22,
      },
    ],
    players: [
      {
        id: 1,
        name: 'Neymar Jr',
        nationality: 'Brazil',
        overall: 92,
        position: 'LW',
        club: 'Paris Saint-Germain',
      },
    ],
  };
}

async function withClient<T>(
  fn: (client: Client) => Promise<T>,
): Promise<T> {
  setDataset(fakeDataset());
  const server = buildServer();
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: 'test-client', version: '0.0.0' });
  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ]);
  try {
    return await fn(client);
  } finally {
    await client.close();
    await server.close();
  }
}

/** Extract the concatenated text payload from a tool result. */
function resultText(res: unknown): string {
  const content = (res as { content?: unknown }).content;
  if (!Array.isArray(content)) return '';
  return content
    .map((c) => (c as { text?: string }).text ?? '')
    .join('\n');
}

describe('Feature: MCP Server Tools', () => {
  Given('a running MCP server with an injected dataset', () => {
    When('I list available tools', () => {
      Then('all spec-required tools are registered', async () => {
        await withClient(async (client) => {
          const res = await client.listTools();
          const names = new Set(res.tools.map((t) => t.name));
          for (const expected of [
            'search_matches',
            'head_to_head',
            'team_stats',
            'search_players',
            'top_players',
            'standings',
            'champion',
            'relegated',
            'competition_stats',
            'biggest_wins',
            'list_competitions',
            'list_teams',
            'list_seasons',
          ]) {
            expect(names.has(expected)).toBe(true);
          }
        });
      });
    });

    When('I call search_matches for Flamengo', () => {
      Then('a content array with text is returned', async () => {
        await withClient(async (client) => {
          const res = await client.callTool({
            name: 'search_matches',
            arguments: { team: 'Flamengo' },
          });
          const text = resultText(res);
          expect(text.length).toBeGreaterThan(0);
          expect(text).toContain('Flamengo');
        });
      });
    });

    When('I call champion for Brasileirao 2019', () => {
      Then('the champion is Flamengo', async () => {
        await withClient(async (client) => {
          const res = await client.callTool({
            name: 'champion',
            arguments: { competition: 'Brasileirao', season: 2019 },
          });
          expect(resultText(res)).toContain('Flamengo');
        });
      });
    });

    When('I call top_players with nationality Brazil', () => {
      Then('Neymar appears in the result', async () => {
        await withClient(async (client) => {
          const res = await client.callTool({
            name: 'top_players',
            arguments: { nationality: 'Brazil', limit: 5 },
          });
          expect(resultText(res)).toContain('Neymar');
        });
      });
    });
  });
});
