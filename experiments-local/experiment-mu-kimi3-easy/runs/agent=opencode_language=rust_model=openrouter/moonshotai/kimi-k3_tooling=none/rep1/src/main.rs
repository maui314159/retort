//! Book collection REST API — binary entry point.
//!
//! Configuration via environment variables:
//! - `DATABASE_PATH` — SQLite file path (default: `books.db`; use `:memory:`
//!   for an ephemeral in-memory database)
//! - `PORT` — listen port (default: `3000`)

use book_api::{build_router, db, AppState};
use rusqlite::Connection;

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let conn = Connection::open(&db_path).expect("failed to open database");
    db::init_schema(&conn).expect("failed to initialize schema");

    let app = build_router(AppState::new(conn));

    let port = std::env::var("PORT").unwrap_or_else(|_| "3000".to_string());
    let addr = format!("0.0.0.0:{port}");
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("failed to bind listener");
    println!("book-api listening on {addr} (database: {db_path})");

    axum::serve(listener, app).await.expect("server error");
}
