using BrazilianSoccerMcpServer.Services;
using BrazilianSoccerMcpServer.Tools;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = Host.CreateDefaultBuilder(args);

builder.ConfigureServices(services =>
{
    var dataDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "data", "kaggle");
    if (!Directory.Exists(dataDir))
    {
        var currentDir = Directory.GetCurrentDirectory();
        var candidate = Path.Combine(currentDir, "data", "kaggle");
        if (Directory.Exists(candidate))
        {
            dataDir = candidate;
        }
        else
        {
            for (int i = 0; i < 3; i++)
            {
                candidate = Path.Combine(currentDir, "data", "kaggle");
                if (Directory.Exists(candidate))
                {
                    dataDir = candidate;
                    break;
                }
                currentDir = Path.GetDirectoryName(currentDir) ?? "";
                if (string.IsNullOrEmpty(currentDir)) break;
            }
        }
    }

    var dataStore = new BrazilianSoccerDataStore();
    dataStore.LoadFromDirectory(dataDir);

    services.AddSingleton(dataStore);
    services.AddMcpServer()
        .WithTools<SoccerTools>();
});

var app = builder.Build();
await app.RunAsync();
