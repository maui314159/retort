use sqlx::SqlitePool;

/// Application state shared across all request handlers.
///
/// `SqlitePool` is internally reference-counted, so cloning is cheap.
#[derive(Clone)]
pub struct AppState {
    pub pool: SqlitePool,
}
