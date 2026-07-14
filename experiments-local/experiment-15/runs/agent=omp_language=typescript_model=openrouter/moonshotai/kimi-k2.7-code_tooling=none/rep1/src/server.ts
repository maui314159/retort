import { createApp } from "./app.js";
import { initDatabase } from "./db.js";

const PORT = Number(process.env.PORT ?? 3000);

async function main(): Promise<void> {
  await initDatabase();
  const app = createApp();

  app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
  });
}

main().catch((err) => {
  console.error("Failed to start server:", err);
  process.exit(1);
});
