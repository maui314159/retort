use sqlx::sqlite::{SqlitePool, SqlitePoolOptions};

pub async fn init_pool(url: &str) -> SqlitePool {
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(url)
        .await
        .expect("failed to connect to sqlite");

    sqlx::migrate!()
        .run(&pool)
        .await
        .expect("failed to run migrations");

    pool
}

#[allow(dead_code)]
pub async fn ensure_schema(pool: &SqlitePool) {
    // Fallback in case migrations dir is not bundled (e.g. tests).
    let _ = sqlx::query(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )",
    )
    .execute(pool)
    .await;
}
