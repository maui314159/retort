import type { Express } from "express";
import request from "supertest";
import { openDatabase, createRepository, type BookRepository } from "../src/db.js";
import { createApp } from "../src/app.js";

export interface TestContext {
  app: Express;
  repo: BookRepository;
  close: () => void;
}

export function buildTestApp(): TestContext {
  const db = openDatabase(":memory:");
  const repo = createRepository(db);
  const app = createApp({ repository: repo });
  return {
    app,
    repo,
    close: () => {
      repo.close();
    },
  };
}

export function get(app: Express, path: string) {
  return request(app).get(path);
}

export function post(app: Express, path: string, body: unknown) {
  return request(app).post(path).send(body);
}

export function put(app: Express, path: string, body: unknown) {
  return request(app).put(path).send(body);
}

export function del(app: Express, path: string) {
  return request(app).delete(path);
}
