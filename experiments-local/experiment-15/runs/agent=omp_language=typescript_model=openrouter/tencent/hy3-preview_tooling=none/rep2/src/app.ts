import express from 'express';
import { BookDatabase } from './db/database';
import { createBookRouter } from './routes/books';

export function createApp(db: BookDatabase): express.Express {
  const app = express();
  app.use(express.json());
  app.use('/', createBookRouter(db));
  app.get('/health', (_req, _res) => {
    const ok = db.healthCheck();
    _res.status(ok ? 200 : 503).json({ status: ok ? 'ok' : 'error' });
  });
  return app;
}
