use actix_web::{web, App, HttpServer};
use actix_cors::Cors;
use sqlx::SqlitePool;
use book_collection_api::db;
use book_collection_api::handlers;



#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let database_url = std::env::var("DATABASE_URL")
        .unwrap_or_else(|_| "sqlite:books.db".to_string());

    let pool = SqlitePool::connect(&database_url)
        .await
        .expect("Failed to connect to database");

    db::init_db(&pool)
        .await
        .expect("Failed to initialize database");

    println!("Server running at http://127.0.0.1:8080");
    println!("Health check: GET /health");
    println!("API endpoints:");
    println!("  POST   /books     - Create a new book");
    println!("  GET    /books     - List all books (filter: ?author=)");
    println!("  GET    /books/{{id}} - Get a single book");
    println!("  PUT    /books/{{id}} - Update a book");
    println!("  DELETE /books/{{id}} - Delete a book");

    HttpServer::new(move || {
        let cors = Cors::default()
            .allow_any_origin()
            .allow_any_method()
            .allow_any_header();

        App::new()
            .app_data(web::Data::new(pool.clone()))
            .wrap(cors)
            .route("/health", web::get().to(handlers::health_check))
            .route("/books", web::post().to(handlers::create_book))
            .route("/books", web::get().to(handlers::get_books))
            .route("/books/{id}", web::get().to(handlers::get_book))
            .route("/books/{id}", web::put().to(handlers::update_book))
            .route("/books/{id}", web::delete().to(handlers::delete_book))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
