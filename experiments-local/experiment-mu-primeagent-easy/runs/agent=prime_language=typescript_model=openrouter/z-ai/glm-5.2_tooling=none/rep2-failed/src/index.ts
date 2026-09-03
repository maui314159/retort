import { createApp } from "./app";
import { getDb } from "./db";

const app = createApp();
const PORT = parseInt(process.env.PORT ?? "3000", 10);

// Initialize the database
getDb();

app.listen(PORT, () => {
  console.log(`Book Collection API is running on http://localhost:${PORT}`);
});

export default app;
