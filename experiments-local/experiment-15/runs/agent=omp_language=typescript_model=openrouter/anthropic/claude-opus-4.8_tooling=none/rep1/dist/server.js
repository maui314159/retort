"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const app_1 = require("./app");
const db_1 = require("./db");
const PORT = Number(process.env.PORT ?? 3000);
const DB_PATH = process.env.DB_PATH ?? "books.db";
const store = new db_1.BookStore(DB_PATH);
const app = (0, app_1.createApp)(store);
const server = app.listen(PORT, () => {
    console.log(`Book collection API listening on http://localhost:${PORT}`);
});
function shutdown() {
    server.close(() => {
        store.close();
        process.exit(0);
    });
}
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
