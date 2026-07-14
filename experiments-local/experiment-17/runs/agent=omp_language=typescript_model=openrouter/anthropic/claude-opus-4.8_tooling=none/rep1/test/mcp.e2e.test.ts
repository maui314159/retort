/**
 * Context
 * =======
 * End-to-end MCP test: spawns the built server over stdio with a real MCP
 * client (the SDK's Client + StdioClientTransport) and exercises the tool
 * surface exactly as an LLM host would — listTools + callTool — asserting the
 * server boots, advertises every tool, and returns well-formed text answers
 * (including the spec's 2019-Flamengo standings example).
 *
 * Requires `npm run build` first (the transport launches dist/server.js). The
 * pretest hook in package.json builds automatically.
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

let client: Client;
let transport: StdioClientTransport;

function textOf(result: unknown): string {
  const content = (result as { content?: { type: string; text?: string }[] }).content ?? [];
  return content
    .filter((c) => c.type === 'text')
    .map((c) => c.text ?? '')
    .join('\n');
}

beforeAll(async () => {
  transport = new StdioClientTransport({
    command: process.execPath,
    args: ['dist/server.js'],
    env: { ...process.env, SOCCER_DATA_DIR: 'data/kaggle' },
  });
  client = new Client({ name: 'e2e-test', version: '1.0.0' });
  await client.connect(transport);
}, 60000);

afterAll(async () => {
  await client?.close();
});

describe('Feature: MCP server over stdio', () => {
  it('Given a running server, When I list tools, Then all query tools are advertised', async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name).sort();
    expect(names).toEqual(
      [
        'biggest_wins',
        'club_roster',
        'head_to_head',
        'league_stats',
        'list_competitions',
        'search_matches',
        'search_players',
        'standings',
        'team_record',
      ].sort(),
    );
  });

  it('Given the standings tool, When I ask for 2019 Brasileirão, Then Flamengo champions appear', async () => {
    const result = await client.callTool({
      name: 'standings',
      arguments: { competition: 'Brasileirão', season: 2019, limit: 5 },
    });
    const text = textOf(result);
    expect(text).toContain('Flamengo');
    expect(text).toContain('90 pts');
    expect(text).toContain('Champion');
  });

  it('Given the search_players tool, When I search Brazilian players, Then Neymar tops the list', async () => {
    const result = await client.callTool({
      name: 'search_players',
      arguments: { nationality: 'Brazil', limit: 3 },
    });
    expect(textOf(result)).toContain('Neymar Jr');
  });

  it('Given the head_to_head tool, When I compare Flamengo and Fluminense, Then a tally returns', async () => {
    const result = await client.callTool({
      name: 'head_to_head',
      arguments: { teamA: 'Flamengo', teamB: 'Fluminense', limit: 5 },
    });
    const text = textOf(result);
    expect(text).toContain('Flamengo');
    expect(text).toContain('Head-to-head');
  });

  it('Given the search_matches tool, When I query Palmeiras 2022, Then matches return', async () => {
    const result = await client.callTool({
      name: 'search_matches',
      arguments: { team: 'Palmeiras', season: 2022, competition: 'Brasileirão', limit: 5 },
    });
    expect(textOf(result)).toMatch(/Palmeiras/);
  });
});
