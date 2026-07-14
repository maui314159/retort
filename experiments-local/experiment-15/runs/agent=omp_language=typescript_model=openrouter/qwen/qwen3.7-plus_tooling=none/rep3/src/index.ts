import express, { Express } from 'express';
import { getDb } from './db';
import booksRouter from './routes/books';

const app: Express = express();
app.use(express.json());

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});

app.use('/books', booksRouter);

export const startServer = async () => {
  await getDb();
  const PORT = process.env.PORT || 3000;
  return app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
  });
};

if (require.main === module) {
  startServer();
}

export default app;