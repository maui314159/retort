import { createApp } from './app.js';
import { openBookStore } from './db.js';

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? '127.0.0.1';
const DB_PATH = process.env.DB_PATH ?? 'books.db';

const { app } = createApp({ store: openBookStore(DB_PATH) });

const server = app.listen(PORT, HOST, () => {
  // eslint-disable-next-line no-console
  console.log(`Book API listening on http://${HOST}:${PORT}`);
});

const shutdown = (signal: string): void => {
  // eslint-disable-next-line no-console
  console.log(`Received ${signal}, shutting down`);
  server.close(() => process.exit(0));
};
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
