use book_api::{build_app, init_db, make_pool, AppState};
use std::net::SocketAddr;

#[tokio::main]
async fn main() {
    let db_path = std::env::var("DATABASE_URL").unwrap_or_else(|_| "books.db".to_string());
    let pool = make_pool(&db_path);
    init_db(&pool).expect("failed to init db");
    let state = AppState { pool };
    let app = build_app(state);
    let addr = SocketAddr::from(([0, 0, 0, 0], 3000));
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    println!("listening on {}", addr);
    axum::serve(listener, app).await.unwrap();
}
