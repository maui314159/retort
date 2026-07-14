import { createApp } from './app';
import { BookStore } from './store';

const PORT = Number(process.env.PORT ?? 3000);
const DB_PATH = process.env.DB_PATH ?? 'books.db';

const store = new BookStore(DB_PATH);
const app = createApp(store);

app.listen(PORT, () => {
  console.log(`Book collection API listening on http://localhost:${PORT}`);
  console.log(`SQLite database at ${DB_PATH}`);
});

const shutdown = (signal: string) => {
  console.log(`\nReceived ${signal}, shutting down...`);
  store.close();
  process.exit(0);
};

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
