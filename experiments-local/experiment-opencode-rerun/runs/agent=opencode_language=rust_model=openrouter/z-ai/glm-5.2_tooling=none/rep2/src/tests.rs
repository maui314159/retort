use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use crate::{
    create_book, delete_book, get_book, list_books, open_connection, router, update_book,
    ApiError, AppState, CreateBook, ListQuery, UpdateBook,
};
use rusqlite::Connection;
use tower::ServiceExt;

fn in_memory_state() -> AppState {
    let conn = Connection::open_in_memory().unwrap();
    crate::init_db(&conn).unwrap();
    AppState::new(conn)
}

#[tokio::test]
async fn create_and_get_book_flow() {
    let state = in_memory_state();
    let created = create_book(
        &state,
        CreateBook {
            title: "The Rust Book".into(),
            author: "Steve Klabnik".into(),
            year: Some(2019),
            isbn: Some("9781593278282".into()),
        },
    )
    .expect("create should succeed");
    assert_eq!(created.title, "The Rust Book");
    assert_eq!(created.author, "Steve Klabnik");
    assert_eq!(created.year, Some(2019));

    let fetched = get_book(&state, created.id).expect("get should succeed");
    assert_eq!(fetched.id, created.id);
    assert_eq!(fetched.title, "The Rust Book");
    assert_eq!(fetched.isbn.as_deref(), Some("9781593278282"));
}

#[tokio::test]
async fn validation_rejects_empty_title_and_author() {
    let state = in_memory_state();
    let err = create_book(
        &state,
        CreateBook {
            title: "   ".into(),
            author: "Author".into(),
            year: None,
            isbn: None,
        },
    )
    .unwrap_err();
    assert!(matches!(err, ApiError::Validation(ref m) if m.contains("title")));

    let err = create_book(
        &state,
        CreateBook {
            title: "Title".into(),
            author: "".into(),
            year: None,
            isbn: None,
        },
    )
    .unwrap_err();
    assert!(matches!(err, ApiError::Validation(ref m) if m.contains("author")));
}

#[tokio::test]
async fn list_filter_by_author() {
    let state = in_memory_state();
    create_book(
        &state,
        CreateBook {
            title: "A".into(),
            author: "Alice".into(),
            year: None,
            isbn: None,
        },
    )
    .unwrap();
    create_book(
        &state,
        CreateBook {
            title: "B".into(),
            author: "Bob".into(),
            year: None,
            isbn: None,
        },
    )
    .unwrap();
    create_book(
        &state,
        CreateBook {
            title: "C".into(),
            author: "Alice".into(),
            year: None,
            isbn: None,
        },
    )
    .unwrap();

    let all = list_books(&state, None).unwrap();
    assert_eq!(all.len(), 3);

    let alice = list_books(&state, Some("Alice".into())).unwrap();
    assert_eq!(alice.len(), 2);
    assert!(alice.iter().all(|b| b.author == "Alice"));

    let _q = ListQuery {
        author: Some("Alice".into()),
    };
}

#[tokio::test]
async fn update_then_delete_book() {
    let state = in_memory_state();
    let created = create_book(
        &state,
        CreateBook {
            title: "Old".into(),
            author: "Old Author".into(),
            year: Some(2000),
            isbn: None,
        },
    )
    .unwrap();

    let updated = update_book(
        &state,
        created.id,
        UpdateBook {
            title: Some("New Title".into()),
            author: None,
            year: Some(2021),
            isbn: Some("111".into()),
        },
    )
    .unwrap();
    assert_eq!(updated.title, "New Title");
    assert_eq!(updated.author, "Old Author");
    assert_eq!(updated.year, Some(2021));

    delete_book(&state, created.id).unwrap();
    let err = get_book(&state, created.id).unwrap_err();
    assert!(matches!(err, ApiError::NotFound));
}

#[tokio::test]
async fn get_missing_returns_not_found() {
    let state = in_memory_state();
    let err = get_book(&state, 9999).unwrap_err();
    assert!(matches!(err, ApiError::NotFound));
}

#[tokio::test]
async fn http_endpoints_integration() {
    let state = in_memory_state();
    let app = router(state);

    // Health
    let resp = app
        .clone()
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);

    // Create via HTTP
    let create_body = serde_json::json!({
        "title": "HTTP Book",
        "author": "HTTP Author",
        "year": 2020,
        "isbn": "isbn-1"
    });
    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(create_body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::CREATED);

    // List via HTTP
    let resp = app
        .clone()
        .oneshot(Request::builder().uri("/books").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let body = axum::body::to_bytes(resp.into_body(), usize::MAX).await.unwrap();
    let arr: Vec<serde_json::Value> = serde_json::from_slice(&body).unwrap();
    assert_eq!(arr.len(), 1);

    // Validation via HTTP: empty title
    let bad = serde_json::json!({"title": "", "author": "x"});
    let resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/books")
                .header("content-type", "application/json")
                .body(Body::from(bad.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}

#[test]
fn open_connection_initializes_schema() {
    let dir = tempfile_dir();
    let path = format!("{}/test_open.db", dir);
    let _ = std::fs::remove_file(&path);
    {
        let conn = open_connection(&path).unwrap();
        // Table should exist; inserting should work.
        conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
            rusqlite::params!["t", "a", 2020, "x"],
        )
        .unwrap();
    }
    std::fs::remove_file(&path).ok();
}

fn tempfile_dir() -> String {
    std::env::temp_dir().to_string_lossy().into_owned()
}
