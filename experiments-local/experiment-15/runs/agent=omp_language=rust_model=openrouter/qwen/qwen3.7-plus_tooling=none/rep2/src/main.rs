use book_api::{create_app, db};

#[tokio::main]
async fn main() {
    let pool = db::init_db("sqlite:books.db").await.expect("Failed to initialize database");
    let app = create_app(pool);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    println!("Listening on {}", listener.local_addr().unwrap());
    axum::serve(listener, app).await.unwrap();
}
