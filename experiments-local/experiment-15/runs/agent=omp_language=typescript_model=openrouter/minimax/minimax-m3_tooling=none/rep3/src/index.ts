import { createApp } from "./app.js";

const port = Number(process.env.PORT ?? 3000);

const { app } = createApp();

const server = app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`book-collection-api listening on http://localhost:${port}`);
});

function shutdown(signal: string): void {
  // eslint-disable-next-line no-console
  console.log(`received ${signal}, shutting down`);
  server.close(() => process.exit(0));
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
