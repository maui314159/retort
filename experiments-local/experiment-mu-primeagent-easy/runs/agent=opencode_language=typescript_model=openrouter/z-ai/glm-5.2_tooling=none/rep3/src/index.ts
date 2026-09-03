import { createApp } from "./app";

const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
const DB_PATH = process.env.DB_PATH ?? "books.db";

const { app } = createApp({ dbPath: DB_PATH });

app.listen(PORT, () => {
  console.log(`Book API listening on http://localhost:${PORT}`);
});
