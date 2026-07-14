use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::response::IntoResponse;
use axum::Json;

use crate::db::Db;
use crate::error::AppError;
use crate::models::{Book, ListQuery, NewBook, UpdateBook};

pub async fn health() -> impl IntoResponse {
    (StatusCode::OK, "ok")
}

pub async fn create_book(
    State(db): State<Db>,
    Json(payload): Json<NewBook>,
) -> Result<(StatusCode, Json<Book>), AppError> {
    let title = payload
        .title
        .map(|t| t.trim().to_string())
        .filter(|t| !t.is_empty())
        .ok_or_else(|| AppError::Validation("title is required".into()))?;
    let author = payload
        .author
        .map(|a| a.trim().to_string())
        .filter(|a| !a.is_empty())
        .ok_or_else(|| AppError::Validation("author is required".into()))?;

    let conn = db.conn.lock().unwrap();
    let isbn_for_insert = payload.isbn.as_deref();
    conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
        rusqlite::params![
            title,
            author,
            payload.year,
            isbn_for_insert,
        ],
    )
    .map_err(|e| match e {
        rusqlite::Error::SqliteFailure(err, msg)
            if err.code == rusqlite::ErrorCode::ConstraintViolation =>
        {
            AppError::Conflict(
                msg.unwrap_or_else(|| "isbn must be unique".to_string()),
            )
        }
        other => AppError::Db(other.to_string()),
    })?;

    let id = conn.last_insert_rowid();
    let book = fetch_book(&conn, id)?.ok_or(AppError::Db("row missing after insert".into()))?;
    drop(conn);
    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn list_books(
    State(db): State<Db>,
    Query(q): Query<ListQuery>,
) -> Result<Json<Vec<Book>>, AppError> {
    let conn = db.conn.lock().unwrap();
    let books: rusqlite::Result<Vec<Book>> = if let Some(author) = q.author {
        let mut stmt =
            conn.prepare("SELECT id, title, author, year, isbn, created_at FROM books WHERE author = ?1 ORDER BY id")?;
        let rows = stmt.query_map(rusqlite::params![author], row_to_book)?;
        rows.collect::<rusqlite::Result<Vec<Book>>>()
    } else {
        let mut stmt =
            conn.prepare("SELECT id, title, author, year, isbn, created_at FROM books ORDER BY id")?;
        let rows = stmt.query_map([], row_to_book)?;
        rows.collect::<rusqlite::Result<Vec<Book>>>()
    };
    Ok(Json(books?))
}

pub async fn get_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> Result<Json<Book>, AppError> {
    let conn = db.conn.lock().unwrap();
    let book = fetch_book(&conn, id)?.ok_or(AppError::NotFound)?;
    Ok(Json(book))
}

pub async fn update_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
    Json(payload): Json<UpdateBook>,
) -> Result<Json<Book>, AppError> {
    let conn = db.conn.lock().unwrap();
    let existing = fetch_book(&conn, id)?.ok_or(AppError::NotFound)?;

    let title = payload
        .title
        .map(|t| t.trim().to_string())
        .map(Some)
        .unwrap_or(Some(existing.title))
        .filter(|t| !t.is_empty())
        .ok_or_else(|| AppError::Validation("title must not be empty".into()))?;

    let author = payload
        .author
        .map(|a| a.trim().to_string())
        .map(Some)
        .unwrap_or(Some(existing.author))
        .filter(|a| !a.is_empty())
        .ok_or_else(|| AppError::Validation("author must not be empty".into()))?;

    let year = payload.year.or(existing.year);
    let isbn = payload.isbn.or(existing.isbn);

    conn.execute(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
        rusqlite::params![title, author, year, isbn.as_deref(), id],
    )
    .map_err(|e| match e {
        rusqlite::Error::SqliteFailure(err, msg)
            if err.code == rusqlite::ErrorCode::ConstraintViolation =>
        {
            AppError::Conflict(msg.unwrap_or_else(|| "isbn must be unique".to_string()))
        }
        other => AppError::Db(other.to_string()),
    })?;

    let book = fetch_book(&conn, id)?.ok_or(AppError::NotFound)?;
    Ok(Json(book))
}

pub async fn delete_book(
    State(db): State<Db>,
    Path(id): Path<i64>,
) -> Result<StatusCode, AppError> {
    let conn = db.conn.lock().unwrap();
    let affected = conn.execute("DELETE FROM books WHERE id = ?1", rusqlite::params![id])?;
    if affected == 0 {
        return Err(AppError::NotFound);
    }
    Ok(StatusCode::NO_CONTENT)
}

fn fetch_book(conn: &rusqlite::Connection, id: i64) -> Result<Option<Book>, rusqlite::Error> {
    let mut stmt = conn.prepare(
        "SELECT id, title, author, year, isbn, created_at FROM books WHERE id = ?1",
    )?;
    let mut rows = stmt.query(rusqlite::params![id])?;
    if let Some(row) = rows.next()? {
        Ok(Some(row_to_book(row)?))
    } else {
        Ok(None)
    }
}

fn row_to_book(row: &rusqlite::Row<'_>) -> rusqlite::Result<Book> {
    Ok(Book {
        id: row.get("id")?,
        title: row.get("title")?,
        author: row.get("author")?,
        year: row.get("year")?,
        isbn: row.get("isbn")?,
        created_at: row.get("created_at")?,
    })
}
