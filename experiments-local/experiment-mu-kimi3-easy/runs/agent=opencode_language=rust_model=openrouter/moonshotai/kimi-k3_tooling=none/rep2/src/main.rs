use std::sync::Arc;

use book_collection_api::{build_router, init_db, AppState};

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_PATH").unwrap_or_else(|_| "books.db".to_string());
    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".to_string());

    let conn = init_db(&db_path).expect("failed to initialize database");
    let app = build_router(Arc::new(AppState::new(conn)));

    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("failed to bind listener");
    println!("book-collection-api listening on http://{addr}");

    axum::serve(listener, app).await.expect("server error");
}
