using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace BrazilianSoccerMCP.MCP
{
    /// <summary>
    /// Simple MCP server implementation
    /// </summary>
    public class MCPServer
    {
        private readonly DataLoader _dataLoader;
        private readonly QueryEngine _queryEngine;
        private List<SoccerMatch>? _matches;
        private List<SoccerPlayer>? _players;
        private bool _initialized = false;
        
        public MCPServer()
        {
            _dataLoader = new DataLoader();
            _queryEngine = new QueryEngine();
        }
        
        /// <summary>
        /// Run the MCP server (reads from stdin, writes to stdout)
        /// </summary>
        public async Task RunAsync(CancellationToken cancellationToken = default)
        {
            Console.Error.WriteLine("Brazilian Soccer MCP Server starting...");
            
            var serializerOptions = new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
                DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull
            };
            
            // Process messages line by line from stdin
            string? line;
            while (!cancellationToken.IsCancellationRequested && 
                   (line = await Console.In.ReadLineAsync()) != null)
            {
                try
                {
                    var message = JsonSerializer.Deserialize<MCPMessage>(line, serializerOptions);
                    if (message == null)
                    {
                        Console.Error.WriteLine("Error: Failed to parse message");
                        continue;
                    }
                    
                    var response = await ProcessMessageAsync(message, cancellationToken);
                    var responseJson = JsonSerializer.Serialize(response, serializerOptions);
                    await Console.Out.WriteLineAsync(responseJson);
                    await Console.Out.FlushAsync();
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine($"Error processing message: {ex.Message}");
                    
                    var errorResponse = new MCPMessage
                    {
                        Id = null,
                        Error = new MCPError
                        {
                            Code = -32603,
                            Message = $"Internal error: {ex.Message}"
                        }
                    };
                    
                    var errorJson = JsonSerializer.Serialize(errorResponse, serializerOptions);
                    await Console.Out.WriteLineAsync(errorJson);
                    await Console.Out.FlushAsync();
                }
            }
        }
        
        private async Task<MCPMessage> ProcessMessageAsync(MCPMessage message, CancellationToken cancellationToken)
        {
            // Load data on first request
            if (!_initialized)
            {
                Console.Error.WriteLine("Loading data...");
                _matches = _dataLoader.LoadMatches();
                _players = _dataLoader.LoadPlayers();
                _queryEngine.Initialize(_matches, _players);
                _initialized = true;
                Console.Error.WriteLine($"Data loaded: {_matches.Count} matches, {_players.Count} players");
            }
            
            switch (message.Method)
            {
                case "initialize":
                    return HandleInitialize(message);
                    
                case "tools/list":
                    return HandleListTools(message);
                    
                case "tools/call":
                    return await HandleCallTool(message, cancellationToken);
                    
                case "ping":
                    return HandlePing(message);
                    
                case "shutdown":
                    return HandleShutdown(message);
                    
                default:
                    return new MCPMessage
                    {
                        Id = message.Id,
                        Error = new MCPError
                        {
                            Code = -32601,
                            Message = $"Method not found: {message.Method}"
                        }
                    };
            }
        }
        
        private MCPMessage HandleInitialize(MCPMessage message)
        {
            Console.Error.WriteLine("Received initialize request");
            
            var result = new MCPMessage
            {
                Id = message.Id,
                Result = new MCPInitializeResult
                {
                    ProtocolVersion = "2024-11-05",
                    Capabilities = new MCPServerCapabilities
                    {
                        Tools = new MCPServerToolCapabilities
                        {
                            ListChanged = false
                        }
                    },
                    ServerInfo = new MCPServerInfo
                    {
                        Name = "brazilian-soccer-mcp",
                        Version = "1.0.0"
                    }
                }
            };
            
            return result;
        }
        
        private MCPMessage HandleListTools(MCPMessage message)
        {
            Console.Error.WriteLine("Received list tools request");
            
            var tools = GetTools();
            
            var result = new MCPMessage
            {
                Id = message.Id,
                Result = new MCPListToolsResult
                {
                    Tools = tools
                }
            };
            
            return result;
        }
        
        private async Task<MCPMessage> HandleCallTool(MCPMessage message, CancellationToken cancellationToken)
        {
            if (message.Params is not JsonElement paramsElement)
            {
                return new MCPMessage
                {
                    Id = message.Id,
                    Error = new MCPError
                    {
                        Code = -32602,
                        Message = "Invalid params"
                    }
                };
            }
            
            var callParams = paramsElement.Deserialize<MCPCallToolParams>();
            if (callParams == null)
            {
                return new MCPMessage
                {
                    Id = message.Id,
                    Error = new MCPError
                    {
                        Code = -32602,
                        Message = "Invalid call tool params"
                    }
                };
            }
            
            Console.Error.WriteLine($"Calling tool: {callParams.Name}");
            
            try
            {
                var content = await ExecuteToolAsync(callParams.Name, callParams.Arguments, cancellationToken);
                
                return new MCPMessage
                {
                    Id = message.Id,
                    Result = new MCPCallToolResult
                    {
                        Content = new List<MCPContent>
                        {
                            new MCPContent
                            {
                                Type = "text",
                                Text = content
                            }
                        }
                    }
                };
            }
            catch (Exception ex)
            {
                return new MCPMessage
                {
                    Id = message.Id,
                    Error = new MCPError
                    {
                        Code = -32000,
                        Message = $"Tool execution error: {ex.Message}"
                    }
                };
            }
        }
        
        private MCPMessage HandlePing(MCPMessage message)
        {
            return new MCPMessage
            {
                Id = message.Id,
                Result = new { }
            };
        }
        
        private MCPMessage HandleShutdown(MCPMessage message)
        {
            Console.Error.WriteLine("Received shutdown request");
            Environment.Exit(0);
            return new MCPMessage
            {
                Id = message.Id,
                Result = new { }
            };
        }
        
        private List<MCPTool> GetTools()
        {
            return new List<MCPTool>
            {
                // Match queries
                new MCPTool
                {
                    Name = "search_matches",
                    Description = "Search for soccer matches by various criteria (team, date, competition, season)",
                    InputSchema = new MCPSchema
                    {
                        Type = "object",
                        Properties = new Dictionary<string, MCPSchemaProperty>
                        {
                            ["team"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Team name to search for (home or away)"
                            },
                            ["homeTeam"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Home team name"
                            },
                            ["awayTeam"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Away team name"
                            },
                            ["team1"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "First team for head-to-head search"
                            },
                            ["team2"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Second team for head-to-head search"
                            },
                            ["startDate"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Start date (YYYY-MM-DD)"
                            },
                            ["endDate"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "End date (YYYY-MM-DD)"
                            },
                            ["competition"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Competition name (Brasileirão, Copa do Brasil, Libertadores)",
                                Enum = new List<string> { "Brasileirão", "Copa do Brasil", "Libertadores", "All" }
                            },
                            ["season"] = new MCPSchemaProperty
                            {
                                Type = "integer",
                                Description = "Season year"
                            },
                            ["limit"] = new MCPSchemaProperty
                            {
                                Type = "integer",
                                Description = "Maximum number of matches to return (default: 20)"
                            }
                        },
                        Required = new List<string>()
                    }
                },
                
                // Team queries
                new MCPTool
                {
                    Name = "get_team_stats",
                    Description = "Get team statistics (wins, losses, goals, etc.)",
                    InputSchema = new MCPSchema
                    {
                        Type = "object",
                        Properties = new Dictionary<string, MCPSchemaProperty>
                        {
                            ["team"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Team name"
                            },
                            ["season"] = new MCPSchemaProperty
                            {
                                Type = "integer",
                                Description = "Season year (optional)"
                            },
                            ["competition"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Competition name (optional)"
                            },
                            ["includeHomeAway"] = new MCPSchemaProperty
                            {
                                Type = "boolean",
                                Description = "Include home/away split (default: true)"
                            }
                        },
                        Required = new List<string> { "team" }
                    }
                },
                
                // Player queries
                new MCPTool
                {
                    Name = "search_players",
                    Description = "Search for players by name, nationality, club, or position",
                    InputSchema = new MCPSchema
                    {
                        Type = "object",
                        Properties = new Dictionary<string, MCPSchemaProperty>
                        {
                            ["name"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Player name (partial match)"
                            },
                            ["nationality"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Nationality (e.g., Brazil)"
                            },
                            ["club"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Club name (partial match)"
                            },
                            ["position"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Position (e.g., ST, LW, GK)"
                            },
                            ["minRating"] = new MCPSchemaProperty
                            {
                                Type = "integer",
                                Description = "Minimum overall rating"
                            },
                            ["maxRating"] = new MCPSchemaProperty
                            {
                                Type = "integer",
                                Description = "Maximum overall rating"
                            },
                            ["limit"] = new MCPSchemaProperty
                            {
                                Type = "integer",
                                Description = "Maximum number of players to return (default: 20)"
                            }
                        },
                        Required = new List<string>()
                    }
                },
                
                // Competition queries
                new MCPTool
                {
                    Name = "get_competition_standings",
                    Description = "Get competition standings for a season",
                    InputSchema = new MCPSchema
                    {
                        Type = "object",
                        Properties = new Dictionary<string, MCPSchemaProperty>
                        {
                            ["competition"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Competition name",
                                Enum = new List<string> { "Brasileirão", "Copa do Brasil", "Libertadores" }
                            },
                            ["season"] = new MCPSchemaProperty
                            {
                                Type = "integer",
                                Description = "Season year"
                            },
                            ["limit"] = new MCPSchemaProperty
                            {
                                Type = "integer",
                                Description = "Maximum number of teams to return (default: all)"
                            }
                        },
                        Required = new List<string> { "competition", "season" }
                    }
                },
                
                // Head-to-head
                new MCPTool
                {
                    Name = "get_head_to_head",
                    Description = "Get head-to-head record between two teams",
                    InputSchema = new MCPSchema
                    {
                        Type = "object",
                        Properties = new Dictionary<string, MCPSchemaProperty>
                        {
                            ["team1"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "First team name"
                            },
                            ["team2"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Second team name"
                            },
                            ["competition"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Competition filter (optional)"
                            },
                            ["startDate"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Start date filter (optional)"
                            },
                            ["endDate"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "End date filter (optional)"
                            }
                        },
                        Required = new List<string> { "team1", "team2" }
                    }
                },
                
                // Statistical analysis
                new MCPTool
                {
                    Name = "get_statistics",
                    Description = "Get aggregated statistics",
                    InputSchema = new MCPSchema
                    {
                        Type = "object",
                        Properties = new Dictionary<string, MCPSchemaProperty>
                        {
                            ["statistic"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Statistic to calculate",
                                Enum = new List<string> { 
                                    "average_goals", 
                                    "home_win_rate", 
                                    "draw_rate",
                                    "biggest_wins",
                                    "most_common_score",
                                    "team_with_most_wins",
                                    "team_with_most_goals",
                                    "top_scorers"  // Note: requires inference from match data
                                }
                            },
                            ["competition"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Competition filter (optional)"
                            },
                            ["season"] = new MCPSchemaProperty
                            {
                                Type = "integer",
                                Description = "Season filter (optional)"
                            },
                            ["limit"] = new MCPSchemaProperty
                            {
                                Type = "integer",
                                Description = "Maximum results (default: 10)"
                            }
                        },
                        Required = new List<string> { "statistic" }
                    }
                },
                
                // General info
                new MCPTool
                {
                    Name = "get_data_info",
                    Description = "Get information about loaded data",
                    InputSchema = new MCPSchema
                    {
                        Type = "object",
                        Properties = new Dictionary<string, MCPSchemaProperty>
                        {
                            ["info"] = new MCPSchemaProperty
                            {
                                Type = "string",
                                Description = "Type of information",
                                Enum = new List<string> { 
                                    "summary", 
                                    "teams", 
                                    "competitions", 
                                    "seasons",
                                    "player_count",
                                    "match_count"
                                }
                            }
                        },
                        Required = new List<string> { "info" }
                    }
                }
            };
        }
        
        private async Task<string> ExecuteToolAsync(string toolName, Dictionary<string, object> arguments, CancellationToken cancellationToken)
        {
            await Task.Yield(); // Allow async
            
            switch (toolName)
            {
                case "search_matches":
                    return ExecuteSearchMatches(arguments);
                    
                case "get_team_stats":
                    return ExecuteGetTeamStats(arguments);
                    
                case "search_players":
                    return ExecuteSearchPlayers(arguments);
                    
                case "get_competition_standings":
                    return ExecuteGetCompetitionStandings(arguments);
                    
                case "get_head_to_head":
                    return ExecuteGetHeadToHead(arguments);
                    
                case "get_statistics":
                    return ExecuteGetStatistics(arguments);
                    
                case "get_data_info":
                    return ExecuteGetDataInfo(arguments);
                    
                default:
                    throw new ArgumentException($"Unknown tool: {toolName}");
            }
        }
        
        private string ExecuteSearchMatches(Dictionary<string, object> arguments)
        {
            return _queryEngine.SearchMatches(arguments);
        }
        
        private string ExecuteGetTeamStats(Dictionary<string, object> arguments)
        {
            return _queryEngine.GetTeamStats(arguments);
        }
        
        private string ExecuteSearchPlayers(Dictionary<string, object> arguments)
        {
            return _queryEngine.SearchPlayers(arguments);
        }
        
        private string ExecuteGetCompetitionStandings(Dictionary<string, object> arguments)
        {
            return _queryEngine.GetCompetitionStandings(arguments);
        }
        
        private string ExecuteGetHeadToHead(Dictionary<string, object> arguments)
        {
            return _queryEngine.GetHeadToHead(arguments);
        }
        
        private string ExecuteGetStatistics(Dictionary<string, object> arguments)
        {
            return _queryEngine.GetStatistics(arguments);
        }
        
        private string ExecuteGetDataInfo(Dictionary<string, object> arguments)
        {
            return _queryEngine.GetDataInfo(arguments);
        }
    }
}