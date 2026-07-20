//! Entry point for the book collection REST API.

use book_api::build_app;
use rusqlite::Connection;

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let bind_addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());

    let conn = Connection::open(&db_path).expect("failed to open database");
    let app = build_app(conn);

    let listener = tokio::net::TcpListener::bind(&bind_addr)
        .await
        .expect("failed to bind");
    println!("book-api listening on http://{bind_addr} (db: {db_path})");
    axum::serve(listener, app).await.expect("server error");
}
