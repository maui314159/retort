use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
};
use rusqlite::params;
use serde::Deserialize;
use uuid::Uuid;
use validator::Validate;

use crate::db::DbPool;
use crate::models::{Book, CreateBookRequest, UpdateBookRequest};

pub async fn health_check() -> Json<serde_json::Value> {
    Json(serde_json::json!({ "status": "ok" }))
}

#[derive(Debug, Deserialize)]
pub struct ListBooksQuery {
    pub author: Option<String>,
}

pub async fn list_books(
    State(db): State<DbPool>,
    Query(params): Query<ListBooksQuery>,
) -> Result<Json<Vec<Book>>, StatusCode> {
    let conn = db.lock().await;
    
    let (query, query_params): (&str, Vec<Box<dyn rusqlite::ToSql>>) = match &params.author {
        Some(author) => (
            "SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?",
            vec![Box::new(format!("%{}%", author)) as Box<dyn rusqlite::ToSql>],
        ),
        None => (
            "SELECT id, title, author, year, isbn FROM books",
            vec![],
        ),
    };

    let mut stmt = conn.prepare(query).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let rows = stmt
        .query_map(rusqlite::params_from_iter(query_params), |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                year: row.get(3)?,
                isbn: row.get(4)?,
            })
        })
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let mut books = Vec::new();
    for book in rows {
        books.push(book.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?);
    }

    Ok(Json(books))
}

pub async fn get_book(State(db): State<DbPool>, Path(id): Path<String>) -> Result<Json<Book>, StatusCode> {
    let conn = db.lock().await;
    let book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            params![id],
            |row| {
                Ok(Book {
                    id: row.get(0)?,
                    title: row.get(1)?,
                    author: row.get(2)?,
                    year: row.get(3)?,
                    isbn: row.get(4)?,
                })
            },
        )
        .map_err(|_| StatusCode::NOT_FOUND)?;

    Ok(Json(book))
}

pub async fn create_book(
    State(db): State<DbPool>,
    Json(payload): Json<CreateBookRequest>,
) -> Result<(StatusCode, Json<Book>), StatusCode> {
    if payload.validate().is_err() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let id = Uuid::new_v4().to_string();
    let conn = db.lock().await;
    
    conn.execute(
        "INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)",
        params![id, payload.title, payload.author, payload.year, payload.isbn],
    )
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let book = Book {
        id: id.clone(),
        title: payload.title,
        author: payload.author,
        year: payload.year,
        isbn: payload.isbn,
    };

    Ok((StatusCode::CREATED, Json(book)))
}

pub async fn update_book(
    State(db): State<DbPool>,
    Path(id): Path<String>,
    Json(payload): Json<UpdateBookRequest>,
) -> Result<Json<Book>, StatusCode> {
    let conn = db.lock().await;

    let existing_book = conn
        .query_row(
            "SELECT id, title, author, year, isbn FROM books WHERE id = ?",
            params![&id],
            |row| {
                Ok(Book {
                    id: row.get(0)?,
                    title: row.get(1)?,
                    author: row.get(2)?,
                    year: row.get(3)?,
                    isbn: row.get(4)?,
                })
            },
        )
        .map_err(|_| StatusCode::NOT_FOUND)?;

    let new_title = payload.title.unwrap_or(existing_book.title);
    let new_author = payload.author.unwrap_or(existing_book.author);
    let new_year = payload.year.or(existing_book.year);
    let new_isbn = payload.isbn.or(existing_book.isbn);

    conn.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        params![new_title, new_author, new_year, new_isbn, &id],
    )
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(Book {
        id: existing_book.id,
        title: new_title,
        author: new_author,
        year: new_year,
        isbn: new_isbn,
    }))
}

pub async fn delete_book(State(db): State<DbPool>, Path(id): Path<String>) -> Result<StatusCode, StatusCode> {
    let conn = db.lock().await;
    let rows_affected = conn
        .execute("DELETE FROM books WHERE id = ?", params![id])
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    if rows_affected == 0 {
        return Err(StatusCode::NOT_FOUND);
    }

    Ok(StatusCode::NO_CONTENT)
}