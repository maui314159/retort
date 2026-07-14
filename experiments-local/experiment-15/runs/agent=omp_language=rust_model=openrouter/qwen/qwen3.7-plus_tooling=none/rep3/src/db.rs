use rusqlite::{Connection, Result};
use std::sync::Arc;
use tokio::sync::Mutex;

pub type DbPool = Arc<Mutex<Connection>>;

pub fn init_db(db_path: &str) -> Result<Connection> {
    let conn = Connection::open(db_path)?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
        [],
    )?;
    Ok(conn)
}