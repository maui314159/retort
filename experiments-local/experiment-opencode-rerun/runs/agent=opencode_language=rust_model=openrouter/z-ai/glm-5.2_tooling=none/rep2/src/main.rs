use books_api::open_connection;
use tower_http::trace::TraceLayer;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db_path = std::env::var("BOOKS_DB_PATH").unwrap_or_else(|_| "books.db".to_string());
    let conn = open_connection(&db_path)?;
    let state = books_api::AppState::new(conn);
    let app = books_api::router(state).layer(TraceLayer::new_for_http());

    let addr = std::env::var("BOOKS_BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:3000".to_string());
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    println!("books-api listening on http://{}", addr);
    axum::serve(listener, app).await?;
    Ok(())
}
