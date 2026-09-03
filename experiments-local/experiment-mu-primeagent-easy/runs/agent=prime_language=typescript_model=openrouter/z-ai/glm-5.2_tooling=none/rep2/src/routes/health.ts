import { Router, Request, Response } from "express";

const router = Router();

// GET /health — health check endpoint
router.get("/", (_req: Request, res: Response) => {
  res.status(200).json({ status: "ok" });
});

export default router;
