use std::sync::Arc;

use book_api::{build_app, init_db, AppState};
use rusqlite::Connection;
use tokio::sync::Mutex;

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let conn = Connection::open(&db_path).expect("open database");
    init_db(&conn).expect("initialize database");

    let state = AppState {
        conn: Arc::new(Mutex::new(conn)),
    };
    let app = build_app(state);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .expect("bind listener");

    axum::serve(listener, app)
        .await
        .expect("run server");
}
