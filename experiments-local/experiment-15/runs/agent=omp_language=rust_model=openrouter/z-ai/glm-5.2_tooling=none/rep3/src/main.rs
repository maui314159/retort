use book_collection::{build_router, db, AppState};
use rusqlite::Connection;
use std::sync::{Arc, Mutex};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();

    let conn = Connection::open("books.db")?;
    db::init(&conn)?;

    let state = AppState {
        conn: Arc::new(Mutex::new(conn)),
    };
    let app = build_router(state);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await?;
    tracing::info!("listening on http://0.0.0.0:3000");
    axum::serve(listener, app).await?;
    Ok(())
}
