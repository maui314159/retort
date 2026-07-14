use sqlx::{sqlite::SqlitePoolOptions, SqlitePool};
use tracing::info;

pub type DbPool = SqlitePool;

pub async fn create_pool(database_url: &str) -> Result<DbPool, sqlx::Error> {
    info!("Connecting to database: {}", database_url);
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(database_url)
        .await?;

    info!("Running migrations...");
    sqlx::migrate!("./migrations")
        .run(&pool)
        .await?;
    info!("Migrations completed");

    Ok(pool)
}

#[cfg(test)]
pub async fn create_test_pool() -> Result<DbPool, sqlx::Error> {
    use tempfile::NamedTempFile;
    
    let temp_file = NamedTempFile::new().unwrap();
    let database_url = format!("sqlite:{}", temp_file.path().to_string_lossy());
    create_pool(&database_url).await
}