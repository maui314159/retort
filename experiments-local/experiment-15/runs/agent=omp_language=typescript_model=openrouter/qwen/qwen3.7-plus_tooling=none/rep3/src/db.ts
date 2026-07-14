import sqlite3 from 'sqlite3';
import { open, Database } from 'sqlite';

let dbInstance: Database | null = null;

export async function getDb(): Promise<Database> {
  if (!dbInstance) {
    dbInstance = await open({
      filename: process.env.NODE_ENV === 'test' ? ':memory:' : 'books.db',
      driver: sqlite3.Database
    });
    
    await dbInstance.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      )
    `);
  }
  return dbInstance;
}

export async function resetDb() {
  if (dbInstance) {
    await dbInstance.close();
    dbInstance = null;
  }
}