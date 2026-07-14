import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { join, dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

interface MCPResponse {
  jsonrpc: string;
  id: number;
  result?: any;
  error?: any;
}

async function sendMCPRequest(serverPath: string, request: any): Promise<MCPResponse> {
  return new Promise((resolve, reject) => {
    const proc = spawn('node', [serverPath], { stdio: ['pipe', 'pipe', 'pipe'] });

    let output = '';
    let stderr = '';

    proc.stdout.on('data', (data: Buffer) => {
      output += data.toString();
    });

    proc.stderr.on('data', (data: Buffer) => {
      stderr += data.toString();
    });

    proc.on('close', (code: number) => {
      const lines = output.trim().split('\n');
      const lastLine = lines[lines.length - 1];
      try {
        const response = JSON.parse(lastLine);
        resolve(response);
      } catch (e) {
        reject(new Error(`Failed to parse response: ${lastLine}\nStderr: ${stderr}`));
      }
    });

    // Send initialize request first
    const initRequest = {
      jsonrpc: '2.0',
      id: 0,
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'test', version: '1.0.0' },
      },
    };

    proc.stdin.write(JSON.stringify(initRequest) + '\n');

    // Send the actual request
    proc.stdin.write(JSON.stringify(request) + '\n');

    // Close stdin
    setTimeout(() => {
      proc.stdin.end();
    }, 100);
  });
}

async function runTests() {
  const serverPath = join(__dirname, '..', 'dist', 'index.js');
  let passed = 0;
  let failed = 0;

  console.log('Running Brazilian Soccer MCP Server Tests...\n');

  // Test 1: Initialize server
  try {
    const response = await sendMCPRequest(serverPath, {
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'test', version: '1.0.0' },
      },
    });

    if (response.result && response.result.serverInfo?.name === 'brazilian-soccer-mcp-server') {
      console.log('✓ Test 1 PASSED: Server initializes correctly');
      passed++;
    } else {
      console.log('✗ Test 1 FAILED: Server did not initialize correctly');
      failed++;
    }
  } catch (e: any) {
    console.log(`✗ Test 1 FAILED: ${e.message}`);
    failed++;
  }

  // Test 2: List tools
  try {
    const response = await sendMCPRequest(serverPath, {
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/list',
    });

    const tools = response.result?.tools || [];
    const expectedTools = [
      'find_matches_by_team',
      'get_team_stats',
      'search_players',
      'get_head_to_head',
      'get_competition_standings',
      'get_statistics',
      'find_matches_by_date',
    ];

    const allToolsPresent = expectedTools.every(tool =>
      tools.some((t: any) => t.name === tool)
    );

    if (allToolsPresent && tools.length === 7) {
      console.log('✓ Test 2 PASSED: All 7 tools are registered');
      passed++;
    } else {
      console.log(`✗ Test 2 FAILED: Expected 7 tools, got ${tools.length}`);
      failed++;
    }
  } catch (e: any) {
    console.log(`✗ Test 2 FAILED: ${e.message}`);
    failed++;
  }

  // Test 3: Find matches by team
  try {
    const response = await sendMCPRequest(serverPath, {
      jsonrpc: '2.0',
      id: 3,
      method: 'tools/call',
      params: {
        name: 'find_matches_by_team',
        arguments: { team: 'Flamengo' },
      },
    });

    const content = response.result?.content?.[0]?.text || '';
    if (content.includes('matches for Flamengo') && content.includes('Found')) {
      console.log('✓ Test 3 PASSED: Can find matches by team');
      passed++;
    } else {
      console.log('✗ Test 3 FAILED: Could not find matches');
      failed++;
    }
  } catch (e: any) {
    console.log(`✗ Test 3 FAILED: ${e.message}`);
    failed++;
  }

  // Test 4: Get team statistics
  try {
    const response = await sendMCPRequest(serverPath, {
      jsonrpc: '2.0',
      id: 4,
      method: 'tools/call',
      params: {
        name: 'get_team_stats',
        arguments: { team: 'Flamengo', season: 2023 },
      },
    });

    const content = response.result?.content?.[0]?.text || '';
    if (content.includes('Matches:') && content.includes('Wins:') && content.includes('Points:')) {
      console.log('✓ Test 4 PASSED: Can calculate team statistics');
      passed++;
    } else {
      console.log('✗ Test 4 FAILED: Could not calculate statistics');
      failed++;
    }
  } catch (e: any) {
    console.log(`✗ Test 4 FAILED: ${e.message}`);
    failed++;
  }

  // Test 5: Search players
  try {
    const response = await sendMCPRequest(serverPath, {
      jsonrpc: '2.0',
      id: 5,
      method: 'tools/call',
      params: {
        name: 'search_players',
        arguments: { nationality: 'Brazil', minOverall: 85 },
      },
    });

    const content = response.result?.content?.[0]?.text || '';
    if (content.includes('Found') && content.includes('players')) {
      console.log('✓ Test 5 PASSED: Can search player data');
      passed++;
    } else {
      console.log('✗ Test 5 FAILED: Could not search players');
      failed++;
    }
  } catch (e: any) {
    console.log(`✗ Test 5 FAILED: ${e.message}`);
    failed++;
  }

  // Test 6: Get head-to-head record
  try {
    const response = await sendMCPRequest(serverPath, {
      jsonrpc: '2.0',
      id: 6,
      method: 'tools/call',
      params: {
        name: 'get_head_to_head',
        arguments: { team1: 'Flamengo', team2: 'Fluminense' },
      },
    });

    const content = response.result?.content?.[0]?.text || '';
    if (content.includes('Head-to-Head') && content.includes('Wins:') && content.includes('Draws:')) {
      console.log('✓ Test 6 PASSED: Can compare teams head-to-head');
      passed++;
    } else {
      console.log('✗ Test 6 FAILED: Could not get head-to-head record');
      failed++;
    }
  } catch (e: any) {
    console.log(`✗ Test 6 FAILED: ${e.message}`);
    failed++;
  }

  // Test 7: Team name normalization
  try {
    const response1 = await sendMCPRequest(serverPath, {
      jsonrpc: '2.0',
      id: 7,
      method: 'tools/call',
      params: {
        name: 'find_matches_by_team',
        arguments: { team: 'Flamengo' },
      },
    });

    const response2 = await sendMCPRequest(serverPath, {
      jsonrpc: '2.0',
      id: 8,
      method: 'tools/call',
      params: {
        name: 'find_matches_by_team',
        arguments: { team: 'Flamengo-RJ' },
      },
    });

    const content1 = response1.result?.content?.[0]?.text || '';
    const content2 = response2.result?.content?.[0]?.text || '';

    const count1 = parseInt(content1.match(/Found (\d+) matches/)?.[1] || '0');
    const count2 = parseInt(content2.match(/Found (\d+) matches/)?.[1] || '0');

    if (count1 === count2 && count1 > 0) {
      console.log('✓ Test 7 PASSED: Handles team name variations correctly');
      passed++;
    } else {
      console.log(`✗ Test 7 FAILED: Team name variations not handled correctly (${count1} vs ${count2})`);
      failed++;
    }
  } catch (e: any) {
    console.log(`✗ Test 7 FAILED: ${e.message}`);
    failed++;
  }

  // Test 8: Properly formatted responses
  try {
    const response = await sendMCPRequest(serverPath, {
      jsonrpc: '2.0',
      id: 9,
      method: 'tools/call',
      params: {
        name: 'get_team_stats',
        arguments: { team: 'Flamengo' },
      },
    });

    const content = response.result?.content?.[0]?.text || '';
    const hasProperFormat = content.includes('Matches:') &&
                          content.includes('Wins:') &&
                          content.includes('Draws:') &&
                          content.includes('Losses:') &&
                          content.includes('Goals For:') &&
                          content.includes('Goals Against:');

    if (hasProperFormat) {
      console.log('✓ Test 8 PASSED: Returns properly formatted responses');
      passed++;
    } else {
      console.log('✗ Test 8 FAILED: Response not properly formatted');
      failed++;
    }
  } catch (e: any) {
    console.log(`✗ Test 8 FAILED: ${e.message}`);
    failed++;
  }

  // Test 9: All CSV files loadable
  try {
    const response = await sendMCPRequest(serverPath, {
      jsonrpc: '2.0',
      id: 10,
      method: 'tools/call',
      params: {
        name: 'find_matches_by_team',
        arguments: { team: 'Flamengo' },
      },
    });

    const content = response.result?.content?.[0]?.text || '';
    const matchCount = parseInt(content.match(/Found (\d+) matches/)?.[1] || '0');

    if (matchCount > 1000) {
      console.log(`✓ Test 9 PASSED: All CSV files are loadable (found ${matchCount} matches)`);
      passed++;
    } else {
      console.log(`✗ Test 9 FAILED: Not enough matches loaded (${matchCount})`);
      failed++;
    }
  } catch (e: any) {
    console.log(`✗ Test 9 FAILED: ${e.message}`);
    failed++;
  }

  // Test 10: Performance test - simple lookup < 2 seconds
  const start = Date.now();
  try {
    await sendMCPRequest(serverPath, {
      jsonrpc: '2.0',
      id: 11,
      method: 'tools/call',
      params: {
        name: 'find_matches_by_team',
        arguments: { team: 'Flamengo' },
      },
    });

    const duration = Date.now() - start;
    if (duration < 2000) {
      console.log(`✓ Test 10 PASSED: Simple lookup responds in < 2 seconds (${duration}ms)`);
      passed++;
    } else {
      console.log(`✗ Test 10 FAILED: Simple lookup took ${duration}ms`);
      failed++;
    }
  } catch (e: any) {
    console.log(`✗ Test 10 FAILED: ${e.message}`);
    failed++;
  }

  console.log(`\n=== Test Results: ${passed} passed, ${failed} failed ===`);
  return failed === 0;
}

runTests().then(success => {
  process.exit(success ? 0 : 1);
}).catch(e => {
  console.error('Test runner error:', e);
  process.exit(1);
});
