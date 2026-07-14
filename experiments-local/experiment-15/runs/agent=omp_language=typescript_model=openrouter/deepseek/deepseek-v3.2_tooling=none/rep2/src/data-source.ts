import 'reflect-metadata';
import { DataSource } from 'typeorm';
import { Book } from './entities/Book';
import dotenv from 'dotenv';

dotenv.config();

export const AppDataSource = new DataSource({
  type: 'better-sqlite3',
  database: process.env.DB_PATH || './database.sqlite',
  synchronize: process.env.NODE_ENV !== 'production',
  logging: process.env.NODE_ENV === 'development',
  entities: [Book],
  subscribers: [],
  migrations: [],
});