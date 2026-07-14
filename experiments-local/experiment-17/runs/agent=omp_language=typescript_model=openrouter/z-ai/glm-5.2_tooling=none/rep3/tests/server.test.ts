/**
 * brazilian-soccer-mcp / tests/server.test.ts
 *
 * BDD test for the MCP server tool wiring.
 *
 * Context block:
 * Drives the real MCP protocol over an in-memory transport pair: a `Client`
 * connects to the `McpServer` returned by `createServer()`, then lists and
 * calls tools. This verifies the full contract between the query layer and
 * the MCP tool surface (tool registration, input validation, and text result
 * formatting) without touching stdio.
 */

import { describe, it, expect } from 'vitest';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { createServer } from '../src/server.js';

const REQUIRED_TOOLS = [
  'search_matches',
  'head_to_head',
  'team_stats',
  'standings',
  'aggregate_stats',
  'biggest_wins',
  'search_players',
  'brazilian_clubs_summary',
] as const;

async function connectClient() {
  const server = createServer();
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await server.connect(serverTransport);
  const client = new Client({ name: 'test-client', version: '1.0.0' });
  await client.connect(clientTransport);
  return { server, client };
}

describe('Feature: MCP Server Tools', () => {
  /*
   * Scenario: The server advertises the required tools
   *   Given createServer() builds the server
   *   When the client lists tools
   *   Then all eight capability tools are present
   */
  it('registers the eight required tools', async () => {
    const { client } = await connectClient();
    const result = await client.listTools();
    const names = result.tools.map((t) => t.name);
    for (const name of REQUIRED_TOOLS) {
      expect(names).toContain(name);
    }
    expect(result.tools.length).toBeGreaterThanOrEqual(REQUIRED_TOOLS.length);
    await client.close();
  });

  /*
   * Scenario: Calling search_matches returns text content
   *   Given the server is connected
   *   When I call search_matches with team Flamengo
   *   Then the result content is text and mentions Flamengo
   */
  it('returns formatted text from search_matches', async () => {
    const { client } = await connectClient();
    const result = await client.callTool({
      name: 'search_matches',
      arguments: { team: 'Flamengo', limit: 3 },
    });
    expect(result.content).toBeDefined();
    const textPart = result.content.find((c) => c.type === 'text');
    expect(textPart).toBeDefined();
    if (textPart && textPart.type === 'text') {
      expect(textPart.text).toContain('Flamengo');
    }
    await client.close();
  });

  /*
   * Scenario: Calling search_players returns ranked players
   *   Given the server is connected
   *   When I call search_players for nationality Brazil limit 3
   *   Then the result text lists players with Overall ratings
   */
  it('returns player list from search_players', async () => {
    const { client } = await connectClient();
    const result = await client.callTool({
      name: 'search_players',
      arguments: { nationality: 'Brazil', limit: 3 },
    });
    const textPart = result.content.find((c) => c.type === 'text');
    expect(textPart).toBeDefined();
    if (textPart && textPart.type === 'text') {
      expect(textPart.text).toContain('Overall');
    }
    await client.close();
  });
});
