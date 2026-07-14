import express from 'express';
import { BookDatabase } from './models/database';
import { createBookRoutes } from './routes/bookRoutes';
const app = express();
const PORT = process.env.PORT || 3000;

// Initialize database
const db = new BookDatabase();
db.initialize(':memory:');

// Middleware
app.use(express.json());

// Routes
app.use('/', createBookRoutes(db));

// Error handling middleware
app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error('Unhandled error:', err.message);
  res.status(500).json({ error: 'Internal server error' });
});

// Start server if not in test mode
if (process.env.NODE_ENV !== 'test') {
  app.listen(PORT, () => {
    console.log(`Book Collection API server running on port ${PORT}`);
  });
}

export { app, db };
