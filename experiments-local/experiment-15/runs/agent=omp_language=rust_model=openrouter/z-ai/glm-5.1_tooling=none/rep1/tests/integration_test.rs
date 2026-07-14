use actix_web::{test, web, App};
use book_api::{create_app, db, models::CreateBook};
use rusqlite::Connection;

fn in_memory_db() -> Connection {
    let conn = Connection::open_in_memory().unwrap();
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id      TEXT PRIMARY KEY,
            title   TEXT NOT NULL,
            author  TEXT NOT NULL,
            year    INTEGER,
            isbn    TEXT
        );",
    )
    .unwrap();
    conn
}

#[actix_web::test]
async fn test_health_check() {
    let conn = in_memory_db();
    let app = test::init_service(create_app(conn)).await;

    let req = test::TestRequest::get().uri("/health").to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let body: serde_json::Value = test::read_body_json(resp).await;
    assert_eq!(body["status"], "ok");
}

#[actix_web::test]
async fn test_create_and_get_book() {
    let conn = in_memory_db();
    let app = test::init_service(create_app(conn)).await;

    // Create a book
    let new_book = CreateBook {
        title: "The Rust Book".into(),
        author: "Steve Klabnik".into(),
        year: Some(2019),
        isbn: Some("978-1-59327-813-4".into()),
    };
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&new_book)
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 201);

    let created: serde_json::Value = test::read_body_json(resp).await;
    let book_id = created["id"].as_str().unwrap().to_string();
    assert_eq!(created["title"], "The Rust Book");
    assert_eq!(created["author"], "Steve Klabnik");

    // Get the book by ID
    let req = test::TestRequest::get()
        .uri(&format!("/books/{book_id}"))
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);

    let fetched: serde_json::Value = test::read_body_json(resp).await;
    assert_eq!(fetched["id"], book_id);
    assert_eq!(fetched["title"], "The Rust Book");
}

#[actix_web::test]
async fn test_validation_rejects_empty_title_and_author() {
    let conn = in_memory_db();
    let app = test::init_service(create_app(conn)).await;

    // Empty title
    let bad_book = CreateBook {
        title: "".into(),
        author: "Author".into(),
        year: None,
        isbn: None,
    };
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&bad_book)
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 400);

    // Empty author
    let bad_book2 = CreateBook {
        title: "Title".into(),
        author: "  ".into(),
        year: None,
        isbn: None,
    };
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&bad_book2)
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 400);
}

#[actix_web::test]
async fn test_list_books_with_author_filter() {
    let conn = in_memory_db();
    let app = test::init_service(create_app(conn)).await;

    // Create two books
    for book in [
        CreateBook {
            title: "Book A".into(),
            author: "Alice".into(),
            year: None,
            isbn: None,
        },
        CreateBook {
            title: "Book B".into(),
            author: "Bob".into(),
            year: None,
            isbn: None,
        },
    ] {
        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(&book)
            .to_request();
        let resp = test::call_service(&app, req).await;
        assert_eq!(resp.status(), 201);
    }

    // List all books
    let req = test::TestRequest::get().uri("/books").to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);
    let all: Vec<serde_json::Value> = test::read_body_json(resp).await;
    assert_eq!(all.len(), 2);

    // Filter by author
    let req = test::TestRequest::get()
        .uri("/books?author=Alice")
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);
    let filtered: Vec<serde_json::Value> = test::read_body_json(resp).await;
    assert_eq!(filtered.len(), 1);
    assert_eq!(filtered[0]["author"], "Alice");
}

#[actix_web::test]
async fn test_update_and_delete_book() {
    let conn = in_memory_db();
    let app = test::init_service(create_app(conn)).await;

    // Create
    let new_book = CreateBook {
        title: "Original".into(),
        author: "Author".into(),
        year: Some(2020),
        isbn: None,
    };
    let req = test::TestRequest::post()
        .uri("/books")
        .set_json(&new_book)
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 201);
    let created: serde_json::Value = test::read_body_json(resp).await;
    let book_id = created["id"].as_str().unwrap().to_string();

    // Update
    let update = serde_json::json!({
        "title": "Updated Title",
        "year": 2024
    });
    let req = test::TestRequest::put()
        .uri(&format!("/books/{book_id}"))
        .set_json(&update)
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 200);
    let updated: serde_json::Value = test::read_body_json(resp).await;
    assert_eq!(updated["title"], "Updated Title");
    assert_eq!(updated["year"], 2024);
    assert_eq!(updated["author"], "Author"); // unchanged

    // Delete
    let req = test::TestRequest::delete()
        .uri(&format!("/books/{book_id}"))
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 204);

    // Verify deleted
    let req = test::TestRequest::get()
        .uri(&format!("/books/{book_id}"))
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 404);
}

#[actix_web::test]
async fn test_get_nonexistent_book_returns_404() {
    let conn = in_memory_db();
    let app = test::init_service(create_app(conn)).await;

    let req = test::TestRequest::get()
        .uri("/books/nonexistent-id")
        .to_request();
    let resp = test::call_service(&app, req).await;
    assert_eq!(resp.status(), 404);
}
