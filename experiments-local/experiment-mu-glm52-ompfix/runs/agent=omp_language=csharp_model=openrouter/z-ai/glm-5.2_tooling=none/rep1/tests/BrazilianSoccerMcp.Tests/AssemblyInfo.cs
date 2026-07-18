// Brazilian Soccer MCP Server - Test assembly configuration
//
// Context: xUnit runs test classes in parallel by default. Each test class
// creates its own SoccerDataService and loads the same ~40k CSV records. While
// concurrent file reads are safe, disabling parallelization avoids redundant
// simultaneous loads and makes test runs deterministic and faster overall.

using Xunit;

// Disable test parallelization so data-heavy tests don't contend on file I/O.
[assembly: CollectionBehavior(CollectionBehavior.CollectionPerAssembly, DisableTestParallelization = true)]
