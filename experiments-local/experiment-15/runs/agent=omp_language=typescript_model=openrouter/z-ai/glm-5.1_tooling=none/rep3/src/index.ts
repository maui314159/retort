import { createApp } from './app';
import { createDb } from './db';

const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;

const { app, db } = createApp(createDb('books.db'));

const server = app.listen(PORT, () => {
  console.log(`Book collection API running on port ${PORT}`);
});

process.on('SIGINT', () => {
  db.close();
  server.close();
  process.exit(0);
});

process.on('SIGTERM', () => {
  db.close();
  server.close();
  process.exit(0);
});
