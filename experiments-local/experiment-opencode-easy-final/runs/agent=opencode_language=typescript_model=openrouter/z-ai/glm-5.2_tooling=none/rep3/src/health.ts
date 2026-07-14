import { Router, type Response } from "express";
import { getDb } from "./db.js";

export const healthRouter = Router();

healthRouter.get("/", (_req, res: Response) => {
  try {
    const db = getDb();
    db.prepare("SELECT 1").get();
    res.status(200).json({ status: "ok", db: "connected" });
  } catch (err) {
    res.status(503).json({ status: "fail", db: "disconnected", error: (err as Error).message });
  }
});
