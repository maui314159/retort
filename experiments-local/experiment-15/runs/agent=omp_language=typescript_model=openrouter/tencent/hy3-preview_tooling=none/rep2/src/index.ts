#!/usr/bin/env node
import { BookDatabase } from './db/database';
import { createApp } from './app';

const PORT: number = Number(process.env['PORT']) || 3000;
const DB_PATH: string = process.env['DB_PATH'] ?? ':memory:';

const db = new BookDatabase(DB_PATH);
const app = createApp(db);

app.listen(PORT, () => {
  console.log(`Book Collection API listening on port ${PORT}`);
});
