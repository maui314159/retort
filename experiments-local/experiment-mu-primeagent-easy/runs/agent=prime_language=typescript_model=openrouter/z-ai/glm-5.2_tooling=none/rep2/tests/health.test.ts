import { describe, it, expect } from "vitest";
import request from "supertest";
import { createApp } from "../src/app";
import type { Express } from "express";

const app: Express = createApp();

describe("Health Check", () => {
  it("should return status ok", async () => {
    const res = await request(app).get("/health");

    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });

  it("should return 404 for unknown routes", async () => {
    const res = await request(app).get("/nonexistent");

    expect(res.status).toBe(404);
    expect(res.body).toHaveProperty("error", "Not found");
  });
});
