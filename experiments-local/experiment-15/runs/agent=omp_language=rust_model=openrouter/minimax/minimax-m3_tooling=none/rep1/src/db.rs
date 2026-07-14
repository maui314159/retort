use sqlx::{sqlite::SqlitePoolOptions, SqlitePool};

/// Connect to the SQLite database referenced by `database_url`.
///
/// Use `sqlite::memory:` for an in-memory database (handy in tests), and
/// `sqlite://path/to/db` (or `sqlite:path/to.db`) for a file-backed store.
pub async fn init_pool(database_url: &str) -> Result<SqlitePool, sqlx::Error> {
    SqlitePoolOptions::new()
        .max_connections(5)
        .connect(database_url)
        .await
}

/// Create the `books` table on an existing pool. Idempotent.
pub async fn init_schema(pool: &SqlitePool) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS books (
            id     TEXT PRIMARY KEY NOT NULL,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )
        "#,
    )
    .execute(pool)
    .await?;
    Ok(())
}

/// Convenience: connect to `database_url` and run schema setup.
pub async fn init(database_url: &str) -> Result<SqlitePool, sqlx::Error> {
    let pool = init_pool(database_url).await?;
    init_schema(&pool).await?;
    Ok(pool)
}
