using System;

namespace BrazilianSoccerMCP.Tests
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("Brazilian Soccer MCP - Test Runner");
            Console.WriteLine("===================================\n");
            
            var tests = new Tests();
            
            if (args.Length > 0 && args[0] == "samples")
            {
                tests.TestSampleQueries();
            }
            else if (args.Length > 0 && args[0] == "server")
            {
                // Run as MCP server
                RunAsServer();
            }
            else
            {
                tests.RunAllTests();
            }
            
            Console.WriteLine("\nPress any key to exit...");
            Console.ReadKey();
        }
        
        static void RunAsServer()
        {
            Console.WriteLine("Starting MCP server...");
            Console.WriteLine("Note: MCP server mode requires stdin/stdout communication");
            Console.WriteLine("This mode is intended to be run by an MCP client.");
            
            var server = new MCP.MCPServer();
            var cts = new System.Threading.CancellationTokenSource();
            
            Console.CancelKeyPress += (s, e) =>
            {
                e.Cancel = true;
                cts.Cancel();
            };
            
            try
            {
                server.RunAsync(cts.Token).Wait();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Server error: {ex.Message}");
            }
        }
    }
}