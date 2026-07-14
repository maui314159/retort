use actix_web::{test, web, App};
use sqlx::SqlitePool;
use book_collection_api::handlers;
use book_collection_api::models::{CreateBookRequest, UpdateBookRequest};
use book_collection_api::db;

async fn setup_test_db() -> SqlitePool {
    let pool = SqlitePool::connect("sqlite::memory:")
        .await
        .expect("Failed to create in-memory database");

    db::init_db(&pool)
        .await
        .expect("Failed to initialize test database");

    pool
}

#[actix_web::test]
async fn test_health_check() {
    let app = test::init_service(
        App::new()
            .route("/health", web::get().to(handlers::health_check))
    ).await;

    let req = test::TestRequest::get().uri("/health").to_request();
    let resp = test::call_service(&app, req).await;

    assert!(resp.status().is_success());
}

#[actix_web::test]
async fn test_create_book() {
    let pool = setup_test_db().await;
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/books", web::post().to(handlers::create_book))
    ).await;

    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(CreateBookRequest {
            title: "Test Book".to_string(),
            author: "Test Author".to_string(),
            year: Some(2024),
            isbn: Some("978-1234567890".to_string()),
        })
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 201);
}

#[actix_web::test]
async fn test_create_book_missing_title() {
    let pool = setup_test_db().await;
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/books", web::post().to(handlers::create_book))
    ).await;

    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(CreateBookRequest {
            title: "".to_string(),
            author: "Test Author".to_string(),
            year: None,
            isbn: None,
        })
        .to_request();

    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 400);
}

#[actix_web::test]
async fn test_get_books() {
    let pool = setup_test_db().await;
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/books", web::post().to(handlers::create_book))
            .route("/books", web::get().to(handlers::get_books))
    ).await;

    // Create a book first
    let create_req = test::TestRequest::post()
        .uri("/books")
        .set_json(CreateBookRequest {
            title: "Book 1".to_string(),
            author: "Author 1".to_string(),
            year: None,
            isbn: None,
        })
        .to_request();

    test::call_service(&app, create_req).await;

    // Get all books
    let get_req = test::TestRequest::get().uri("/books").to_request();
    let resp = test::call_service(&app, get_req).await;

    assert!(resp.status().is_success());
}

#[actix_web::test]
async fn test_get_book_by_id() {
    let pool = setup_test_db().await;
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/books", web::post().to(handlers::create_book))
            .route("/books/{id}", web::get().to(handlers::get_book))
    ).await;

    // Create a book
    let create_req = test::TestRequest::post()
        .uri("/books")
        .set_json(CreateBookRequest {
            title: "Test Book".to_string(),
            author: "Test Author".to_string(),
            year: None,
            isbn: None,
        })
        .to_request();

    let create_resp = test::call_service(&app, create_req).await;
    assert_eq!(create_resp.status(), 201);

    // Get the book by ID (assuming ID 1)
    let get_req = test::TestRequest::get().uri("/books/1").to_request();
    let resp = test::call_service(&app, get_req).await;

    assert!(resp.status().is_success());
}

#[actix_web::test]
async fn test_update_book() {
    let pool = setup_test_db().await;
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/books", web::post().to(handlers::create_book))
            .route("/books/{id}", web::put().to(handlers::update_book))
    ).await;

    // Create a book
    let create_req = test::TestRequest::post()
        .uri("/books")
        .set_json(CreateBookRequest {
            title: "Original Title".to_string(),
            author: "Original Author".to_string(),
            year: None,
            isbn: None,
        })
        .to_request();

    test::call_service(&app, create_req).await;

    // Update the book
    let update_req = test::TestRequest::put()
        .uri("/books/1")
        .set_json(UpdateBookRequest {
            title: Some("Updated Title".to_string()),
            author: None,
            year: None,
            isbn: None,
        })
        .to_request();

    let resp = test::call_service(&app, update_req).await;
    assert!(resp.status().is_success());
}

#[actix_web::test]
async fn test_delete_book() {
    let pool = setup_test_db().await;
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/books", web::post().to(handlers::create_book))
            .route("/books/{id}", web::delete().to(handlers::delete_book))
    ).await;

    // Create a book
    let create_req = test::TestRequest::post()
        .uri("/books")
        .set_json(CreateBookRequest {
            title: "Book to Delete".to_string(),
            author: "Author".to_string(),
            year: None,
            isbn: None,
        })
        .to_request();

    test::call_service(&app, create_req).await;

    // Delete the book
    let delete_req = test::TestRequest::delete().uri("/books/1").to_request();
    let resp = test::call_service(&app, delete_req).await;

    assert!(resp.status().is_success());
}

#[actix_web::test]
async fn test_filter_books_by_author() {
    let pool = setup_test_db().await;
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .route("/books", web::post().to(handlers::create_book))
            .route("/books", web::get().to(handlers::get_books))
    ).await;

    // Create books with different authors
    let authors = vec!["Smith", "Johnson", "Smith"];
    for author in authors {
        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(CreateBookRequest {
                title: format!("Book by {}", author),
                author: author.to_string(),
                year: None,
                isbn: None,
            })
            .to_request();
        test::call_service(&app, create_req).await;
    }

    // Filter by author "Smith"
    let get_req = test::TestRequest::get()
        .uri("/books?author=Smith")
        .to_request();
    let resp = test::call_service(&app, get_req).await;

    assert!(resp.status().is_success());
}
