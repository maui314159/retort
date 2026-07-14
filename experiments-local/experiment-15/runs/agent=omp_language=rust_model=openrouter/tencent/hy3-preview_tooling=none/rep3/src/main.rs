use actix_web::{web, App, HttpResponse, HttpServer, Responder};
use parking_lot::Mutex;
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Book {
    id: Option<i64>,
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct CreateBookRequest {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}
#[derive(Debug, Deserialize, Serialize)]
struct UpdateBookRequest {
    title: Option<String>,
    author: Option<String>,
    year: Option<i32>,
    isbn: Option<String>,
}

struct AppState {
    db: Mutex<Connection>,
}

impl AppState {
    fn new(db_path: &str) -> Result<Self, rusqlite::Error> {
        let conn = Connection::open(db_path)?;
        conn.execute(
            "CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )",
            [],
        )?;
        Ok(AppState { db: Mutex::new(conn) })
    }
}

async fn health_check() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({"status": "healthy"}))
}

async fn create_book(
    data: web::Data<Arc<AppState>>,
    req: web::Json<CreateBookRequest>,
) -> impl Responder {
    if req.title.trim().is_empty() || req.author.trim().is_empty() {
        return HttpResponse::BadRequest().json(
            serde_json::json!({"error": "Title and author are required"}),
        );
    }

    let conn = data.db.lock();
    match conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        params![req.title, req.author, req.year, req.isbn],
    ) {
        Ok(_) => {
            let id = conn.last_insert_rowid();
            match conn.query_row(
                "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
                params![id],
                |row| {
                    Ok(Book {
                        id: Some(row.get(0)?),
                        title: row.get(1)?,
                        author: row.get(2)?,
                        year: row.get(3)?,
                        isbn: row.get(4)?,
                    })
                },
            ) {
                Ok(book) => HttpResponse::Created().json(book),
                Err(e) => HttpResponse::InternalServerError().json(
                    serde_json::json!({"error": format!("Failed to fetch created book: {}", e)}),
                ),
            }
        }
        Err(e) => HttpResponse::InternalServerError().json(
            serde_json::json!({"error": format!("Failed to create book: {}", e)}),
        ),
    }
}

async fn list_books(
    data: web::Data<Arc<AppState>>,
    query: web::Query<std::collections::HashMap<String, String>>,
) -> impl Responder {
    let conn = data.db.lock();
    let author_filter = query.get("author");

    let (sql, params_vec): (&str, Vec<&dyn rusqlite::ToSql>) = match author_filter {
        Some(author) => (
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?",
            vec![author as &dyn rusqlite::ToSql],
        ),
        None => (
            "SELECT id, title, author, year, isbn FROM books",
            vec![],
        ),
    };

    let mut stmt = match conn.prepare(sql) {
        Ok(stmt) => stmt,
        Err(e) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": format!("Failed to prepare query: {}", e)}),
            );
        }
    };

    let map_fn = |row: &rusqlite::Row| {
        Ok(Book {
            id: Some(row.get(0)?),
            title: row.get(1)?,
            author: row.get(2)?,
            year: row.get(3)?,
            isbn: row.get(4)?,
        })
    };

    let rows = if params_vec.is_empty() {
        stmt.query_map([], map_fn)
    } else {
        stmt.query_map(params_vec.as_slice(), map_fn)
    };

    match rows {
        Ok(rows) => {
            let books: Vec<Book> = rows.filter_map(Result::ok).collect();
            HttpResponse::Ok().json(books)
        }
        Err(e) => HttpResponse::InternalServerError().json(
            serde_json::json!({"error": format!("Failed to fetch books: {}", e)}),
        ),
    }
}

async fn get_book(
    data: web::Data<Arc<AppState>>,
    path: web::Path<i64>,
) -> impl Responder {
    let conn = data.db.lock();
    let book_id = path.into_inner();

    match conn.query_row(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
        params![book_id],
        |row| {
            Ok(Book {
                id: Some(row.get(0)?),
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        },
    ) {
        Ok(book) => HttpResponse::Ok().json(book),
        Err(rusqlite::Error::QueryReturnedNoRows) => HttpResponse::NotFound().json(
            serde_json::json!({"error": "Book not found"}),
        ),
        Err(e) => HttpResponse::InternalServerError().json(
            serde_json::json!({"error": format!("Failed to fetch book: {}", e)}),
        ),
    }
}

async fn update_book(
    data: web::Data<Arc<AppState>>,
    path: web::Path<i64>,
    req: web::Json<UpdateBookRequest>,
) -> impl Responder {
    let book_id = path.into_inner();

    if let Some(ref title) = req.title {
        if title.trim().is_empty() {
            return HttpResponse::BadRequest().json(
                serde_json::json!({"error": "Title cannot be empty"}),
            );
        }
    }

    if let Some(ref author) = req.author {
        if author.trim().is_empty() {
            return HttpResponse::BadRequest().json(
                serde_json::json!({"error": "Author cannot be empty"}),
            );
        }
    }

    let conn = data.db.lock();

    match conn.query_row(
        "SELECT id FROM books WHERE id = ?",
        params![book_id],
        |_| Ok(()),
    ) {
        Ok(_) => {}
        Err(rusqlite::Error::QueryReturnedNoRows) => {
            return HttpResponse::NotFound().json(
                serde_json::json!({"error": "Book not found"}),
            );
        }
        Err(e) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": format!("Failed to check book: {}", e)}),
            );
        }
    };

    let mut updates = Vec::new();
    let mut params_vec: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();

    if let Some(ref title) = req.title {
        updates.push("title = ?");
        params_vec.push(Box::new(title.clone()));
    }
    if let Some(ref author) = req.author {
        updates.push("author = ?");
        params_vec.push(Box::new(author.clone()));
    }
    if req.year.is_some() {
        updates.push("year = ?");
        params_vec.push(Box::new(req.year));
    }
    if req.isbn.is_some() {
        updates.push("isbn = ?");
        params_vec.push(Box::new(req.isbn.clone()));
    }

    if updates.is_empty() {
        return HttpResponse::BadRequest().json(
            serde_json::json!({"error": "No fields to update"}),
        );
    }

    let sql = format!("UPDATE books SET {} WHERE id = ?", updates.join(", "));
    params_vec.push(Box::new(book_id));

    let param_refs: Vec<&dyn rusqlite::ToSql> = params_vec.iter().map(|p| p.as_ref()).collect();

    match conn.execute(&sql, param_refs.as_slice()) {
        Ok(_) => match conn.query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            params![book_id],
            |row| {
                Ok(Book {
                    id: Some(row.get(0)?),
                    title: row.get(1)?,
                    author: row.get(2)?,
                    year: row.get(3)?,
                    isbn: row.get(4)?,
                })
            },
        ) {
            Ok(book) => HttpResponse::Ok().json(book),
            Err(e) => HttpResponse::InternalServerError().json(
                serde_json::json!({"error": format!("Failed to fetch updated book: {}", e)}),
            ),
        },
        Err(e) => HttpResponse::InternalServerError().json(
            serde_json::json!({"error": format!("Failed to update book: {}", e)}),
        ),
    }
}

async fn delete_book(
    data: web::Data<Arc<AppState>>,
    path: web::Path<i64>,
) -> impl Responder {
    let conn = data.db.lock();
    let book_id = path.into_inner();

    match conn.execute("DELETE FROM books WHERE id = ?", params![book_id]) {
        Ok(count) if count > 0 => HttpResponse::NoContent().finish(),
        Ok(_) => HttpResponse::NotFound().json(
            serde_json::json!({"error": "Book not found"}),
        ),
        Err(e) => HttpResponse::InternalServerError().json(
            serde_json::json!({"error": format!("Failed to delete book: {}", e)}),
        ),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let state = Arc::new(
        AppState::new("books.db").expect("Failed to initialize database"),
    );

    println!("Server running at http://127.0.0.1:8080");

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(state.clone()))
            .route("/health", web::get().to(health_check))
            .route("/books", web::post().to(create_book))
            .route("/books", web::get().to(list_books))
            .route("/books/{id}", web::get().to(get_book))
            .route("/books/{id}", web::put().to(update_book))
            .route("/books/{id}", web::delete().to(delete_book))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}

#[cfg(test)]
mod tests {
    use super::*;
    use actix_web::test;

    fn setup_test_state() -> Arc<AppState> {
        let state = AppState::new(":memory:").expect("Failed to create in-memory database");
        Arc::new(state)
    }

    #[actix_web::test]
    async fn test_health_check() {
        let app = test::init_service(
            App::new()
                .route("/health", web::get().to(health_check)),
        )
        .await;

        let req = test::TestRequest::get().uri("/health").to_request();
        let resp = test::call_service(&app, req).await;

        assert!(resp.status().is_success());
    }

    #[actix_web::test]
    async fn test_create_and_get_book() {
        let state = setup_test_state();

        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(state.clone()))
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::get().to(get_book)),
        )
        .await;

        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(&CreateBookRequest {
                title: "Test Book".to_string(),
                author: "Test Author".to_string(),
                year: Some(2024),
                isbn: Some("1234567890".to_string()),
            })
            .to_request();

        let create_resp = test::call_service(&app, create_req).await;
        assert_eq!(create_resp.status().as_u16(), 201);

        let body: Book = test::read_body_json(create_resp).await;
        let book_id = body.id.unwrap();

        let get_req = test::TestRequest::get()
            .uri(&format!("/books/{}", book_id))
            .to_request();
        let get_resp = test::call_service(&app, get_req).await;

        assert!(get_resp.status().is_success());
    }

    #[actix_web::test]
    async fn test_list_books_with_filter() {
        let state = setup_test_state();

        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(state.clone()))
                .route("/books", web::post().to(create_book))
                .route("/books", web::get().to(list_books)),
        )
        .await;

        for i in 0..3 {
            let req = test::TestRequest::post()
                .uri("/books")
                .set_json(&CreateBookRequest {
                    title: format!("Book {}", i),
                    author: "Author A".to_string(),
                    year: Some(2024),
                    isbn: None,
                })
                .to_request();
            test::call_service(&app, req).await;
        }

        let req = test::TestRequest::post()
            .uri("/books")
            .set_json(&CreateBookRequest {
                title: "Different Book".to_string(),
                author: "Author B".to_string(),
                year: Some(2023),
                isbn: None,
            })
            .to_request();
        test::call_service(&app, req).await;
        let list_req = test::TestRequest::get()
            .uri("/books?author=Author%20A")
            .to_request();
        let list_resp = test::call_service(&app, list_req).await;

        assert!(list_resp.status().is_success());
        let books: Vec<Book> = test::read_body_json(list_resp).await;
        assert_eq!(books.len(), 3);
    }

    #[actix_web::test]
    async fn test_update_book() {
        let state = setup_test_state();

        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(state.clone()))
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::put().to(update_book)),
        )
        .await;

        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(&CreateBookRequest {
                title: "Original".to_string(),
                author: "Author".to_string(),
                year: Some(2024),
                isbn: None,
            })
            .to_request();

        let create_resp = test::call_service(&app, create_req).await;
        let body: Book = test::read_body_json(create_resp).await;
        let book_id = body.id.unwrap();

        let update_req = test::TestRequest::put()
            .uri(&format!("/books/{}", book_id))
            .set_json(&UpdateBookRequest {
                title: Some("Updated".to_string()),
                author: None,
                year: Some(2025),
                isbn: None,
            })
            .to_request();

        let update_resp = test::call_service(&app, update_req).await;
        assert!(update_resp.status().is_success());

        let body: Book = test::read_body_json(update_resp).await;
        assert_eq!(body.title, "Updated");
        assert_eq!(body.year, Some(2025));
    }

    #[actix_web::test]
    async fn test_delete_book() {
        let state = setup_test_state();

        let app = test::init_service(
            App::new()
                .app_data(web::Data::new(state.clone()))
                .route("/books", web::post().to(create_book))
                .route("/books/{id}", web::delete().to(delete_book))
                .route("/books/{id}", web::get().to(get_book)),
        )
        .await;

        let create_req = test::TestRequest::post()
            .uri("/books")
            .set_json(&CreateBookRequest {
                title: "To Delete".to_string(),
                author: "Author".to_string(),
                year: None,
                isbn: None,
            })
            .to_request();

        let create_resp = test::call_service(&app, create_req).await;
        let body: Book = test::read_body_json(create_resp).await;
        let book_id = body.id.unwrap();

        let delete_req = test::TestRequest::delete()
            .uri(&format!("/books/{}", book_id))
            .to_request();
        let delete_resp = test::call_service(&app, delete_req).await;

        assert_eq!(delete_resp.status().as_u16(), 204);

        let get_req = test::TestRequest::get()
            .uri(&format!("/books/{}", book_id))
            .to_request();
        let get_resp = test::call_service(&app, get_req).await;

        assert_eq!(get_resp.status().as_u16(), 404);
    }
}
