use axum::Router;
use books_api::app;
use books_api::db;
use std::net::SocketAddr;

#[tokio::main]
async fn main() {
    let database = db::init_db().expect("failed to initialize database");
    let router: Router = app(database);

    let addr: SocketAddr = "0.0.0.0:8080".parse().unwrap();
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, router).await.unwrap();
}
