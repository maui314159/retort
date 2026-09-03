import { describe, it, expect } from "vitest";
import request from "supertest";
import { createApp } from "../src/app.js";
import { BookStore } from "../src/db.js";

describe("GET /health", () => {
  it("returns ok status", async () => {
    const app = createApp({ store: new BookStore(":memory:") });
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});
