use book_api::{app, init_db};
use sqlx::SqlitePool;

#[tokio::main]
async fn main() -> sqlx::Result<()> {
    let pool = SqlitePool::connect("sqlite:books.db").await?;
    init_db(&pool).await?;

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    println!("Listening on {}", listener.local_addr().unwrap());
    axum::serve(listener, app(pool)).await.unwrap();
    Ok(())
}
