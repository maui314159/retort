mod db;
mod handlers;
mod models;

use actix_web::middleware::Logger;
use actix_web::{web, App, HttpServer};
use db::Database;
use std::env;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    let database_url = env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite:book_collection.db".to_string());

    log::info!("Connecting to database: {}", database_url);

    let db = Database::new(&database_url)
        .await
        .expect("Failed to connect to database");
    db.migrate()
        .await
        .expect("Failed to run migrations");

    let db_data = web::Data::new(db);

    log::info!("Starting server at http://0.0.0.0:8080");

    HttpServer::new(move || {
        App::new()
            .app_data(db_data.clone())
            .wrap(Logger::default())
            .service(
                web::scope("/books")
                    .route("", web::get().to(handlers::list_books))
                    .route("", web::post().to(handlers::create_book))
                    .route("/{id}", web::get().to(handlers::get_book))
                    .route("/{id}", web::put().to(handlers::update_book))
                    .route("/{id}", web::delete().to(handlers::delete_book)),
            )
            .route("/health", web::get().to(handlers::health))
    })
    .bind("0.0.0.0:8080")?
    .run()
    .await
}

#[cfg(test)]
mod tests {
    use super::*;
    use actix_web::test;
    use sqlx::SqlitePool;

    async fn setup_test_db() -> Database {
        let database_url = "sqlite::memory:";
        let db = Database::new(database_url)
            .await
            .expect("Failed to create in-memory database");
        db.migrate()
            .await
            .expect("Failed to run migrations");
        db
    }

    #[actix_web::test]
    async fn test_health_endpoint() {
        let db = setup_test_db().await;
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .route("/health", web::get().to(crate::handlers::health)),
        )
        .await;

        let req = test::TestRequest::get().uri("/health").to_request();
        let resp = test::call_service(&app, req).await;

        assert!(resp.status().is_success());
    }

    #[actix_web::test]
    async fn test_create_and_get_book() {
        let db = setup_test_db().await;
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .route("/books", web::post().to(crate::handlers::create_book))
                .route("/books/{id}", web::get().to(crate::handlers::get_book)),
        )
        .await;

        // Create a book
        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(&serde_json::json!({
                "title": "Test Book",
                "author": "Test Author",
                "year": 2024,
                "isbn": "1234567890"
            }))
            .to_request();
        let create_resp = test::call_service(&app, create_req).await;
        assert_eq!(create_resp.status().as_u16(), 201);

        // Get the created book
        let body: serde_json::Value = test::read_body_json(create_resp).await;
        let book_id = body["id"].as_str().unwrap();

        let get_req = test::TestRequest::get()
            .uri(&format!("/books/{}", book_id))
            .to_request();
        let get_resp = test::call_service(&app, get_req).await;
        assert!(get_resp.status().is_success());
    }

    #[actix_web::test]
    async fn test_list_books() {
        let db = setup_test_db().await;
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .route("/books", web::get().to(crate::handlers::list_books))
                .route("/books", web::post().to(crate::handlers::create_book)),
        )
        .await;

        // Create a book first
        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(&serde_json::json!({
                "title": "Test Book",
                "author": "Test Author"
            }))
            .to_request();
        let _ = test::call_service(&app, create_req).await;

        // List books
        let list_req = test::TestRequest::get()
            .uri("/books")
            .to_request();
        let list_resp = test::call_service(&app, list_req).await;
        assert!(list_resp.status().is_success());
    }

    #[actix_web::test]
    async fn test_update_book() {
        let db = setup_test_db().await;
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .route("/books", web::post().to(crate::handlers::create_book))
                .route("/books/{id}", web::put().to(crate::handlers::update_book))
                .route("/books/{id}", web::get().to(crate::handlers::get_book)),
        )
        .await;

        // Create a book
        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(&serde_json::json!({
                "title": "Original Title",
                "author": "Original Author"
            }))
            .to_request();
        let create_resp = test::call_service(&app, create_req).await;
        let body: serde_json::Value = test::read_body_json(create_resp).await;
        let book_id = body["id"].as_str().unwrap();

        // Update the book
        let update_req = test::TestRequest::put()
            .uri(&format!("/books/{}", book_id))
            .set_json(&serde_json::json!({
                "title": "Updated Title"
            }))
            .to_request();
        let update_resp = test::call_service(&app, update_req).await;
        assert!(update_resp.status().is_success());

        // Verify the update
        let get_req = test::TestRequest::get()
            .uri(&format!("/books/{}", book_id))
            .to_request();
        let get_resp = test::call_service(&app, get_req).await;
        let body: serde_json::Value = test::read_body_json(get_resp).await;
        assert_eq!(body["title"], "Updated Title");
    }

    #[actix_web::test]
    async fn test_delete_book() {
        let db = setup_test_db().await;
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .route("/books", web::post().to(crate::handlers::create_book))
                .route("/books/{id}", web::delete().to(crate::handlers::delete_book))
                .route("/books/{id}", web::get().to(crate::handlers::get_book)),
        )
        .await;

        // Create a book
        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(&serde_json::json!({
                "title": "Test Book",
                "author": "Test Author"
            }))
            .to_request();
        let create_resp = test::call_service(&app, create_req).await;
        let body: serde_json::Value = test::read_body_json(create_resp).await;
        let book_id = body["id"].as_str().unwrap();

        // Delete the book
        let delete_req = test::TestRequest::delete()
            .uri(&format!("/books/{}", book_id))
            .to_request();
        let delete_resp = test::call_service(&app, delete_req).await;
        assert_eq!(delete_resp.status().as_u16(), 204);

        // Verify the book is gone
        let get_req = test::TestRequest::get()
            .uri(&format!("/books/{}", book_id))
            .to_request();
        let get_resp = test::call_service(&app, get_req).await;
        assert_eq!(get_resp.status().as_u16(), 404);
    }

    #[actix_web::test]
    async fn test_filter_books_by_author() {
        let db = setup_test_db().await;
        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(db))
                .route("/books", web::post().to(crate::handlers::create_book))
                .route("/books", web::get().to(crate::handlers::list_books)),
        )
        .await;

        // Create books with different authors
        let authors = vec!["Author A", "Author B", "Author A"];
        for author in authors {
            let create_req = test::TestRequest::post()
                .uri("/books")
                .set_json(&serde_json::json!({
                    "title": "Test Book",
                    "author": author
                }))
                .to_request();
            let _ = test::call_service(&app, create_req).await;
        }

        // Filter by author
        let filter_req = test::TestRequest::get()
            .uri("/books?author=Author%20A")
            .to_request();
        let filter_resp = test::call_service(&app, filter_req).await;
        assert!(filter_resp.status().is_success());
        let body: Vec<serde_json::Value> = test::read_body_json(filter_resp).await;
        assert_eq!(body.len(), 2);
    }
}
