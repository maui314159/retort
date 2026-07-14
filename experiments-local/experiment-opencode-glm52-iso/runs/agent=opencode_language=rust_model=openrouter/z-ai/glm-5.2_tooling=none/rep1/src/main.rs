use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Book {
    id: i64,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct NewBook {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize, Default)]
struct ListQuery {
    author: Option<String>,
}

#[derive(Debug, Serialize)]
struct ErrorBody {
    error: String,
}

enum ApiError {
    BadRequest(String),
    NotFound,
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, msg) = match self {
            ApiError::BadRequest(m) => (StatusCode::BAD_REQUEST, m),
            ApiError::NotFound => (StatusCode::NOT_FOUND, "book not found".to_string()),
            ApiError::Internal(m) => (StatusCode::INTERNAL_SERVER_ERROR, m),
        };
        (status, Json(ErrorBody { error: msg })).into_response()
    }
}

type SharedDb = Arc<Mutex<Connection>>;

#[derive(Clone)]
struct AppState {
    db: SharedDb,
}

fn init_db(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );",
    )?;
    Ok(())
}

fn insert_book(conn: &Connection, nb: &NewBook) -> rusqlite::Result<Book> {
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        rusqlite::params![
            nb.title,
            nb.author,
            nb.year,
            nb.isbn,
        ],
    )?;
    let id = conn.last_insert_rowid();
    Ok(Book {
        id,
        title: nb.title.clone().unwrap_or_default(),
        author: nb.author.clone().unwrap_or_default(),
        year: nb.year,
        isbn: nb.isbn.clone(),
    })
}

fn list_books(conn: &Connection, author: Option<&str>) -> rusqlite::Result<Vec<Book>> {
    let mut sql = String::from("SELECT id, title, author, year, isbn FROM books");
    let mut params: Vec<String> = Vec::new();
    if let Some(a) = author {
        sql.push_str(" WHERE author = ?1");
        params.push(a.to_string());
    }
    sql.push_str(" ORDER BY id ASC");
    let mut stmt = conn.prepare(&sql)?;
    let rows = stmt.query_map(rusqlite::params_from_iter(params.iter()), |row| {
        Ok(Book {
            id: row.get(0)?,
            title: row.get(1)?,
            author: row.get(2)?,
            year: row.get(3)?,
            isbn: row.get(4)?,
        })
    })?;
    let mut books = Vec::new();
    for r in rows {
        books.push(r?);
    }
    Ok(books)
}

fn get_book(conn: &Connection, id: i64) -> rusqlite::Result<Option<Book>> {
    let mut stmt =
        conn.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?1")?;
    let mut rows = stmt.query_map(rusqlite::params![id], |row| {
        Ok(Book {
            id: row.get(0)?,
            title: row.get(1)?,
            author: row.get(2)?,
            year: row.get(3)?,
            isbn: row.get(4)?,
        })
    })?;
    match rows.next() {
        Some(r) => Ok(Some(r?)),
        None => Ok(None),
    }
}

fn update_book(conn: &Connection, id: i64, nb: &NewBook) -> rusqlite::Result<bool> {
    let res = conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        rusqlite::params![nb.title, nb.author, nb.year, nb.isbn, id],
    )?;
    Ok(res > 0)
}

fn delete_book(conn: &Connection, id: i64) -> rusqlite::Result<bool> {
    let res = conn.execute("DELETE FROM books WHERE id = ?1", rusqlite::params![id])?;
    Ok(res > 0)
}

fn validate(nb: &NewBook) -> Result<(), ApiError> {
    let title = nb.title.as_deref().unwrap_or("").trim();
    let author = nb.author.as_deref().unwrap_or("").trim();
    if title.is_empty() {
        return Err(ApiError::BadRequest("title is required".into()));
    }
    if author.is_empty() {
        return Err(ApiError::BadRequest("author is required".into()));
    }
    Ok(())
}

async fn create_book(
    State(state): State<AppState>,
    Json(payload): Json<NewBook>,
) -> Result<(StatusCode, Json<Book>), ApiError> {
    validate(&payload)?;
    let book = {
        let conn = state
            .db
            .lock()
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        insert_book(&conn, &payload).map_err(|e| ApiError::Internal(e.to_string()))?
    };
    Ok((StatusCode::CREATED, Json(book)))
}

async fn list_books_handler(
    State(state): State<AppState>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, ApiError> {
    let books = {
        let conn = state
            .db
            .lock()
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        list_books(&conn, q.author.as_deref()).map_err(|e| ApiError::Internal(e.to_string()))?
    };
    Ok(Json(books))
}

async fn get_book_handler(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, ApiError> {
    let book = {
        let conn = state
            .db
            .lock()
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        get_book(&conn, id).map_err(|e| ApiError::Internal(e.to_string()))?
    };
    match book {
        Some(b) => Ok(Json(b)),
        None => Err(ApiError::NotFound),
    }
}

async fn update_book_handler(
    State(state): State<AppState>,
    Path(id): Path<i64>,
    Json(payload): Json<NewBook>,
) -> Result<Json<Book>, ApiError> {
    validate(&payload)?;
    let updated = {
        let conn = state
            .db
            .lock()
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        update_book(&conn, id, &payload).map_err(|e| ApiError::Internal(e.to_string()))?
    };
    if !updated {
        return Err(ApiError::NotFound);
    }
    let book = {
        let conn = state
            .db
            .lock()
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        get_book(&conn, id).map_err(|e| ApiError::Internal(e.to_string()))?
    };
    match book {
        Some(b) => Ok(Json(b)),
        None => Err(ApiError::NotFound),
    }
}

async fn delete_book_handler(
    State(state): State<AppState>,
    Path(id): Path<i64>,
) -> Result<StatusCode, ApiError> {
    let deleted = {
        let conn = state
            .db
            .lock()
            .map_err(|e| ApiError::Internal(e.to_string()))?;
        delete_book(&conn, id).map_err(|e| ApiError::Internal(e.to_string()))?
    };
    if deleted {
        Ok(StatusCode::NO_CONTENT)
    } else {
        Err(ApiError::NotFound)
    }
}

async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(serde_json::json!({"status": "ok"})))
}

fn build_router(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books_handler))
        .route(
            "/books/:id",
            get(get_book_handler)
                .put(update_book_handler)
                .delete(delete_book_handler),
        )
        .with_state(state)
}

fn make_state(path: &str) -> AppState {
    let conn = Connection::open(path).expect("open db");
    init_db(&conn).expect("init db");
    AppState {
        db: Arc::new(Mutex::new(conn)),
    }
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();
    let db_path = std::env::var("DB_PATH").unwrap_or_else(|_| "books.db".to_string());
    let state = make_state(&db_path);
    let app = build_router(state);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    tracing::info!("listening on 0.0.0.0:3000");
    axum::serve(listener, app).await.unwrap();
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use http_body_util::BodyExt;
    use tower::ServiceExt;

    fn test_state() -> AppState {
        let conn = Connection::open_in_memory().expect("open in-memory db");
        init_db(&conn).expect("init db");
        AppState {
            db: Arc::new(Mutex::new(conn)),
        }
    }

    async fn body_str(b: Body) -> String {
        let bytes = b.collect().await.unwrap();
        String::from_utf8(bytes.to_bytes().to_vec()).unwrap()
    }

    #[tokio::test]
    async fn create_and_get_book() {
        let state = test_state();
        let app = build_router(state.clone());
        let payload = serde_json::json!({
            "title": "The Hobbit",
            "author": "Tolkien",
            "year": 1937,
            "isbn": "978-0261102217"
        });
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(payload.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);
        let body = body_str(resp.into_body()).await;
        let book: Book = serde_json::from_str(&body).unwrap();
        assert_eq!(book.title, "The Hobbit");
        assert_eq!(book.id, 1);

        // GET single
        let resp = app
            .oneshot(Request::builder().uri(format!("/books/{}", book.id)).body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let body = body_str(resp.into_body()).await;
        let fetched: Book = serde_json::from_str(&body).unwrap();
        assert_eq!(fetched.author, "Tolkien");
    }

    #[tokio::test]
    async fn full_crud_lifecycle() {
        let state = test_state();
        let app = build_router(state.clone());

        // Create
        let payload = serde_json::json!({
            "title": "Dune",
            "author": "Herbert",
            "year": 1965,
            "isbn": null
        });
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(payload.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);
        let body = body_str(resp.into_body()).await;
        let book: Book = serde_json::from_str(&body).unwrap();
        let id = book.id;

        // GET single
        let resp = app
            .clone()
            .oneshot(Request::builder().uri(format!("/books/{}", id)).body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);

        // Update
        let upd = serde_json::json!({
            "title": "Dune Updated",
            "author": "Frank Herbert",
            "year": 1965,
            "isbn": "9780441172719"
        });
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("PUT")
                    .uri(format!("/books/{}", id))
                    .header("content-type", "application/json")
                    .body(Body::from(upd.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let body = body_str(resp.into_body()).await;
        let b: Book = serde_json::from_str(&body).unwrap();
        assert_eq!(b.title, "Dune Updated");

        // List with filter
        let resp = app
            .clone()
            .oneshot(Request::builder().uri("/books?author=Frank%20Herbert").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let body = body_str(resp.into_body()).await;
        let books: Vec<Book> = serde_json::from_str(&body).unwrap();
        assert_eq!(books.len(), 1);

        // Delete
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("DELETE")
                    .uri(format!("/books/{}", id))
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::NO_CONTENT);

        // GET after delete -> 404
        let resp = app
            .oneshot(Request::builder().uri(format!("/books/{}", id)).body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn validation_errors() {
        let state = test_state();
        let app = build_router(state.clone());

        // Missing title
        let payload = serde_json::json!({ "author": "Someone" });
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(payload.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);

        // Missing author
        let payload = serde_json::json!({ "title": "Something" });
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/books")
                    .header("content-type", "application/json")
                    .body(Body::from(payload.to_string()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn health_ok() {
        let state = test_state();
        let app = build_router(state.clone());
        let resp = app
            .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
    }
}
