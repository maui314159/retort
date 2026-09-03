import { createApp } from "./app";

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "0.0.0.0";

const app = createApp();

const server = app.listen(PORT, HOST, () => {
  console.log(`Book collection API listening on http://${HOST}:${PORT}`);
});

// Graceful shutdown: close the HTTP server so in-flight requests finish.
const shutdown = (signal: string): void => {
  console.log(`\nReceived ${signal}, shutting down...`);
  server.close(() => {
    console.log("HTTP server closed.");
    process.exit(0);
  });
};

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
