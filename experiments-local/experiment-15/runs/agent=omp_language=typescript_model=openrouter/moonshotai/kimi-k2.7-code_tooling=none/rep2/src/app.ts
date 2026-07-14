import express from 'express';
import booksRouter from './routes/books';

const app = express();

app.use(express.json());

app.get('/health', (_req, res) => {
  res.status(200).json({ status: 'ok' });
});

app.use('/books', booksRouter);

export default app;
